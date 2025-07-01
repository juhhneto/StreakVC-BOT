import discord
from discord.ext import commands
import json
import inspect
import sys
import sqlite3
import datetime
from colorama import Fore, Style, init
from cachetools import TTLCache

# --- CONFIGURAÇÃO INICIAL ---
if sys.version_info < (3, 8) or sys.version_info > (3, 13):
    exit("Only versions between Python 3.8 and 3.13 is supported")

init(autoreset=True)

DB_NAME = 'streakVCBot.db'

# Carregar o token
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
        token = config.get('token')
        if not token:
            exit("Token not found in config.json")
except FileNotFoundError:
    exit("config.json not found. Please create it and add your bot token.")

# --- BANCO DE DADOS ---
def setup_database():
    """Inicializa o banco de dados e a tabela se não existirem."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS voice_activity(
                user_id INTEGER PRIMARY KEY,
                last_activity_date TEXT,
                streak INTEGER DEFAULT 0,
                total_vc_minutes INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

# --- INICIALIZAÇÃO DO BOT ---
intents = discord.Intents.default()
intents.voice_states = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# --- CACHE E ESTADO GLOBAL ---
leaderboard_cache = TTLCache(maxsize=100, ttl=300)
streak_icon = "icon.png"
user_join_times = {}

# --- EVENTOS E COMANDOS DO BOT ---
@bot.event
async def on_ready():
    """Chamado quando o bot está pronto e conectado."""
    setup_database()
    print(f"{Fore.GREEN}Banco de dados conectado e verificado.")

    try:
        synced = await bot.tree.sync()
        print(f"{Fore.CYAN}Sincronizados {len(synced)} comandos de barra.")
    except Exception as e:
        print(f"{Fore.RED}Erro ao sincronizar comandos: {e}")
    
    if not bot.user:
        return

    print(inspect.cleandoc(f"""
        Logged in as {bot.user} (ID: {bot.user.id})
        Use this URL to invite {bot.user} to your server:
        {Fore.LIGHTBLUE_EX}https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&scope=applications.commands%20bot{Fore.RESET}
    """), end="\n\n")

@bot.tree.command(name="streak", description="Verifica seu streak atual e tempo total em VC.")
async def streak(interaction: discord.Interaction):
    """Exibe o streak do usuário e o tempo total em canais de voz."""
    user = interaction.user
    print(f"> {Style.BRIGHT}{user}{Style.RESET_ALL} usou o comando /streak.")

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
        print(f"{Fore.RED}Erro ao buscar streak para {user.name}: {e}")
        await interaction.response.send_message("Ocorreu um erro ao buscar seus dados. Tente novamente mais tarde.", ephemeral=True)
        return
    finally:
        if conn:
            conn.close()

    # Cria uma resposta bonita (Embed)
    embed = discord.Embed(
        title=f"{streak_icon} Streak de {user.display_name}",
        color=discord.Color.orange()
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name=f"{streak_icon} Sequência Atual", value=f"**{current_streak}** dias", inline=True)
    embed.add_field(name="⏰ Tempo Total em Voz", value=f"**{total_minutes}** minutos", inline=True)

    if current_streak == 0:
        embed.set_footer(text="Passe mais de 30 minutos em um canal de voz para começar seu streak!")
    else:
        embed.set_footer(text="Continue assim para manter sua chama acesa!")

    await interaction.response.send_message(embed=embed)

@bot.event
async def on_voice_state_update(member, before, after):
    """Rastreia quando um usuário entra ou sai de um canal de voz."""
    if member.bot:
        return

    # Usuário entra em um canal de voz
    if before.channel is None and after.channel is not None:
        print(f"{member.name} entrou no canal de voz {after.channel.name}.")
        user_join_times[member.id] = datetime.datetime.now()

    # Usuário sai de um canal de voz
    elif before.channel is not None and after.channel is None:
        if member.id in user_join_times:
            start_time = user_join_times.pop(member.id)
            duration_seconds = (datetime.datetime.now() - start_time).total_seconds()
            duration_minutes = duration_seconds / 60
            
            print(f"{member.name} ficou em VC por {duration_minutes:.2f} minutos.")

            try:
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()

                # Primeiro, garanta que o usuário exista e atualize o tempo total em minutos
                c.execute("UPDATE voice_activity SET total_vc_minutes = total_vc_minutes + ? WHERE user_id = ?", (int(duration_minutes), member.id))
                if c.rowcount == 0:
                    c.execute("INSERT INTO voice_activity (user_id, total_vc_minutes) VALUES (?, ?)", (member.id, int(duration_minutes)))
                conn.commit()

                # Agora, lide com a lógica de streak se a duração for maior que 30 minutos
                if duration_minutes > 30:
                    c.execute("SELECT streak, last_activity_date FROM voice_activity WHERE user_id = ?", (member.id,))
                    result = c.fetchone()
                    current_streak, last_date_str = result if result else (0, None)

                    today_str = datetime.date.today().isoformat()

                    # Só atualiza o streak se a última atividade não foi hoje
                    if last_date_str != today_str:
                        yesterday_str = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
                        
                        new_streak = 0
                        if last_date_str == yesterday_str:
                            new_streak = current_streak + 1
                            print(f"Streak de {member.name} continuou! Novo streak: {new_streak}")
                        else:
                            new_streak = 1 # Começa um novo streak
                            print(f"Novo streak iniciado para {member.name}.")
                        
                        c.execute("UPDATE voice_activity SET streak = ?, last_activity_date = ? WHERE user_id = ?", (new_streak, today_str, member.id))
                        conn.commit()

            except sqlite3.Error as e:
                print(f"{Fore.RED}Erro no banco de dados: {e}")
            finally:
                if conn:
                    conn.close()

# --- EXECUÇÃO DO BOT ---
if __name__ == "__main__":
    bot.run(token)