# chess_game.py
import discord
from discord.ext import commands
from discord import app_commands
import chess
import sqlite3

# قاموس لتحويل قطع الشطرنج إلى إيموجيات منسقة
EMOJI_BOARD = {
    'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',  # قطع بيضاء
    'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟',  # قطع سوداء
    '.': '⬛', '::': '⬜'
}

def render_board(board: chess.Board) -> str:
    """تحويل رقعة الشطرنج البرمجية إلى نص يحتوي على إيموجيات ديسكورد"""
    lines = []
    lines.append("⬛ 🇦 🇧 🇨 🇩 🇪 🇫 🇬 🇭")
    for row in range(8):
        line = f"{8 - row}️⃣ "
        for col in range(8):
            square = chess.square(col, 7 - row)
            piece = board.piece_at(square)
            if piece:
                line += EMOJI_BOARD[piece.symbol()] + " "
            else:
                if (row + col) % 2 == 0:
                    line += "⬜ "
                else:
                    line += "⬛ "
        lines.append(line)
    return "\n".join(lines)


# قائمة منسدلة لاختيار الحركة
class ChessMoveSelect(discord.ui.Select):
    def __init__(self, options, placeholder="♟️ Choose your move..."):
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        view: ChessView = self.view
        
        # التأكد من أن اللاعب صاحب الدور هو من يضغط
        current_player = view.white_player if view.board.turn == chess.WHITE else view.black_player
        if interaction.user != current_player:
            await interaction.response.send_message(
                view.cog.get_translated(interaction.user, "chess_not_your_turn"), 
                ephemeral=True
            )
            return

        # تطبيق الحركة المحددة
        move = chess.Move.from_uci(self.values[0])
        view.board.push(move)

        # التحقق من نهاية المباراة (كش ملك وفوز لاعب)
        if view.board.is_checkmate():
            view.clear_items()
            
            # تحديد الفائز والخاسر
            winner = interaction.user
            loser = view.black_player if winner == view.white_player else view.white_player
            
            # توزيع النقاط (+100 للفائز، +10 للخاسر)
            points_cog = view.cog.bot.get_cog("PointsSystem")
            if points_cog:
                await points_cog.add_points(interaction.guild.id, winner.id, 100)
                await points_cog.add_points(interaction.guild.id, loser.id, 10)

            win_text = view.cog.get_translated(interaction.user, "chess_win_msg").format(user=winner.mention)
            embed = discord.Embed(title="👑 Checkmate! Game Over", description=win_text, color=discord.Color.gold())
            embed.description += f"\n\n{render_board(view.board)}"
            await interaction.response.edit_message(embed=embed, view=view)
            return

        # التحقق من التعادل
        if view.board.is_game_over():
            view.clear_items()
            draw_text = view.cog.get_translated(interaction.user, "chess_draw_msg")
            embed = discord.Embed(title="🤝 Draw / انتهت المباراة", description=draw_text, color=discord.Color.light_grey())
            embed.description += f"\n\n{render_board(view.board)}"
            await interaction.response.edit_message(embed=embed, view=view)
            return

        # تحديث القائمة المنسدلة للحركات القادمة
        view.update_select_menu()
        await interaction.response.edit_message(embed=view.make_embed(interaction.user), view=view)


# واجهة إدارة اللعبة
class ChessView(discord.ui.View):
    def __init__(self, white_player: discord.Member, black_player: discord.Member, cog):
        super().__init__(timeout=300)
        self.white_player = white_player
        self.black_player = black_player
        self.cog = cog
        self.board = chess.Board()
        self.update_select_menu()

    def make_embed(self, userForLang: discord.Member):
        current_turn = self.white_player if self.board.turn == chess.WHITE else self.black_player
        color_text = "اللون الأبيض ⚪" if self.board.turn == chess.WHITE else "اللون الأسود ⚫"
        
        embed = discord.Embed(title="⚔️ Chess Match ⚔️", color=discord.Color.dark_red())
        embed.add_field(name="Player White ⚪", value=self.white_player.mention, inline=True)
        embed.add_field(name="Player Black ⚫", value=self.black_player.mention, inline=True)
        embed.add_field(name="Turn / الدور الحالي", value=f"{current_turn.mention} ({color_text})", inline=False)
        embed.description = f"\n{render_board(self.board)}"
        return embed

    def update_select_menu(self):
        self.clear_items()
        options = []
        legal_moves = list(self.board.legal_moves)[:25] 
        
        for move in legal_moves:
            move_str = move.uci()
            label = f"{move_str[:2]} ➡️ {move_str[2:]}"
            options.append(discord.SelectOption(label=label, value=move_str))

        if options:
            # نمرر نص الإرشاد المترجم
            placeholder_text = self.cog.get_translated(self.white_player, "chess_confirm_btn") # نص احتياطي
            self.add_item(ChessMoveSelect(options, placeholder="♟️ Choose your move..."))


# واجهة التأكيد والتذكير قبل الخصم والبدء
class ChessWarningView(discord.ui.View):
    def __init__(self, challenger: discord.Member, opponent: discord.Member, cog):
        super().__init__(timeout=60)
        self.challenger = challenger
        self.opponent = opponent
        self.cog = cog

        # إنشاء زر التأكيد
        confirm_label = self.cog.get_translated(challenger, "chess_confirm_btn")
        button = discord.ui.Button(label=confirm_label, style=discord.ButtonStyle.danger, emoji="⚔️")
        button.callback = self.confirm_callback
        self.add_item(button)

    async def confirm_callback(self, interaction: discord.Interaction):
        # التأكد من أن صاحب الأمر هو من يضغط للتأكيد
        if interaction.user != self.challenger:
            await interaction.response.send_message("❌ This confirmation is not for you!", ephemeral=True)
            return

        # خصم الـ 20 نقطة برمجياً لتفعيل الأمر
        points_cog = self.cog.bot.get_cog("PointsSystem")
        if points_cog:
            # الخصم بإضافة نقاط سالبة
            await points_cog.add_points(interaction.guild.id, self.challenger.id, -20)

        # تشغيل اللعبة رسمياً
        view = ChessView(self.challenger, self.opponent, self.cog)
        invite_msg = self.cog.get_translated(self.opponent, "chess_invite_msg").format(opponent=self.opponent.mention, user=self.challenger.mention)
        
        # تعديل الرسالة السابقة لبدء اللعبة
        await interaction.response.edit_message(content=invite_msg, embed=view.make_embed(interaction.user), view=view)


class ChessCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "points_database.db"
        self.init_db()

    def init_db(self):
        """إنشاء جدول لتخزين قنوات الشطرنج المخصصة"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chess_channels (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER
            )
        ''')
        conn.commit()
        conn.close()

    def get_translated(self, member: discord.Member, key: str) -> str:
        """جلب النص المترجم ديناميكياً"""
        translation_cog = self.bot.get_cog("TranslationSystem")
        if translation_cog:
            return translation_cog.get_text(member, key)
        return key

    def get_chess_channel(self, guild_id: int) -> int:
        """جلب القناة المخصصة للشطرنج في السيرفر"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT channel_id FROM chess_channels WHERE guild_id = ?", (guild_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

    def get_user_points(self, guild_id: int, user_id: int) -> int:
        """جلب نقاط العضو الحالية من قاعدة البيانات"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT points FROM user_points WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0

    @app_commands.command(name="chess", description="بدء تحدي مباراة شطرنج ضد عضو آخر في السيرفر")
    async def start_chess(self, interaction: discord.Interaction, opponent: discord.Member):
        if opponent == interaction.user:
            await interaction.response.send_message(self.get_translated(interaction.user, "chess_no_self"), ephemeral=True)
            return
        if opponent.bot:
            await interaction.response.send_message(self.get_translated(interaction.user, "chess_no_bot"), ephemeral=True)
            return

        guild_id = interaction.guild.id

        # 1. التحقق مما إذا كانت هناك قناة مخصصة للشطرنج واللعب فيها حصراً
        required_channel_id = self.get_chess_channel(guild_id)
        if required_channel_id and interaction.channel.id != required_channel_id:
            req_channel = interaction.guild.get_channel(required_channel_id)
            err_msg = self.get_translated(interaction.user, "chess_wrong_channel").format(channel=req_channel.mention if req_channel else "Unknown")
            await interaction.response.send_message(err_msg, ephemeral=True)
            return

        # 2. التحقق من رصيد اللاعب للتأكد من امتلاكه 20 نقطة على الأقل للعب
        user_points = self.get_user_points(guild_id, interaction.user.id)
        if user_points < 20:
            err_points = self.get_translated(interaction.user, "chess_no_points").format(points=user_points)
            await interaction.response.send_message(err_points, ephemeral=True)
            return

        # 3. إرسال واجهة التحذير والتأكيد قبل خصم النقاط والبدء
        warning_title = self.get_translated(interaction.user, "chess_warning_title")
        warning_desc = self.get_translated(interaction.user, "chess_warning_desc")
        
        embed = discord.Embed(title=warning_title, description=warning_desc, color=discord.Color.orange())
        view = ChessWarningView(interaction.user, opponent, self)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="chess_setup", description="[للإدارة] تحديد قناة مخصصة للعب مباريات الشطرنج")
    @app_commands.checks.has_permissions(administrator=True)
    async def chess_setup(self, interaction: discord.Interaction, channel: discord.TextChannel):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO chess_channels (guild_id, channel_id)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET channel_id = EXCLUDED.channel_id
        ''', (interaction.guild.id, channel.id))
        conn.commit()
        conn.close()

        success_msg = self.get_translated(interaction.user, "chess_setup_success").format(channel=channel.mention)
        await interaction.response.send_message(success_msg, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ChessCog(bot))