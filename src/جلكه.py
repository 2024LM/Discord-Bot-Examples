# جلكه.py
import discord
from discord.ext import commands
from discord import app_commands

class JalkaButton(discord.ui.Button):
    def __init__(self, x: int, y: int):
        super().__init__(style=discord.ButtonStyle.secondary, label="‌", row=y)
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction):
        view: JalkaView = self.view
        current_player = view.player1 if view.turn == "🔴" else view.player2

        if interaction.user != current_player:
            await interaction.response.send_message("❌ هذا ليس دورك في اللعب!", ephemeral=True)
            return

        # --- المرحلة الأولى: وضع القطع الثلاث (Placement Phase) ---
        if view.phase == "place":
            if view.board[self.y][self.x] != " ":
                await interaction.response.send_message("❌ هذا المربع ممتلئ بالفعل!", ephemeral=True)
                return

            # وضع القطعة
            view.board[self.y][self.x] = view.turn
            self.label = view.turn
            self.style = discord.ButtonStyle.danger if view.turn == "🔴" else discord.ButtonStyle.primary

            if view.turn == "🔴":
                view.p1_placed += 1
                view.turn = "🔵"
            else:
                view.p2_placed += 1
                view.turn = "🔴"

            # الانتقال لمرحلة التحريك إذا تم وضع جميع القطع (3 لكل لاعب)
            if view.p1_placed == 3 and view.p2_placed == 3:
                view.phase = "move"

        # --- المرحلة الثانية: اختيار القطعة وتحريكها (Movement Phase) ---
        elif view.phase == "move":
            # إذا لم يختر اللاعب قطعة ليحركها بعد
            if view.selected_piece == None:
                if view.board[self.y][self.x] != view.turn:
                    await interaction.response.send_message("❌ يجب أن تختار إحدى قطعك أولاً ليتم تحريكها!", ephemeral=True)
                    return
                
                view.selected_piece = (self.x, self.y)
                await interaction.response.send_message(f"🔄 اخترت القطعة في الصف {self.y+1} والعمود {self.x+1}. الآن اضغط على مربع فارغ مجاور لتحريكها إليه.", ephemeral=True)
                return
            else:
                # إذا ضغط على نفس القطعة مجدداً، يلغي الاختيار
                old_x, old_y = view.selected_piece
                if old_x == self.x and old_y == self.y:
                    view.selected_piece = None
                    await interaction.response.send_message("🔄 تم إلغاء اختيار القطعة. اختر قطعة أخرى.", ephemeral=True)
                    return

                # التحقق أن المربع الجديد فارغ
                if view.board[self.y][self.x] != " ":
                    await interaction.response.send_message("❌ المربع المستهدف ليس فارغاً!", ephemeral=True)
                    return

                # التحقق من أن الحركة مجاورة قانونياً (يمكن التحرك لأي مربع مجاور أفقياً أو عمودياً أو قطرياً)
                if abs(old_x - self.x) > 1 or abs(old_y - self.y) > 1:
                    await interaction.response.send_message("❌ يمكنك تحريك القطعة خطوة واحدة فقط للمربعات المجاورة المتصلة بها!", ephemeral=True)
                    return

                # تنفيذ النقل البرمجي
                view.board[old_y][old_x] = " "
                view.board[self.y][self.x] = view.turn
                view.selected_piece = None

                # تحديث الأزرار بصرياً
                view.refresh_buttons_styles()

                # تبديل الدور
                view.turn = "🔵" if view.turn == "🔴" else "🔴"

        # فحص الفوز بعد كل حركة
        if view.check_winner():
            view.disable_all_buttons()
            winner = view.player1 if view.turn == "🔵" else view.player2 # الفائز هو من لعب الحركة الأخيرة
            embed = discord.Embed(
                title="🎉 نهاية مباراة الجلكة التراثية!",
                description=f"🏆 كفووو! الفائز هو {winner.mention} بعد تشكيل خط مستقيم كامل!",
                color=discord.Color.gold()
            )
            await interaction.response.edit_message(embed=embed, view=view)
            return

        # تحديث الرسالة بالوضع الجديد
        await interaction.response.edit_message(embed=view.make_embed(), view=view)


class JalkaView(discord.ui.View):
    def __init__(self, player1: discord.Member, player2: discord.Member):
        super().__init__(timeout=240)
        self.player1 = player1
        self.player2 = player2
        self.turn = "🔴"  # اللاعب الأول يبدأ بـ الأحمر
        self.phase = "place" # المراحل: 'place' للوضع، 'move' للتحريك
        self.p1_placed = 0
        self.p2_placed = 0
        self.selected_piece = None # لتخزين إحداثيات القطعة المراد نقلها
        self.board = [[" " for _ in range(3)] for _ in range(3)]

        # بناء رقعة الـ 3x3
        for y in range(3):
            for x in range(3):
                self.add_item(JalkaButton(x, y))

    def make_embed(self):
        current = self.player1.mention if self.turn == "🔴" else self.player2.mention
        phase_text = " وضع القطع الثلاث بالتناوب" if self.phase == "place" else " تحريك قطعة واحدة إلى مربع مجاور فارغ لعمل خط"
        
        embed = discord.Embed(title="🎮 لعبة الجلكة التراثية (Three Men's Morris)", color=discord.Color.dark_magenta())
        embed.add_field(name="اللاعب الأول (🔴)", value=self.player1.mention, inline=True)
        embed.add_field(name="اللاعب الثاني (🔵)", value=self.player2.mention, inline=True)
        embed.add_field(name="المرحلة الحالية", value=f"ℹ️ **{phase_text}**", inline=False)
        embed.add_field(name="الدور الحالي لـ", value=f"➡️ {current} ({self.turn})", inline=False)
        return embed

    def refresh_buttons_styles(self):
        """إعادة رسم أشكال وألوان الأزرار بناءً على مصفوفة اللعبة عند التحريك"""
        for button in self.children:
            if isinstance(button, JalkaButton):
                cell_content = self.board[button.y][button.x]
                button.label = cell_content
                if cell_content == "🔴":
                    button.style = discord.ButtonStyle.danger
                elif cell_content == "🔵":
                    button.style = discord.ButtonStyle.primary
                else:
                    button.label = "‌"
                    button.style = discord.ButtonStyle.secondary

    def check_winner(self):
        b = self.board
        # فحص الأسطر والأعمدة والقطرين
        for i in range(3):
            if b[i][0] == b[i][1] == b[i][2] != " ": return True
            if b[0][i] == b[1][i] == b[2][i] != " ": return True
        if b[0][0] == b[1][1] == b[2][2] != " ": return True
        if b[0][2] == b[1][1] == b[2][0] != " ": return True
        return False

    def disable_all_buttons(self):
        for button in self.children:
            if isinstance(button, JalkaButton):
                button.disabled = True


class JalkaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="جلكه", description="بدء تحدي لعبة الجلكة التراثية العراقية ضد صديق")
    async def start_jalka(self, interaction: discord.Interaction, opponent: discord.Member):
        if opponent == interaction.user:
            await interaction.response.send_message("❌ لا يمكنك تحدي نفسك في الجلكة!", ephemeral=True)
            return
        if opponent.bot:
            await interaction.response.send_message("❌ لا يمكنك اللعب ضد البوتات في هذه اللعبة التراثية!", ephemeral=True)
            return

        view = JalkaView(interaction.user, opponent)
        await interaction.response.send_message(
            content=f"⚔️ {opponent.mention}، لقد تم تحديك في لعبة **الجلكة** من قبل {interaction.user.mention}! من سيصنع الخط أولاً؟",
            embed=view.make_embed(),
            view=view
        )

async def setup(bot):
    await bot.add_cog(JalkaCog(bot))