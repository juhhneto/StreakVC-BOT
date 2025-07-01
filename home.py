import discord
from discord.ext import commands
import json
import inspect
import sys
import sqlite3
import datetime
from colorama import Fore, Style, init
from cachetools import TTLCache

# --- INITIAL SETUP ---
if sys.version_info < (3, 8) or sys.version_info > (3, 13):
    exit("Only versions between Python 3.8 and 3.13 are supported")

init(autoreset=True)

DB_NAME = 'streakVCBot.db'

# Load the token
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
        token = config.get('token')
        if not token:
            exit("Token not found in config.json")
except FileNotFoundError:
    exit("config.json not found. Please create it and add your bot token.")

# --- DATABASE ---
def setup_database():
    """Initializes the database and the table if they don't exist."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS voice_activity(
                user_id INTEGER PRIMARY KEY,
                last_activity_date TEXT,
                streak INTEGER DEFAULT 0,
                total_vc_minutes INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

# --- BOT INITIALIZATION ---
intents = discord.Intents.default()
intents.voice_states = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# --- CACHE AND GLOBAL STATE ---
leaderboard_cache = TTLCache(maxsize=100, ttl=300)
user_join_times = {}

# --- BOT EVENTS AND COMMANDS ---
@bot.event
async def on_ready():
    """Called when the bot is ready and connected."""
    setup_database()
    print(f"{Fore.GREEN}Database connected and verified.")

    try:
        synced = await bot.tree.sync()
        print(f"{Fore.CYAN}Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"{Fore.RED}Error syncing commands: {e}")
    
    if not bot.user:
        return

    print(inspect.cleandoc(f"""
        Logged in as {bot.user} (ID: {bot.user.id})
        Use this URL to invite {bot.user} to your server:
        {Fore.LIGHTBLUE_EX}https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&scope=applications.commands%20bot{Fore.RESET}
    """), end="\n\n")

@bot.tree.command(name="streak", description="Checks your current streak and total time in VC.")
async def streak(interaction: discord.Interaction):
    """Displays the user's streak and total time in voice channels."""
    user = interaction.user
    print(f"> {Style.BRIGHT}{user}{Style.RESET_ALL} used the /streak command.")

    streak_icon = "<:streakicon:1389711098416070777>"

    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT streak, total_vc_minutes FROM voice_activity WHERE user_id = ?", (user.id,))
        result = c.fetchone()

        if result:
            current_streak, total_minutes = result
        else:
            current_streak, total_minutes = 0, 0

    except sqlite3.Error as e:
        print(f"{Fore.RED}Error fetching streak for {user.name}: {e}")
        await interaction.response.send_message("An error occurred while fetching your data. Please try again later.", ephemeral=True)
        return
    finally:
        if conn:
            conn.close()

    # Create a nice embed response
    embed = discord.Embed(
        title=f"{streak_icon} Streak of {user.display_name}",
        color=discord.Color.orange()
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name=f"{streak_icon} Current Streak", value=f"**{current_streak}** days", inline=True)
    embed.add_field(name="⏰ Total Time in Voice", value=f"**{total_minutes}** minutes", inline=True)

    if current_streak == 0:
        embed.set_footer(text="Spend more than 30 minutes in a voice channel to start your streak!")
    else:
        embed.set_footer(text="Keep it up to keep your flame alive!")

    await interaction.response.send_message(embed=embed)

@bot.event
async def on_voice_state_update(member, before, after):
    """Tracks when a user joins or leaves a voice channel."""
    if member.bot:
        return

    # User joins a voice channel
    if before.channel is None and after.channel is not None:
        print(f"{member.name} joined voice channel {after.channel.name}.")
        user_join_times[member.id] = datetime.datetime.now()

    # User leaves a voice channel
    elif before.channel is not None and after.channel is None:
        if member.id in user_join_times:
            start_time = user_join_times.pop(member.id)
            duration_seconds = (datetime.datetime.now() - start_time).total_seconds()
            duration_minutes = duration_seconds / 60
            
            print(f"{member.name} was in VC for {duration_minutes:.2f} minutes.")

            try:
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()

                # First, ensure the user exists and update the total time in minutes
                c.execute("UPDATE voice_activity SET total_vc_minutes = total_vc_minutes + ? WHERE user_id = ?", (int(duration_minutes), member.id))
                if c.rowcount == 0:
                    c.execute("INSERT INTO voice_activity (user_id, total_vc_minutes) VALUES (?, ?)", (member.id, int(duration_minutes)))
                conn.commit()

                # Now, handle the streak logic if the duration is longer than 30 minutes
                if duration_minutes > 30:
                    c.execute("SELECT streak, last_activity_date FROM voice_activity WHERE user_id = ?", (member.id,))
                    result = c.fetchone()
                    current_streak, last_date_str = result if result else (0, None)

                    today_str = datetime.date.today().isoformat()

                    # Only update the streak if the last activity was not today
                    if last_date_str != today_str:
                        yesterday_str = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
                        
                        new_streak = 0
                        if last_date_str == yesterday_str:
                            new_streak = current_streak + 1
                            print(f"{member.name}'s streak continued! New streak: {new_streak}")
                        else:
                            new_streak = 1 # Starts a new streak
                            print(f"New streak started for {member.name}.")
                        
                        c.execute("UPDATE voice_activity SET streak = ?, last_activity_date = ? WHERE user_id = ?", (new_streak, today_str, member.id))
                        conn.commit()

            except sqlite3.Error as e:
                print(f"{Fore.RED}Database error: {e}")
            finally:
                if conn:
                    conn.close()

# --- BOT EXECUTION ---
if __name__ == "__main__":
    bot.run(token)