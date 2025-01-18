import discord
from discord.ext import commands
import os

class Reload(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(administrator=True)  # Solo administradores pueden usar este comando
    async def reload(self, ctx):
        """Recarga todos los cogs dentro de la carpeta cogs/comandos/."""
        try:
            reload_success = True  # Bandera para saber si todo se recarga correctamente
            embed = discord.Embed(
                title="Recarga de Cogs",
                description="Recargando los cogs dentro de la carpeta `cogs/comandos/`...",
                color=discord.Color.blurple()
            )

            for filename in os.listdir('cogs/comandos/'):
                if filename.endswith('.py') and filename != 'musica.py':  # Ignorar musica.py
                    cog_name = f'cogs.comandos.{filename[:-3]}'
                    try:
                        self.bot.reload_extension(cog_name)  # No es necesario usar 'await' aquí
                        embed.add_field(name=f'Cog {filename}', value="✅ Recargado correctamente.", inline=False)
                    except Exception as e:
                        embed.add_field(name=f'Cog {filename}', value=f"⚠️ Error: {e}", inline=False)
                        reload_success = False  # Si ocurre un error, se marca como falso

            if reload_success:
                # Si todos los cogs se recargaron correctamente, se añade el gif de éxito
                gif_url = "https://i.pinimg.com/originals/13/42/12/134212ba34a8099c993e07a686345f84.gif"
                embed.add_field(name="¡Todo recargado correctamente!", value=f"🎉 Aquí tienes un gif de éxito: {gif_url}", inline=False)
            else:
                embed.add_field(name="Recarga Incompleta", value="Algunos cogs no se recargaron correctamente.", inline=False)

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f'Ocurrió un error: {e}')

# La función setup debe ser síncrona, no asincrónica
async def setup(bot):
    await bot.add_cog(Reload(bot))
