import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import sqlite3
import os
import requests
from io import BytesIO

intents = discord.Intents.default()
intents.members = True  # Habilitar eventos relacionados con miembros
intents.message_content = True

# Función para obtener la conexión a la base de datos
def obtener_conexion(db_path):
    conn = sqlite3.connect(db_path, check_same_thread=False)  # Permite usar la conexión en diferentes hilos
    conn.row_factory = sqlite3.Row  # Para obtener resultados como diccionarios
    conn.execute('PRAGMA journal_mode = WAL')  # Activar el modo WAL
    return conn

class MemberJoin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        # Enviar tarjeta de bienvenida
        await self.send_card(member, "welcome", "¡Bienvenido/a, {member.name}!")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        # Enviar tarjeta de despedida
        await self.send_card(member, "goodbye", "¡Adiós, {member.name}!")

    async def send_card(self, member, table_name, message_text):
        """Envía una tarjeta personalizada al canal configurado."""
        # Obtener el ID del canal desde la base de datos
        channel_id = await self.get_channel_id(member.guild.id)
        if channel_id is None:
            print(f"⚠️ No se configuró un canal para el servidor {member.guild.name}.")
            return

        # Buscar el canal por ID
        channel = member.guild.get_channel(channel_id)
        if not channel:
            print(f"⚠️ No se encontró un canal con ID {channel_id} en el servidor {member.guild.name}.")
            return

        # Obtener la URL desde la base de datos
        background_url = await self.get_url(member.guild.id, table_name)

        # Crear la tarjeta personalizada
        image_card = await self.create_card(member, background_url, message_text)
        if image_card:
            # Crear el embed con el mensaje
            embed = discord.Embed(
                title=message_text.format(member=member),
                description="¡Esperamos verte pronto!" if table_name == "goodbye" else "¡Esperamos que disfrutes tu estancia!",
                color=discord.Color.red() if table_name == "goodbye" else discord.Color.blue()
            )
            file = discord.File(image_card, filename="card.png")
            embed.set_image(url="attachment://card.png")

            # Enviar el mensaje con la tarjeta personalizada
            await channel.send(embed=embed, file=file)

    async def get_channel_id(self, guild_id):
        """Obtiene el ID del canal desde la base de datos."""
        db_file = f"server/discord_bot_{guild_id}.db"

        if not os.path.exists(db_file):
            print(f"⚠️ La base de datos para el servidor {guild_id} no existe.")
            return None

        try:
            conn = obtener_conexion(db_file)
            c = conn.cursor()

            # Obtener el ID del canal desde la tabla Configuracion
            c.execute("SELECT canal_id_b_g FROM Configuracion WHERE id = 1")
            result = c.fetchone()
            conn.close()

            if result and result["canal_id_b_g"]:
                return result["canal_id_b_g"]
            else:
                print(f"⚠️ No se configuró un canal para el servidor {guild_id}.")
                return None
        except sqlite3.Error as e:
            print(f"Error al acceder a la base de datos: {e}")
            return None

    async def get_url(self, guild_id, table_name):
        """Obtiene la URL desde la base de datos."""
        db_file = f"server/discord_bot_{guild_id}.db"
        default_url = "https://content.wepik.com/statics/279370817/preview-page0.jpg"

        if not os.path.exists(db_file):
            print(f"⚠️ La base de datos para el servidor {guild_id} no existe.")
            return default_url

        try:
            conn = obtener_conexion(db_file)
            c = conn.cursor()

            # Verificar si la tabla 'Configuracion' existe y obtener las URLs de bienvenida o despedida
            c.execute("SELECT bienvenida_url, despedida_url FROM Configuracion WHERE id = 1")
            result = c.fetchone()
            conn.close()

            if result:
                # Retorna la URL correspondiente según el tipo de evento (bienvenida o despedida)
                if table_name == "welcome":
                    return result["bienvenida_url"] if result["bienvenida_url"] else default_url
                elif table_name == "goodbye":
                    return result["despedida_url"] if result["despedida_url"] else default_url
            else:
                print(f"⚠️ No se encontró configuración para el servidor {guild_id}.")
                return default_url
        except sqlite3.Error as e:
            print(f"Error al acceder a la base de datos: {e}")
            return default_url

    async def create_card(self, member, background_url, message_text):
        try:
            # Crear una imagen de fondo fija de 735x386
            background = Image.new("RGBA", (735, 386), (255, 255, 255, 255))
            
            # Descargar la imagen de fondo desde la URL
            response = requests.get(background_url)
            bg_image = Image.open(BytesIO(response.content)).convert("RGBA")
            bg_image = bg_image.resize((735, 386))  # Redimensionar a 735x386
            background.paste(bg_image, (0, 0))

            # Descargar la foto de perfil del usuario
            avatar_asset = member.display_avatar.with_size(128)
            avatar_bytes = await avatar_asset.read()
            avatar = Image.open(BytesIO(avatar_bytes)).convert("RGBA")

            # Redimensionar la imagen de perfil
            avatar_size = 140  # Aumento del tamaño de la foto de perfil
            avatar = avatar.resize((avatar_size, avatar_size))
            mask = Image.new("L", avatar.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
            avatar.putalpha(mask)

            # Centrar la foto de perfil
            avatar_x = (background.width - avatar_size) // 2
            avatar_y = (background.height - avatar_size) // 3  # Colocar más arriba
            background.paste(avatar, (avatar_x, avatar_y), avatar)

            # Añadir el texto con sombreado
            draw = ImageDraw.Draw(background)
            font_size = int(background.width * 0.1)
            font = ImageFont.truetype("./lobster/birama.ttf", font_size)
            text = message_text.format(member=member)

            # Dividir el texto en líneas ajustadas al ancho de la imagen
            max_width = background.width - 40  # Margen
            wrapped_text = self.wrap_text(draw, text, font, max_width)

            # Dibujar cada línea de texto centrada
            line_height = draw.textbbox((0, 0), "Ay", font=font)[3]
            total_text_height = len(wrapped_text) * line_height
            text_y = avatar_y + avatar_size + 30
            start_y = text_y

            if start_y + total_text_height > background.height - 20:
                start_y = background.height - total_text_height - 20

            for i, line in enumerate(wrapped_text):
                text_width = draw.textlength(line, font=font)
                text_x = (background.width - text_width) / 2
                line_y = start_y + i * line_height

                # Dibujar sombra
                draw.text((text_x + 5, line_y + 5), line, font=font, fill=(169, 169, 169, 128))
                # Dibujar texto principal
                draw.text((text_x, line_y), line, font=font, fill="white")

            # Guardar la tarjeta en memoria
            output = BytesIO()
            background.save(output, "PNG")
            output.seek(0)
            return output
        except Exception as e:
            print(f"Error al crear la tarjeta: {e}")
            return None

    def wrap_text(self, draw, text, font, max_width):
        """Divide el texto en líneas que se ajusten al ancho máximo."""
        lines = []
        words = text.split()
        current_line = ""

        for word in words:
            test_line = f"{current_line} {word}".strip()
            if draw.textlength(test_line, font=font) <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        return lines

async def setup(bot):
    await bot.add_cog(MemberJoin(bot))
