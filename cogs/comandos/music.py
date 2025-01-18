import discord
from discord.ext import commands
from discord.ui import Button, View
import yt_dlp
import asyncio

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_clients = {}
        self.music_queues = {}
        self.autoplay = {}

    @commands.command()
    async def play(self, ctx, *, query: str):
        if not ctx.author.voice:
            await ctx.send(embed=discord.Embed(
                title="Debes estar conectado a un canal de voz",
                color=discord.Color.red()
            ))
            return

        voice_channel = ctx.author.voice.channel

        # Conexión al canal de voz
        if ctx.guild.id not in self.voice_clients:
            vc = await voice_channel.connect()
            self.voice_clients[ctx.guild.id] = vc
            self.music_queues[ctx.guild.id] = []
            self.autoplay[ctx.guild.id] = False  # Autoplay desactivado por defecto
        else:
            vc = self.voice_clients[ctx.guild.id]

        # Búsqueda de la canción o playlist
        songs = await self.search_song(query)
        if not songs:
            await ctx.send(embed=discord.Embed(
                title="No se encontró la canción",
                color=discord.Color.red()
            ))
            return

        # Agregar canciones a la cola
        for title, url, thumbnail in songs:
            self.music_queues[ctx.guild.id].append((url, title, thumbnail))

        if len(songs) > 1:
            await ctx.send(embed=discord.Embed(
                title=f"Se añadieron {len(songs)} canciones a la cola",
                color=discord.Color.purple()
            ))
        else:
            await ctx.send(embed=discord.Embed(
                title=f"Agregado a la cola: {songs[0][0]}",
                color=discord.Color.purple()
            ))

        # Reproducir si no hay música sonando
        if not vc.is_playing():
            await self.play_next(ctx, vc)

    async def search_song(self, query: str):
        ytdl_opts = {
            'format': 'bestaudio',
            'noplaylist': False,  # Permite procesar playlists y mixes
            'quiet': True,
            'default_search': 'ytsearch',
            'extract_audio': True,
        }

        # Búsqueda asincrónica de la canción o playlist
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._search_song_sync, query, ytdl_opts)

    def _search_song_sync(self, query, ytdl_opts):
        with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
            try:
                info = ydl.extract_info(query, download=False)
                
                # Detecta si es una playlist/mix
                if 'entries' in info and info['entries']:
                    songs = []
                    for entry in info['entries'][:50]:  # Limita a las primeras 50 canciones
                        title = entry.get('title', 'Unknown Title')
                        url = entry.get('url', '')
                        thumbnail = entry.get('thumbnail', None)
                        songs.append((title, url, thumbnail))
                    return songs  # Devuelve una lista de canciones
                elif 'url' in info:  # Caso de una sola canción
                    title = info.get('title', 'Unknown Title')
                    url = info.get('url')
                    thumbnail = info.get('thumbnail', None)
                    return [(title, url, thumbnail)]
                else:
                    return None
            except Exception as e:
                print(f"Error al buscar canción: {e}")
                return None

    async def play_next(self, ctx, vc):
        if self.music_queues[ctx.guild.id]:
            url, title, thumbnail = self.music_queues[ctx.guild.id].pop(0)

            embed = discord.Embed(title=f"Reproduciendo: {title}", color=discord.Color.purple())
            embed.set_thumbnail(url="https://i.pinimg.com/originals/fe/c6/52/fec652e8690b6bc68020e36ef6475cf4.gif")
            if thumbnail:
                embed.set_image(url=thumbnail)

            await ctx.send(embed=embed, view=MusicControlView(vc, ctx.guild.id, self.voice_clients, self.music_queues, self.autoplay))

            # Reproducir la canción en segundo plano
            vc.play(discord.FFmpegPCMAudio(url, **self.ffmpeg_options()), after=lambda e: self.bot.loop.create_task(self.check_queue(ctx, vc)))

    async def check_queue(self, ctx, vc):
        if self.music_queues[ctx.guild.id]:
            if self.autoplay.get(ctx.guild.id, False):  # Verificar si autoplay está activado
                await self.play_next(ctx, vc)
            else:
                await asyncio.sleep(60)  # Esperar un minuto antes de desconectar
                if not vc.is_playing() and len(vc.channel.members) == 1:  # Solo el bot
                    await vc.disconnect()
                    del self.voice_clients[ctx.guild.id]
                    del self.music_queues[ctx.guild.id]

    def ffmpeg_options(self):
        return {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn -filter:a "volume=0.50"'  # Puedes ajustar el volumen aquí si lo deseas
        }

class MusicControlView(View):
    def __init__(self, vc, guild_id, voice_clients, music_queues, autoplay):
        super().__init__(timeout=None)
        self.vc = vc
        self.guild_id = guild_id
        self.voice_clients = voice_clients
        self.music_queues = music_queues
        self.autoplay = autoplay  # Guardar el diccionario autoplay aquí

    @discord.ui.button(label="⏯️ Pausa", style=discord.ButtonStyle.primary)
    async def pause(self, interaction: discord.Interaction, button: Button):
        if self.vc.is_playing():
            self.vc.pause()
            await interaction.response.send_message("⏸️ Música pausada", ephemeral=True)
        else:
            await interaction.response.send_message("No hay música reproduciéndose", ephemeral=True)

    @discord.ui.button(label="▶️ Reanudar", style=discord.ButtonStyle.success)
    async def resume(self, interaction: discord.Interaction, button: Button):
        if self.vc.is_paused():
            self.vc.resume()
            await interaction.response.send_message("▶️ Música reanudada", ephemeral=True)
        else:
            await interaction.response.send_message("La música no está pausada", ephemeral=True)

    @discord.ui.button(label="⏹️ Detener", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: Button):
        if self.guild_id in self.voice_clients:
            await self.vc.disconnect()
            del self.voice_clients[self.guild_id]
            del self.music_queues[self.guild_id]
            await interaction.response.send_message("⏹️ Música detenida y bot desconectado", ephemeral=True)
        else:
            await interaction.response.send_message("El bot no está conectado a un canal de voz", ephemeral=True)

    # Agregar un botón de "Autoplay" en la vista de control de música
    @discord.ui.button(label="🔁 Autoplay", style=discord.ButtonStyle.primary)
    async def autoplay(self, interaction: discord.Interaction, button: Button):
        if self.guild_id not in self.autoplay:
            self.autoplay[self.guild_id] = False  # Asegura que tenga un valor predeterminado si no existe
        self.autoplay[self.guild_id] = not self.autoplay[self.guild_id]  # Cambiar el estado de autoplay
        status = "activado" if self.autoplay[self.guild_id] else "desactivado"
        await interaction.response.send_message(f"Autoplay {status}", ephemeral=True)

    @discord.ui.button(label="🗒️ Cola", style=discord.ButtonStyle.secondary)
    async def queue(self, interaction: discord.Interaction, button: Button):
        if self.music_queues[self.guild_id]:
            await self.display_queue(interaction)
        else:
            await interaction.response.send_message("La cola está vacía", ephemeral=True)

    async def display_queue(self, interaction: discord.Interaction):
        queue_list = "\n".join([f"{i+1}. {title}" for i, (url, title, _) in enumerate(self.music_queues[self.guild_id])])
        embed = discord.Embed(title="Cola de Música", description=queue_list, color=discord.Color.purple())
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Music(bot))
