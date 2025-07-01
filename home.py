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
    noStreak_icon = "<:nostreak:1389730597194301593>"

    total_minutes = 0
    current_streak = 0

    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT streak, total_vc_minutes FROM voice_activity WHERE user_id = ?", (user.id,))
        result = c.fetchone()

        if result:
            current_streak, total_minutes = result

    except sqlite3.Error as e:
        print(f"{Fore.RED}Error fetching streak for {user.name}: {e}")
        await interaction.response.send_message("An error occurred while fetching your data. Please try again later.", ephemeral=True)
        return
    finally:
        if conn:
            conn.close()

    # Add time from the current session if the user is in a voice channel
    if user.id in user_join_times:
        join_time = user_join_times[user.id]
        current_session_seconds = (datetime.datetime.now() - join_time).total_seconds()
        current_session_minutes = int(current_session_seconds / 60)
        total_minutes += current_session_minutes

    # Create a nice embed response
    embed = discord.Embed(
        title=f"Streak of {user.display_name}",
        color=discord.Color.orange()
    )
    embed.set_thumbnail(url=user.display_avatar.url)

    # Determine streak display and footer
    if current_streak == 0:
        streak_value = f"{noStreak_icon} **No streak :/**"
        embed.set_footer(text="Spend more than 30 minutes in a voice channel to start your streak!")
    elif current_streak == 1:
        streak_value = f"{streak_icon} **{current_streak}** day"
        embed.set_footer(text="Keep it up to keep your flame alive!")
    else:  # streak > 1
        streak_value = f"{streak_icon} **{current_streak}** days"
        embed.set_footer(text="Keep it up to keep your flame alive!")

    # Add fields in a consistent order
    embed.add_field(name="Current Streak", value=streak_value, inline=True)
    embed.add_field(name="Total Time in Voice", value=f"⏰ **{total_minutes}** minutes", inline=True)

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
        return

    # User leaves a voice channel
    if before.channel is not None and after.channel is None:
        if member.id not in user_join_times:
            return

        start_time = user_join_times.pop(member.id)
        duration_seconds = (datetime.datetime.now() - start_time).total_seconds()
        duration_minutes = int(duration_seconds / 60)

        if duration_minutes <= 0:
            print(f"{member.name} was in VC for less than a minute.")
            return

        print(f"{member.name} was in VC for {duration_minutes} minutes.")

        conn = None
        try:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()

            # Get current user data
            c.execute("SELECT streak, total_vc_minutes, last_activity_date FROM voice_activity WHERE user_id = ?", (member.id,))
            result = c.fetchone()

            today_str = datetime.date.today().isoformat()

            if result:
                # Existing user
                current_streak, total_minutes, last_date_str = result
                new_total_minutes = total_minutes + duration_minutes
                new_streak = current_streak
                new_last_activity_date = last_date_str

                # Update streak if session > 30 mins and not already counted today
                if duration_minutes > 30 and last_date_str != today_str:
                    yesterday_str = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
                    if last_date_str == yesterday_str:
                        new_streak = current_streak + 1
                        print(f"{member.name}'s streak continued! New streak: {new_streak}")
                    else:
                        new_streak = 1
                        print(f"New streak started for {member.name}.")
                    new_last_activity_date = today_str
                c.execute("UPDATE voice_activity SET total_vc_minutes = ?, streak = ?, last_activity_date = ? WHERE user_id = ?",
                          (new_total_minutes, new_streak, new_last_activity_date, member.id))
            else:
                # New user
                new_streak = 1 if duration_minutes > 30 else 0
                new_last_activity_date = today_str if new_streak > 0 else None
                
                c.execute("INSERT INTO voice_activity (user_id, total_vc_minutes, streak, last_activity_date) VALUES (?, ?, ?, ?)",
                          (member.id, duration_minutes, new_streak, new_last_activity_date))
                
                if new_streak > 0:
                    print(f"New streak started for {member.name}.")

            conn.commit()

        except sqlite3.Error as e:
            print(f"{Fore.RED}Database error during voice state update for {member.name}: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

# --- BOT EXECUTION ---
if __name__ == "__main__":
    bot.run(token)