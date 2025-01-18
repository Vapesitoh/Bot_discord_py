import discord
from discord.ext import commands
import os
import sqlite3
from dotenv import load_dotenv
import threading
import asyncio
import signal
import sys
from web.app import app  # Importa 'app' de 'web.app'
import requests  # Agregar esta línea
import time  # Asegúrate de importar el módulo 'time'


# Cargar variables del archivo .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
DEFAULT_PREFIX = os.getenv("DEFAULT_PREFIX", "!")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

def get_prefix(bot, message):
    db_path = f"server/discord_bot_{message.guild.id}.db"
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT prefix FROM Configuracion LIMIT 1")
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else '!'  # Prefijo por defecto

    return '!'  # Prefijo por defecto

bot = commands.Bot(command_prefix=get_prefix, intents=intents)

# Establecer el bot en la configuración de Flask antes de iniciar el servidor
app.config['BOT'] = bot

@bot.event
async def on_ready():
    print(f"Estamos dentro! {bot.user}")
    await load_cogs()  # Asegurarse de cargar los cogs de manera asincrónica

async def load_cogs():
    print("Cargando comandos...")
    correct_count_commands = 0
    error_count_commands = 0
    error_files_commands = []

    for filename in os.listdir('./cogs/comandos'):
        if filename.endswith('.py'):
            try:
                # Usar await para añadir el cog
                await bot.load_extension(f'cogs.comandos.{filename[:-3]}')
                correct_count_commands += 1
            except Exception as e:
                error_count_commands += 1
                error_files_commands.append(filename[:-3])

    print(f"✅ {correct_count_commands} Comandos cargados correctamente")
    if error_count_commands > 0:
        print(f"🆘 {error_count_commands} comando(s) no cargado(s):")
        for error_file in error_files_commands:
            print(f"❌ {error_file}")

    print("Cargando eventos...")
    correct_count_events = 0
    error_count_events = 0
    error_files_events = []

    for filename in os.listdir('./events'):
        if filename.endswith('.py'):
            try:
                await bot.load_extension(f'events.{filename[:-3]}')
                correct_count_events += 1
            except Exception as e:
                error_count_events += 1
                error_files_events.append(filename[:-3])

    print(f"✅ {correct_count_events} Eventos cargados correctamente")
    if error_count_events > 0:
        print(f"🆘 {error_count_events} evento(s) no cargado(s):")
        for error_file in error_files_events:
            print(f"❌ {error_file}")

# Función para hacer ping al servidor cada 5 minutos
def ping_servidor():
    global ping_count
    while True:
        try:
            # Realizar una solicitud HTTP a la propia aplicación para asegurarse de que está viva
            response = requests.get("https://bot-discordpy-1.onrender.com")  # Cambiar a la URL pública
            if response.status_code == 200:
                ping_count += 1
                print(f"Ping #{ping_count} al servidor Flask está vivo.")
            else:
                print(f"Error al hacer ping: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error al hacer ping: {e}")
        
        # Esperar 5 minutos (300 segundos)
        time.sleep(300)  # Cambié el intervalo a 5 minutos

# Ejecutar Flask en un hilo separado
def run_flask():
    port = int(os.environ.get("PORT", 5000))  # Obtener el puerto desde la variable de entorno
    app.run(debug=True, host="0.0.0.0", port=port, use_reloader=False)  # Desactiva el recargador

# Iniciar el ping en un hilo separado
ping_thread = threading.Thread(target=ping_servidor, daemon=True)
ping_thread.start()

# Función para detener el servidor Flask de manera ordenada
async def stop_flask():
    """Detiene el servidor Flask de forma ordenada."""
    print("Deteniendo el servidor Flask...")
    os._exit(0)  # Cierra el proceso de Flask

# Función para detener el bot y el servidor Flask
def shutdown_bot():
    """Detiene el bot de Discord y el servidor Flask."""
    print("Deteniendo el bot de Discord...")
    bot.loop.create_task(stop_flask())  # Detener Flask de manera asíncrona
    asyncio.create_task(bot.close())  # Detener el bot de Discord

# Añadir manejador de señales para un cierre limpio
def setup_signal_handler():
    """Configura el manejador de señales para capturar SIGINT (Ctrl + C)."""
    signal.signal(signal.SIGINT, lambda signum, frame: shutdown_bot())
    signal.signal(signal.SIGTERM, lambda signum, frame: shutdown_bot())

# Configurar el manejador de señales antes de ejecutar el bot
setup_signal_handler()

# Iniciar el bot de Discord
bot.run(TOKEN)
