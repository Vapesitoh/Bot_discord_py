import discord
from discord.ext import commands
from discord.ui import Button, View

class CustomHelpCommand(commands.HelpCommand):
    def __init__(self):
        super().__init__()

    async def send_bot_help(self, mapping):
        """Muestra todos los comandos organizados por categoría."""
        ctx = self.context
        bot = ctx.bot

        # Lista de comandos por páginas (5 comandos por página)
        pages = []
        current_page = []
        page_limit = 5

        for cog, commands in mapping.items():
            cog_name = cog.qualified_name if cog else "Sin Categoría"
            command_list = [f"`{command.name}`: {command.help or 'Sin descripción'}" for command in commands]
            for command in command_list:
                current_page.append(command)
                if len(current_page) >= page_limit:
                    pages.append((cog_name, current_page))
                    current_page = []
        
        # Si hay comandos restantes en la última página
        if current_page:
            pages.append((cog_name, current_page))

        # Función para enviar una página
        async def send_page(page_number):
            page = pages[page_number]
            embed = discord.Embed(
                title="Lista de Comandos",
                description=f"Aquí están los comandos organizados por categorías (Página {page_number + 1}):",
                color=discord.Color.blurple()
            )

            cog_name, command_list = page
            embed.add_field(
                name=cog_name,
                value="\n".join(command_list),
                inline=False
            )

            embed.set_footer(text=f"Solicitado por {ctx.author.name}", icon_url=ctx.author.avatar.url)

            # Botones de navegación
            buttons = View()

            if page_number > 0:
                prev_button = Button(label="◀️ Anterior", style=discord.ButtonStyle.primary, custom_id="prev")
                buttons.add_item(prev_button)

            if page_number < len(pages) - 1:
                next_button = Button(label="Siguiente ▶️", style=discord.ButtonStyle.primary, custom_id="next")
                buttons.add_item(next_button)

            # Botón de inicio
            if page_number != 0:
                start_button = Button(label="🔙 Inicio", style=discord.ButtonStyle.secondary, custom_id="start")
                buttons.add_item(start_button)

            return embed, buttons

        # Enviar la primera página
        current_page = 0
        embed, buttons = await send_page(current_page)
        message = await ctx.send(embed=embed, view=buttons)

        # Función para manejar la interacción de los botones
        async def button_callback(interaction):
            nonlocal current_page
            if interaction.user != ctx.author:
                return await interaction.response.send_message("No puedes usar estos botones.", ephemeral=True)

            # Asegurarse de que la interacción tiene custom_id
            if isinstance(interaction, discord.Interaction) and hasattr(interaction, 'custom_id'):
                if interaction.custom_id == "next" and current_page < len(pages) - 1:
                    current_page += 1
                elif interaction.custom_id == "prev" and current_page > 0:
                    current_page -= 1
                elif interaction.custom_id == "start":
                    current_page = 0

                embed, buttons = await send_page(current_page)
                await interaction.response.edit_message(embed=embed, view=buttons)
            else:
                await interaction.response.send_message("Interacción no válida.", ephemeral=True)

        # Añadir los callbacks a los botones
        for button in buttons.children:
            button.callback = button_callback

    async def send_command_help(self, command):
        """Muestra la ayuda detallada para un comando específico."""
        embed = discord.Embed(
            title=f"Comando: {command.name}",
            description=command.help or "Sin descripción",
            color=discord.Color.green()
        )
        embed.add_field(name="Uso", value=f"`{self.clean_prefix}{command.name} {command.signature}`", inline=False)
        if command.aliases:
            embed.add_field(name="Alias", value=", ".join(command.aliases), inline=False)
        await self.context.send(embed=embed)

    async def send_cog_help(self, cog):
        """Muestra la ayuda para una categoría específica."""
        embed = discord.Embed(
            title=f"Categoría: {cog.qualified_name}",
            description=cog.description or "Sin descripción",
            color=discord.Color.orange()
        )
        commands_list = [f"`{command.name}`: {command.help or 'Sin descripción'}" for command in cog.get_commands()]
        embed.add_field(name="Comandos", value="\n".join(commands_list), inline=False)
        await self.context.send(embed=embed)

# Configuración de la ayuda personalizada
async def setup(bot):
    bot.help_command = CustomHelpCommand()
