# xo_game.py
import discord
from discord.ext import commands
from discord import app_commands
import random

# فئة الأزرار الخاصة بلوحة اللعبة
class XOButton(discord.ui.Button):
    def __init__(self, x: int, y: int):
        # 👑 التعديل هنا: استخدام discord.ButtonStyle بدلاً من discord.Style
        super().__init__(style=discord.ButtonStyle.secondary, label="‌", row=y)
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction):
        view: XOView = self.view
        
        current_player = view.player1 if view.turn == "X" else view.player2
        
        if current_player == "bot":
            await interaction.response.send_message("🤖 البوت يفكر حالياً، انتظر دورك!", ephemeral=True)
            return

        if interaction.user != current_player:
            await interaction.response.send_message("❌ هذا ليس دورك في اللعب!", ephemeral=True)
            return

        # وضع العلامة على الزر وتعديل اللون بأمان
        self.label = view.turn
        self.style = discord.ButtonStyle.danger if view.turn == "X" else discord.ButtonStyle.success
        self.disabled = True
        view.board[self.y][self.x] = view.turn

        if view.check_winner():
            view.disable_all_buttons()
            embed = discord.Embed(
                title="🎉 نهاية المباراة!",
                description=f"🏆 كفووو! الفائز هو {interaction.user.mention} ({view.turn})",
                color=discord.Color.gold()
            )
            await interaction.response.edit_message(embed=embed, view=view)
            return

        if view.check_tie():
            view.disable_all_buttons()
            embed = discord.Embed(title="🤝 تعادل!", description="انتهت المباراة بالتعادل بين الطرفين!", color=discord.Color.light_grey())
            await interaction.response.edit_message(embed=embed, view=view)
            return

        view.turn = "O" if view.turn == "X" else "X"
        
        if view.turn == "O" and view.player2 == "bot":
            view.bot_move()
            if view.check_winner():
                view.disable_all_buttons()
                embed = discord.Embed(title="🤖 فاز البوت!", description="حظاً أوفر في المرة القادمة، لقد انتصر البوت عليك!", color=discord.Color.red())
                await interaction.response.edit_message(embed=embed, view=view)
                return
            if view.check_tie():
                view.disable_all_buttons()
                embed = discord.Embed(title="🤝 تعادل!", description="انتهت المباراة بالتعادل مع البوت!", color=discord.Color.light_grey())
                await interaction.response.edit_message(embed=embed, view=view)
                return
            view.turn = "X"

        await interaction.response.edit_message(embed=view.make_embed(), view=view)


class XOView(discord.ui.View):
    def __init__(self, player1: discord.Member, player2):
        super().__init__(timeout=180)
        self.player1 = player1
        self.player2 = player2
        self.turn = "X"
        self.board = [[" " for _ in range(3)] for _ in range(3)]

        for y in range(3):
            for x in range(3):
                self.add_item(XOButton(x, y))

    def make_embed(self):
        p2_mention = "🤖 الذكاء الاصطناعي (البوت)" if self.player2 == "bot" else self.player2.mention
        current = self.player1.mention if self.turn == "X" else p2_mention
        
        embed = discord.Embed(title="❌ لعبة X OR O ⭕", color=discord.Color.blue())
        embed.add_field(name="اللاعب الأول (X)", value=self.player1.mention, inline=True)
        embed.add_field(name="اللاعب الثاني (O)", value=p2_mention, inline=True)
        embed.add_field(name="الدور الحالي لـ", value=f"➡️ {current} ({self.turn})", inline=False)
        return embed

    def bot_move(self):
        empty_buttons = [button for button in self.children if isinstance(button, XOButton) and not button.disabled]
        if empty_buttons:
            move = random.choice(empty_buttons)
            move.label = "O"
            move.style = discord.ButtonStyle.success # 👑 تم التعديل هنا أيضاً
            move.disabled = True
            self.board[move.y][move.x] = "O"

    def check_winner(self):
        b = self.board
        for i in range(3):
            if b[i][0] == b[i][1] == b[i][2] != " ": return True
            if b[0][i] == b[1][i] == b[2][i] != " ": return True
        if b[0][0] == b[1][1] == b[2][2] != " ": return True
        if b[0][2] == b[1][1] == b[2][0] != " ": return True
        return False

    def check_tie(self):
        return all(cell != " " for row in self.board for cell in row)

    def disable_all_buttons(self):
        for button in self.children:
            if isinstance(button, XOButton):
                button.disabled = True


class XOGameCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="xo", description="بدء مباراة X OR O ضد صديق أو ضد البوت")
    async def xo_game(self, interaction: discord.Interaction, opponent: discord.Member = None):
        if opponent is None:
            view = XOView(interaction.user, "bot")
            await interaction.response.send_message(embed=view.make_embed(), view=view)
        else:
            if opponent == interaction.user:
                await interaction.response.send_message("❌ لا يمكنك اللعب ضد نفسك يا ذكي!", ephemeral=True)
                return
            if opponent.bot:
                await interaction.response.send_message("❌ لا يمكنك تحدي بوتات أخرى، إذا أردت اللعب ضد الذكاء الاصطناعي اترك خانة الخصم فارغة.", ephemeral=True)
                return

            view = XOView(interaction.user, opponent)
            await interaction.response.send_message(
                content=f"⚔️ {opponent.mention}، لقد تم تحديك في مباراة X o O من قبل {interaction.user.mention}!",
                embed=view.make_embed(), 
                view=view
            )

async def setup(bot):
    await bot.add_cog(XOGameCog(bot))