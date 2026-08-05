import discord
from discord import app_commands
from discord.ext import commands, tasks
import sqlite3
from datetime import datetime

class PointsSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_path = "points_database.db"
        self.init_db()
        self.weekly_announcer.start() # بدء مؤقت الإعلان الأسبوعي/الشهري تلقائياً

    def init_db(self):
        """إنشاء جداول قاعدة البيانات لضمان فصل السيرفرات وعدم تداخل النقاط"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # جدول النقاط: يربط بين السيرفر والعضو لمنع التداخل
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_points (
                guild_id INTEGER,
                user_id INTEGER,
                points INTEGER DEFAULT 0,
                weekly_points INTEGER DEFAULT 0,
                monthly_points INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            )
        ''')
        
        # جدول إعدادات السيرفر (تحديد قناة لوحة الصدارة)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                leaderboard_channel_id INTEGER
            )
        ''')
        conn.commit()
        conn.close()

    def get_translated_message(self, member: discord.Member, key: str) -> str:
        """جلب النص المترجم ديناميكياً من نظام الترجمة"""
        translation_cog = self.bot.get_cog("TranslationSystem")
        if translation_cog:
            return translation_cog.get_text(member, key)
        # نص احتياطي بسيط في حال لم يتم تحميل نظام الترجمة بعد
        fallback_messages = {
            "setup_success": "✅ Leaderboard channel configured successfully!",
            "no_points_data": "⚠️ No point data recorded for this server yet.",
            "leaderboard_footer": "Keep active to raise your rank!",
            "announcement_intro": "Congratulations to our most active members! 🚀",
            "points_word": "Points",
            "total_title": "Total Leaderboard",
            "weekly_title": "Weekly Leaderboard",
            "monthly_title": "Monthly Leaderboard"
        }
        return fallback_messages.get(key, key)

    async def add_points(self, guild_id: int, user_id: int, points_to_add: int):
        """دالة عامة لإضافة النقاط ومزامنتها مع الصدارة الأسبوعية والشهرية"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO user_points (guild_id, user_id, points, weekly_points, monthly_points)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET
                points = points + EXCLUDED.points,
                weekly_points = weekly_points + EXCLUDED.weekly_points,
                monthly_points = monthly_points + EXCLUDED.monthly_points
        ''', (guild_id, user_id, points_to_add, points_to_add, points_to_add))
        
        conn.commit()
        conn.close()

    # --- 1. احتساب نقاط الكلام والتفاعل في الشات ---
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        # إضافة نقطة واحدة عند التحدث في الشات
        await self.add_points(message.guild.id, message.author.id, 1)

    # --- 2. احتساب نقاط التفاعل مع البوت (استخدام الأوامر) ---
    @commands.Cog.listener()
    async def on_app_command_completion(self, interaction: discord.Interaction, command: app_commands.Command):
        # تجنب احتساب نقاط على أمر leaderboard نفسه لتفادي استغلال التكرار (Spam)
        if command.name == "leaderboard":
            return
            
        if interaction.guild:
            await self.add_points(interaction.guild.id, interaction.user.id, 10)

    # --- 3. أمر الإدارة لتفعيل وتحديد قناة المتصدرين ---
    @app_commands.command(name="points_setup", description="[Admin] Set leaderboard channel / [للإدارة] تحديد قناة المتصدرين")
    @app_commands.checks.has_permissions(administrator=True)
    async def points_setup(self, interaction: discord.Interaction, channel: discord.TextChannel):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO guild_settings (guild_id, leaderboard_channel_id)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET leaderboard_channel_id = EXCLUDED.leaderboard_channel_id
        ''', (interaction.guild.id, channel.id))
        
        conn.commit()
        conn.close()
        
        # استخدام رسالة التأكيد المترجمة وإدخال اسم القناة بداخلها
        raw_msg = self.get_translated_message(interaction.user, "setup_success")
        success_msg = raw_msg.replace("{channel}", channel.mention)
        
        await interaction.response.send_message(success_msg, ephemeral=True)

    # --- 4. أمر الأعضاء لرؤية لوحة الصدارة في أي وقت ---
    @app_commands.command(name="leaderboard", description="View current server leaderboard / عرض متصدري السيرفر")
    @app_commands.choices(type=[
        app_commands.Choice(name="🏆 Total / الإجمالية", value="total"),
        app_commands.Choice(name="📅 Weekly / الأسبوعية", value="weekly"),
        app_commands.Choice(name="🌙 Monthly / الشهرية", value="monthly")
    ])
    async def leaderboard(self, interaction: discord.Interaction, type: str):
        await interaction.response.defer()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        column = "points" if type == "total" else "weekly_points" if type == "weekly" else "monthly_points"
        
        cursor.execute(f'''
            SELECT user_id, {column} FROM user_points
            WHERE guild_id = ? AND {column} > 0
            ORDER BY {column} DESC LIMIT 10
        ''', (interaction.guild.id,))
        
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            await interaction.followup.send(self.get_translated_message(interaction.user, "no_points_data"))
            return

        # تحديد العنوان المترجم بناءً على نوع الصدارة
        title_key = f"{type}_title"
        title_text = self.get_translated_message(interaction.user, title_key)
        points_word = self.get_translated_message(interaction.user, "points_word")

        embed = discord.Embed(
            title=f"🏆 {title_text} - {interaction.guild.name}",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )
        
        description = ""
        medals = ["🥇", "🥈", "🥉", "👤", "👤", "👤", "👤", "👤", "👤", "👤"]
        
        for index, (user_id, points) in enumerate(results):
            member = interaction.guild.get_member(user_id)
            name = member.mention if member else f"User left ({user_id})"
            description += f"{medals[index]} **#{index+1}** {name} ┃ **{points}** {points_word}\n"
            
        embed.description = description
        embed.set_footer(text=self.get_translated_message(interaction.user, "leaderboard_footer"))
        await interaction.followup.send(embed=embed)

    # --- 5. نظام الإعلان الدوري والتلقائي في القناة المحددة ---
    @tasks.loop(hours=24)
    async def weekly_announcer(self):
        now = datetime.now()
        is_sunday = now.weekday() == 6 # يوم الأحد
        is_first_of_month = now.day == 1
        
        if not (is_sunday or is_first_of_month):
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT guild_id, leaderboard_channel_id FROM guild_settings")
        guilds_settings = cursor.fetchall()
        
        for guild_id, channel_id in guilds_settings:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                continue
                
            channel = guild.get_channel(channel_id)
            if not channel:
                continue
                
            if is_sunday:
                await self.send_periodic_leaderboard(guild, channel, "weekly_points", "weekly_title")
                cursor.execute("UPDATE user_points SET weekly_points = 0 WHERE guild_id = ?", (guild_id,))
                
            if is_first_of_month:
                await self.send_periodic_leaderboard(guild, channel, "monthly_points", "monthly_title")
                cursor.execute("UPDATE user_points SET monthly_points = 0 WHERE guild_id = ?", (guild_id,))
                
        conn.commit()
        conn.close()

    async def send_periodic_leaderboard(self, guild, channel, column, title_key):
        """دالة مساعدة لصياغة رسالة الإعلان التلقائي المترجمة"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(f"SELECT user_id, {column} FROM user_points WHERE guild_id = ? AND {column} > 0 ORDER BY {column} DESC LIMIT 5", (guild.id,))
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            return
            
        # بما أن هذا الإعلان عام في قناة مشتركة، سنعتمد لغة السيرفر الافتراضية (الإنجليزية) أو العربية بناءً على ما تفضله. هنا سنستخدم دالة الترجمة مستعينين بـ guild.me للحصول على لغة افتراضية مناسبة للقناة
        title_text = self.get_translated_message(guild.me, title_key)
        intro_text = self.get_translated_message(guild.me, "announcement_intro")
        points_word = self.get_translated_message(guild.me, "points_word")

        embed = discord.Embed(title=f"🎉 {title_text} 🎉", color=discord.Color.purple(), timestamp=datetime.utcnow())
        description = f"{intro_text}\n\n"
        for index, (user_id, points) in enumerate(results):
            member = guild.get_member(user_id)
            name = member.mention if member else f"Member ({user_id})"
            description += f"**#{index+1}** {name} ┃ **{points}** {points_word} ✨\n"
        embed.description = description
        await channel.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(PointsSystem(bot))