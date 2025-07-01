import discord
from discord.ext import commands
from discord.ext import menus 
import json
import inspect
import sys
import sqlite3
import datetime
from colorama import Fore, init
from cachetools import TTLCache
leaderboard_cache = TTLCache(maxsize=100, ttl=300) #Refresh after 5 min

# Initialize colorama
init(autoreset=True)

# Configuração inicial
intents = discord.Intents.default()
intents.voice_states = True
intents.messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

if sys.version_info < (3, 8) or sys.version_info > (3, 13):
    exit("Only versions between Python 3.8 and 3.13 is supported")

# Load config
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
        token = config.get('token')
        if not token:
            exit("Token not found in config.json")
except FileNotFoundError:
    exit("config.json not found. Please create it and add your bot token.")

intents = discord.Intents.default()
intents.message_content = True # Enable message content intent if you need to read messages

bot = commands.Bot(command_prefix='!', intents=intents)

#connect database
def connectDb():
    conn = sqlite3.connect('streakVCBot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS voice_activity(
                user_id INTEGER PRIMARY KEY,
                last_joinDate text,
                streak INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

connectDb()

@bot.event
async def on_ready():
    """
    This is called when the bot is ready and has a connection with Discord
    It also prints out the bot's invite URL that automatically uses your
    Client ID to make sure you invite the correct bot with correct scopes.
    """
    if not bot.user:
        raise RuntimeError("on_ready() somehow got called before Client.user was set!")

    print(inspect.cleandoc(f"""
        Logged in as {bot.user} (ID: {bot.user.id})

        Use this URL to invite {bot.user} to your server:
        {Fore.LIGHTBLUE_EX}https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&scope=applications.commands%20bot{Fore.RESET}
    """), end="\n\n")

if __name__ == "__main__":
    bot.run(token)

@client.tree.command()
async def streak(interaction:Interaction):
    #function that's going to make a streak go up once a day
    #that checks if the user is in a vc or message from the day 
    print(f"> {Style.BRIGHT}{interaction.user}{Style.RESET_ALL} used the command.")

@bot.event
async def updateVoiceState(member, before, after):
    if member.bot:
        return 