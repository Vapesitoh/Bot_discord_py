import discord
from discord.ext import commands
import time

class ComandosPing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    @commands.command()
    async def ping(self, ctx):
        """ Muestra el ping del bot con un GIF dependiendo del tiempo de respuesta """
        start_time = time.time()  # Tiempo de inicio
        message = await ctx.send("Prueba")  # Enviar mensaje inicial
        end_time = time.time()  # Tiempo de finalización

        # Calcular la latencia
        ping = (end_time - start_time) * 1000  # Convertir a milisegundos

        # Determinar el GIF según el tiempo de respuesta
        if ping >= 200:
            gif_url = "https://i.pinimg.com/originals/47/6e/ce/476ece614a5a979c016096b1fc0bba34.gif"
        elif ping >= 100:
            gif_url = "https://i.gifer.com/AfDa.gif"
        else:
            gif_url = "https://media.tenor.com/zLFrBs-2_h8AAAAM/counterside-sigma.gif"

        # Crear el Embed
        embed = discord.Embed(
            title="Prueba",
            description=f"**Tiempo de respuesta:** {round(ping, 2)}ms",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Latencia del bot: {round(ping, 2)}ms")
        embed.set_image(url=gif_url)  # Añadir el GIF al embed

        # Editar el mensaje con el Embed
        await message.edit(content=None, embed=embed)

# Función setup asincrónica
async def setup(bot):
    await bot.add_cog(ComandosPing(bot))  # Usa await aquí
