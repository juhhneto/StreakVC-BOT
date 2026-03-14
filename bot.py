import discord
from discord import app_commands
from discord.ext import commands, tasks
import json
import inspect
import sys
import sqlite3
import datetime
from colorama import Fore, Style, init
from cachetools import TTLCache
import os
from dotenv import load_dotenv

from i18n import t, set_lang, get_lang

# --- INITIAL SETUP ---
if sys.version_info < (3, 8) or sys.version_info > (3, 13):
    exit("Only versions between Python 3.8 and 3.13 are supported")

load_dotenv()

token = os.getenv("DISCORD_TOKEN")

if not token:
    raise ValueError("Token não encontrado! Verifique sua variável de ambiente DISCORD_TOKEN.")

init(autoreset=True)

DB_NAME = 'streakVCBot.db'



# --- XP AND LEVEL SYSTEM ---
XP_PER_MINUTE = 1

LEVEL_THRESHOLDS = [
    (0,    1, "level_1", "🌱"),
    (30,   2, "level_2", "📚"),
    (60,   3, "level_3", "⚡"),
    (120,  4, "level_4", "🔥"),
    (180,  5, "level_5", "💎"),
    (240,  6, "level_6", "👑"),
    (320,  7, "level_7", "🚀"),
    (400,  8, "level_8", "🌌"),
    (500,  9, "level_9", "🌀"),
    (650,  10, "level_10", "🌟"),
    (800,  11, "level_11", "🛸"),
    (1000, 12, "level_12", "🏆"),
    (1250, 13, "level_13", "👾"),
    (1500, 14, "level_14", "🌠"),
    (2000, 15, "level_15", "🌌"),
    (3000, 16, "level_16", "🔱"),
    (4000, 17, "level_17", "🛡️"),
    (5200, 18, "level_18", "⚔️"),
    (6500, 19, "level_19", "🧙"),
    (8000, 20, "level_20", "🐲"),
    (9700, 21, "level_21", "🌋"),
    (11500, 22, "level_22", "☄️"),
    (13500, 23, "level_23", "🧿"),
    (15700, 24, "level_24", "⛩️"),
    (18100, 25, "level_25", "🏮"),
    (20700, 26, "level_26", "🏯"),
    (23500, 27, "level_27", "🌅"),
    (26500, 28, "level_28", "☀️"),
    (29700, 29, "level_29", "🎆"),
    (33100, 30, "level_30", "✨"),
    (36800, 31, "level_31", "🎈"),
    (40700, 32, "level_32", "🧨"),
    (44800, 33, "level_33", "🧧"),
    (49100, 34, "level_34", "🎀"),
    (53600, 35, "level_35", "🎟️"),
    (58300, 36, "level_36", "🎖️"),
    (63200, 37, "level_37", "🎗️"),
    (68300, 38, "level_38", "🏮"),
    (73600, 39, "level_39", "🎐"),
    (79100, 40, "level_40", "💠"),
    (85000, 41, "level_41", "🔱"),
    (91100, 42, "level_42", "☸️"),
    (97400, 43, "level_43", "☮️"),
    (103900, 44, "level_44", "☪️"),
    (110600, 45, "level_45", "🕉️"),
    (117500, 46, "level_46", "☯️"),
    (124600, 47, "level_47", "☦️"),
    (131900, 48, "level_48", "⛎"),
    (139400, 49, "level_49", "♈"),
    (147100, 50, "level_50", "☯️")
]

def get_level_info(daily_minutes: int):
    """Returns (level, title, emoji, xp, xp_in_level, xp_to_next) for today's minutes."""
    xp = daily_minutes * XP_PER_MINUTE
    current_entry = LEVEL_THRESHOLDS[0]
    next_min_xp = None
    for i, entry in enumerate(LEVEL_THRESHOLDS):
        if xp >= entry[0]:
            current_entry = entry
            next_min_xp = LEVEL_THRESHOLDS[i + 1][0] if i + 1 < len(LEVEL_THRESHOLDS) else None
    min_xp, level, title_key, emoji = current_entry
    title = t(title_key)
    xp_in_level = xp - min_xp
    xp_to_next  = (next_min_xp - min_xp) if next_min_xp is not None else None
    return level, title, emoji, xp, xp_in_level, xp_to_next

def build_xp_bar(xp_in_level: int, xp_to_next, bar_length: int = 10) -> str:
    if xp_to_next is None:
        return t("streak_max_xp")
    progress = min(xp_in_level / xp_to_next, 1.0)
    filled   = int(progress * bar_length)
    bar      = "█" * filled + "░" * (bar_length - filled)
    return f"`[{bar}]` {xp_in_level}/{xp_to_next} XP"

def format_time(total_minutes: int) -> str:
    hours = total_minutes // 60
    mins  = total_minutes % 60
    if hours > 0:
        return f"{hours}h {mins}m"
    return f"{mins} min"

def get_current_week_start() -> str:
    today = datetime.date.today()
    return (today - datetime.timedelta(days=today.weekday())).isoformat()

# --- DATABASE ---
_REQUIRED_COLUMNS = [
    ("guild_id",          "INTEGER DEFAULT 0"),  # migration for old DBs without guild_id
    ("username",          "TEXT"),
    ("streak",            "INTEGER DEFAULT 0"),
    ("last_streak_date",  "TEXT"),
    ("daily_vc_minutes",  "INTEGER DEFAULT 0"),
    ("last_reset_date",   "TEXT"),
    ("weekly_vc_minutes", "INTEGER DEFAULT 0"),
    ("week_start_date",   "TEXT"),
    ("last_activity_date","TEXT"),
    ("total_vc_minutes",  "INTEGER DEFAULT 0"),
]

def setup_database():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS voice_activity (
                    user_id INTEGER,
                    guild_id INTEGER,
                    username TEXT,
                    streak INTEGER DEFAULT 0,
                    last_streak_date TEXT,
                    daily_vc_minutes INTEGER DEFAULT 0,
                    last_reset_date TEXT,
                    weekly_vc_minutes INTEGER DEFAULT 0,
                    week_start_date TEXT,
                    PRIMARY KEY (user_id, guild_id)
                )''')

    c.execute("PRAGMA table_info(voice_activity)")
    existing_columns = {row[1] for row in c.fetchall()}

    for col_name, col_def in _REQUIRED_COLUMNS:
        if col_name not in existing_columns:
            c.execute(f"ALTER TABLE voice_activity ADD COLUMN {col_name} {col_def}")
            print(f"{Fore.YELLOW}Migration: added column '{col_name}' to voice_activity.")

    c.execute("PRAGMA table_info(voice_activity)")
    existing_columns = {row[1] for row in c.fetchall()}

    if "last_activity_date" in existing_columns and "last_streak_date" in existing_columns:
        c.execute("""
            UPDATE voice_activity
            SET last_streak_date = last_activity_date
            WHERE last_streak_date IS NULL AND last_activity_date IS NOT NULL
        """)
        if c.rowcount:
            print(f"{Fore.YELLOW}Migration: copied last_activity_date → last_streak_date for {c.rowcount} user(s).")

    if "total_vc_minutes" in existing_columns and "weekly_vc_minutes" in existing_columns:
        c.execute("""
            UPDATE voice_activity
            SET weekly_vc_minutes = total_vc_minutes,
                week_start_date   = ?
            WHERE weekly_vc_minutes = 0 AND total_vc_minutes > 0
        """, (get_current_week_start(),))
        if c.rowcount:
            print(f"{Fore.YELLOW}Migration: copied total_vc_minutes → weekly_vc_minutes for {c.rowcount} user(s).")

    conn.commit()
    conn.close()

def commit_session(member_id: int, guild_id: int, display_name: str, duration_minutes: int):
    """
    Saves a VC session.
    - Resets daily counter when the day changes (flushing into weekly first).
    - Updates weekly counter when the week changes.
    - Updates streak once per day when daily total first crosses 30 min.
    """
    if duration_minutes <= 0:
        return

    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        today_str     = datetime.date.today().isoformat()
        yesterday_str = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        current_week  = get_current_week_start()

        c.execute("""SELECT streak, last_streak_date,
                            daily_vc_minutes, last_reset_date,
                            weekly_vc_minutes, week_start_date
                     FROM voice_activity WHERE user_id = ? AND guild_id = ?""",
                  (member_id, guild_id))
        row = c.fetchone()

        if row:
            (current_streak, last_streak_date,
             daily_minutes, last_reset_date,
             weekly_minutes, week_start) = row

            # Daily reset: flush yesterday's daily total into weekly before zeroing
            if last_reset_date != today_str:
                if week_start != current_week:
                    weekly_minutes = 0
                    week_start     = current_week
                else:
                    weekly_minutes += daily_minutes

                print(f"{Fore.MAGENTA}Daily reset for {display_name} "
                      f"(yesterday: {daily_minutes} min → weekly: {weekly_minutes} min).")
                daily_minutes = 0

            daily_minutes  += duration_minutes
            new_streak      = current_streak
            new_last_streak = last_streak_date

            already_qualified = (last_streak_date == today_str)
            just_qualified    = daily_minutes >= 30 and not already_qualified

            if just_qualified:
                if last_streak_date == yesterday_str:
                    new_streak += 1
                    print(f"{Fore.GREEN}{display_name}'s streak continued → {new_streak} days.")
                else:
                    new_streak = 1
                    print(f"{Fore.GREEN}New streak started for {display_name}.")
                new_last_streak = today_str

            c.execute("""UPDATE voice_activity
                         SET username=?, streak=?, last_streak_date=?,
                             daily_vc_minutes=?, last_reset_date=?,
                             weekly_vc_minutes=?, week_start_date=?
                         WHERE user_id=? AND guild_id=?""",
                      (display_name, new_streak, new_last_streak,
                       daily_minutes, today_str,
                       weekly_minutes, week_start,
                       member_id, guild_id))
        else:
            new_streak      = 1 if duration_minutes >= 30 else 0
            new_last_streak = today_str if new_streak > 0 else None
            if new_streak > 0:
                print(f"{Fore.GREEN}First streak started for {display_name}.")

            c.execute("""INSERT INTO voice_activity
                         (user_id, guild_id, username, streak, last_streak_date,
                          daily_vc_minutes, last_reset_date,
                          weekly_vc_minutes, week_start_date)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                      (member_id, guild_id, display_name, new_streak, new_last_streak,
                       duration_minutes, today_str,
                       duration_minutes, current_week))

        conn.commit()
        leaderboard_cache.clear()

    except sqlite3.Error as e:
        print(f"{Fore.RED}DB error for {display_name}: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

# --- BOT INITIALIZATION ---
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

leaderboard_cache = TTLCache(maxsize=100, ttl=300)
user_join_times: dict[int, datetime.datetime]        = {}
user_guild_map:  dict[int, int]                      = {}  # uid -> guild_id
channel_members_snapshot: dict[int, set[int]]        = {}


# --- POLLING TASK ---
@tasks.loop(seconds=60)
async def poll_voice_channels():
    # Canais que o bot está atualmente conectado
    active_channel_ids = {vc.channel.id for vc in bot.voice_clients if vc.channel}

    # Canais que estavam no snapshot mas o bot não está mais conectado
    for channel_id in list(channel_members_snapshot.keys()):
        if channel_id not in active_channel_ids:
            now = datetime.datetime.now()
            # Tenta recuperar a guild pelo snapshot — busca em todas as guilds
            guild_id = None
            for vc in bot.voice_clients:
                if vc.channel and vc.channel.id == channel_id:
                    guild_id = vc.channel.guild.id
                    break
            for uid in channel_members_snapshot[channel_id]:
                if uid in user_join_times:
                    start      = user_join_times.pop(uid)
                    duration_m = int((now - start).total_seconds() / 60)
                    gid        = user_guild_map.pop(uid, guild_id)
                    name       = str(uid)
                    if gid:
                        guild = bot.get_guild(gid)
                        if guild:
                            member = guild.get_member(uid)
                            if member:
                                name = member.display_name
                    print(f"{Fore.YELLOW}Bot saiu de canal — commitando {name}: {duration_m} min.")
                    if gid:
                        commit_session(uid, gid, name, duration_m)
            del channel_members_snapshot[channel_id]

    for voice_client in bot.voice_clients:
        channel = voice_client.channel
        if channel is None:
            continue

        guild_id    = channel.guild.id
        current_ids = {m.id for m in channel.members if not m.bot}
        prev_ids    = channel_members_snapshot.get(channel.id, set())

        for uid in current_ids - prev_ids:
            if uid not in user_join_times:
                user_join_times[uid] = datetime.datetime.now()
                user_guild_map[uid]  = guild_id
                member = channel.guild.get_member(uid)
                name   = member.display_name if member else str(uid)
                print(f"{Fore.CYAN}{name} detected in '{channel.name}'.")

        for uid in prev_ids - current_ids:
            if uid in user_join_times:
                start      = user_join_times.pop(uid)
                gid        = user_guild_map.pop(uid, guild_id)
                duration_m = int((datetime.datetime.now() - start).total_seconds() / 60)
                member     = channel.guild.get_member(uid)
                name       = member.display_name if member else str(uid)
                print(f"{Fore.YELLOW}{name} left after {duration_m} min.")
                commit_session(uid, gid, name, duration_m)

        # Flush active users still in channel — saves 1 min of progress per tick
        now = datetime.datetime.now()
        for uid in current_ids:
            if uid in user_join_times:
                start      = user_join_times[uid]
                duration_m = int((now - start).total_seconds() / 60)
                if duration_m <= 0:
                    continue
                member = channel.guild.get_member(uid)
                name   = member.display_name if member else str(uid)
                commit_session(uid, guild_id, name, duration_m)
                user_join_times[uid] = now  # reset timer to avoid double-counting

        channel_members_snapshot[channel.id] = current_ids

@poll_voice_channels.before_loop
async def before_poll():
    await bot.wait_until_ready()


# --- BOT EVENTS ---
@bot.event
async def on_ready():
    setup_database()
    print(f"{Fore.GREEN}Database connected and verified.")
    try:
        synced = await bot.tree.sync()
        print(f"{Fore.CYAN}{len(synced)} slash commands synced.")
    except Exception as e:
        print(f"{Fore.RED}Error syncing commands: {e}")

    poll_voice_channels.start()
    print(f"{Fore.CYAN}Voice poll started (60s). Progress saved every tick.")

    if not bot.user:
        return
    print(inspect.cleandoc(f"""
        Logged in as {bot.user} (ID: {bot.user.id})
        Invite URL:
        {Fore.LIGHTBLUE_EX}https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&scope=applications.commands%20bot{Fore.RESET}
    """), end="\n\n")


# --- SLASH COMMANDS ---

@bot.tree.command(name="join", description="Make the bot join your current voice channel. / Entrar no canal de voz.")
async def join_cmd(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message(t("server_only"), ephemeral=True)
        return

    member = interaction.guild.get_member(interaction.user.id)
    if member is None or member.voice is None or member.voice.channel is None:
        await interaction.response.send_message(t("join_not_in_vc"), ephemeral=True)
        return

    channel = member.voice.channel

    if interaction.guild.voice_client and interaction.guild.voice_client.channel == channel:
        await interaction.response.send_message(
            t("join_already", channel=channel.name), ephemeral=True)
        return

    await interaction.response.defer()

    try:
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.move_to(channel)
        else:
            await channel.connect(reconnect=True, self_deaf=True)
    except Exception as e:
        print(f"{Fore.RED}Failed to connect to voice: {e}")
        await interaction.followup.send(f"❌ Could not connect to **{channel.name}**: {e}", ephemeral=True)
        return

    now         = datetime.datetime.now()
    guild_id    = interaction.guild.id
    current_ids = {m.id for m in channel.members if not m.bot}
    channel_members_snapshot[channel.id] = current_ids
    for uid in current_ids:
        user_join_times.setdefault(uid, now)
        user_guild_map.setdefault(uid, guild_id)

    print(f"{Fore.GREEN}Bot connected to '{channel.name}' with {len(current_ids)} member(s).")
    await interaction.followup.send(t("join_success", channel=channel.name))


@bot.tree.command(name="leave", description="Make the bot leave and save open sessions. / Sair e salvar sessões.")
async def leave_cmd(interaction: discord.Interaction):
    if not interaction.guild or not interaction.guild.voice_client:
        await interaction.response.send_message(t("leave_not_connected"), ephemeral=True)
        return

    channel  = interaction.guild.voice_client.channel
    guild_id = interaction.guild.id
    now      = datetime.datetime.now()

    saved = []
    for uid in list(user_join_times.keys()):
        start      = user_join_times.pop(uid)
        gid        = user_guild_map.pop(uid, guild_id)
        duration_m = int((now - start).total_seconds() / 60)
        member     = interaction.guild.get_member(uid)
        name       = member.display_name if member else str(uid)
        commit_session(uid, gid, name, duration_m)
        saved.append(name)

    channel_members_snapshot.pop(channel.id, None)
    await interaction.guild.voice_client.disconnect()

    msg = t("leave_msg", channel=channel.name)
    if saved:
        msg += t("leave_saved", names=", ".join(saved))
    await interaction.response.send_message(msg)


@bot.tree.command(name="streak", description="Show your streak, today's voice time and level. / Ver frequência.")
async def streak_cmd(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message(t("server_only"), ephemeral=True)
        return

    user     = interaction.user
    guild_id = interaction.guild.id
    print(f"> {Style.BRIGHT}{user}{Style.RESET_ALL} used /streak.")

    streak_icon   = "<:streakicon:1389711098416070777>"
    nostreak_icon = "<:nostreak:1389730597194301593>"
    current_streak = 0
    daily_minutes  = 0

    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        c    = conn.cursor()
        c.execute("""SELECT streak, daily_vc_minutes, last_reset_date, last_streak_date
                     FROM voice_activity WHERE user_id = ? AND guild_id = ?""",
                  (user.id, guild_id))
        row = c.fetchone()
        last_streak_date = None
        if row:
            current_streak, daily_minutes, last_reset_date, last_streak_date = row
            if last_reset_date != datetime.date.today().isoformat():
                daily_minutes = 0
    except sqlite3.Error as e:
        print(f"{Fore.RED}Error fetching streak: {e}")
        await interaction.response.send_message(t("db_error"), ephemeral=True)
        return
    finally:
        if conn:
            conn.close()

    if user.id in user_join_times:
        live_s = (datetime.datetime.now() - user_join_times[user.id]).total_seconds()
        daily_minutes += int(live_s / 60)

    level, title, level_emoji, xp, xp_in_level, xp_to_next = get_level_info(daily_minutes)
    xp_bar       = build_xp_bar(xp_in_level, xp_to_next)
    minutes_left = max(0, 30 - daily_minutes)

    today_str      = datetime.date.today().isoformat()
    yesterday_str  = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    tentative_streak = current_streak
    session_qualifies = daily_minutes >= 30
    streak_already_updated = (last_streak_date == today_str)

    if session_qualifies and not streak_already_updated:
        if last_streak_date == yesterday_str:
            tentative_streak = current_streak + 1
        else:
            tentative_streak = 1

    embed = discord.Embed(
        title=t("streak_title", name=user.display_name),
        color=discord.Color.orange()
    )
    embed.set_thumbnail(url=user.display_avatar.url)

    if tentative_streak == 0:
        streak_value = t("streak_none", icon=nostreak_icon)
    elif tentative_streak == 1:
        streak_value = t("streak_day", icon=streak_icon, n=tentative_streak)
    else:
        streak_value = t("streak_days", icon=streak_icon, n=tentative_streak)

    footer_text = (
        t("streak_footer_need", min=minutes_left)
        if minutes_left > 0
        else t("streak_footer_done")
    )

    embed.add_field(name=t("streak_field_streak"), value=streak_value,                        inline=True)
    embed.add_field(name=t("streak_field_time"),   value=f"**{format_time(daily_minutes)}**", inline=True)
    embed.add_field(name="\u200b",                  value="\u200b",                            inline=True)
    embed.add_field(
        name=t("streak_field_level", emoji=level_emoji, level=level, title=title),
        value=xp_bar,
        inline=False
    )
    embed.set_footer(text=footer_text)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="ranking", description="Show the weekly voice time top 3. / Ver ranking semanal.")
async def ranking_cmd(interaction: discord.Interaction):
    user = interaction.user
    print(f"> {Style.BRIGHT}{user}{Style.RESET_ALL} used /ranking.")

    if not interaction.guild:
        await interaction.response.send_message(t("server_only"), ephemeral=True)
        return

    guild_id  = interaction.guild.id
    cache_key = f"weekly_ranking:{guild_id}"
    top_users = leaderboard_cache.get(cache_key)

    if top_users is None:
        try:
            today_str    = datetime.date.today().isoformat()
            current_week = get_current_week_start()
            conn = sqlite3.connect(DB_NAME)
            c    = conn.cursor()
            c.execute("""
                SELECT user_id, username, streak,
                       weekly_vc_minutes + CASE
                           WHEN week_start_date = ? AND last_reset_date = ? THEN daily_vc_minutes
                           ELSE 0
                       END AS total_week_minutes
                FROM voice_activity
                WHERE guild_id = ?
                  AND (
                    weekly_vc_minutes > 0
                    OR (week_start_date = ? AND daily_vc_minutes > 0)
                  )
                ORDER BY total_week_minutes DESC, streak DESC
                LIMIT 3
            """, (current_week, today_str, guild_id, current_week))
            top_users = c.fetchall()
            leaderboard_cache[cache_key] = top_users
        except sqlite3.Error as e:
            print(f"{Fore.RED}Error fetching ranking: {e}")
            await interaction.response.send_message(t("ranking_error"), ephemeral=True)
            return
        finally:
            if conn:
                conn.close()

    embed = discord.Embed(
        title=t("ranking_title"),
        description=t("ranking_desc"),
        color=discord.Color.gold()
    )

    medals      = ["🥇", "🥈", "🥉"]
    streak_icon = "<:streakicon:1389711098416070777>"

    if not top_users:
        embed.description = t("ranking_empty")
    else:
        for i, (uid, username, streak, week_minutes) in enumerate(top_users):
            days_label = t("ranking_day") if streak == 1 else t("ranking_days")
            embed.add_field(
                name=f"{medals[i]} {username}",
                value=(
                    t("ranking_week_time", time=format_time(week_minutes)) + "\n" +
                    t("ranking_streak", icon=streak_icon, n=streak, label=days_label)
                ),
                inline=False
            )

    embed.set_footer(text=t("ranking_footer"))
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="language", description="Change the bot language. / Mudar o idioma do bot.")
@app_commands.describe(lang="Choose a language / Escolha um idioma")
@app_commands.choices(lang=[
    app_commands.Choice(name="Português 🇧🇷", value="pt"),
    app_commands.Choice(name="English 🇺🇸",   value="en"),
])
async def language_cmd(interaction: discord.Interaction, lang: app_commands.Choice[str]):
    current = get_lang()

    if current == lang.value:
        await interaction.response.send_message(t("lang_already"), ephemeral=True)
        return

    set_lang(lang.value)
    leaderboard_cache.clear()
    print(f"{Fore.CYAN}Language changed to '{lang.value}' by {interaction.user}.")
    await interaction.response.send_message(t("lang_changed"))


# --- BOT EXECUTION ---
if __name__ == "__main__":
    bot.run(token)