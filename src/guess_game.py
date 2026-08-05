# guess_game.py
import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import random
import time

class GuessGameCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.json_file = "game_data.json"
        self.game_data = self.load_game_data()
        self.last_guess_time = {} # قاموس لحفظ توقيت آخر تخمين لكل عضو لمنع التكرار

    def load_game_data(self):
        if os.path.exists(self.json_file):
            try:
                with open(self.json_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"خطأ في قراءة ملف اللعبة: {e}")
                return {}
        return {}

    def save_game_data(self):
        try:
            with open(self.json_file, "w", encoding="utf-8") as f:
                json.dump(self.game_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"خطأ في حفظ ملف اللعبة: {e}")

    def get_translated(self, member: discord.Member, key: str) -> str:
        """جلب النص المترجم ديناميكياً"""
        translation_cog = self.bot.get_cog("TranslationSystem")
        if translation_cog:
            return translation_cog.get_text(member, key)
        return key

    # 🛠️ أمر المشرفين لتهيئة اللعبة وتحديد القناة والرتبة
    @app_commands.command(name="setup_game", description="[Admin] Set guessing game channel / [للإدارة] إعداد لعبة التخمين")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_game(self, interaction: discord.Interaction, channel: discord.TextChannel, role: discord.Role):
        server_id = str(interaction.guild_id)
        secret_number = random.randint(1, 1000)

        self.game_data[server_id] = {
            "channel_id": channel.id,
            "role_id": role.id,
            "secret_number": secret_number,
            "active": True
        }
        self.save_game_data()

        success_title = "🎮"
        success_desc = self.get_translated(interaction.user, "guess_setup_success").format(channel=channel.mention, role=role.mention)
        
        embed = discord.Embed(
            title=success_title,
            description=success_desc + f"\n\n**1 - 1000 👇**",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
        
        # إرسال رسالة افتتاحية مترجمة في قناة اللعبة نفسها
        announcement_text = self.get_translated(interaction.user, "guess_start_announcement")
        await channel.send(announcement_text)

    # 👁️ مراقبة الرسائل المكتوبة في قناة اللعبة بشكل دائم
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        server_id = str(message.guild.id)

        # التحقق إذا كانت اللعبة مفعلة في هذا السيرفر
        if server_id not in self.game_data or not self.game_data[server_id].get("active"):
            return

        # التحقق إذا كانت الرسالة في القناة المخصصة للعبة فقط
        if message.channel.id != self.game_data[server_id]["channel_id"]:
            return

        # 🔢 الشرط: البوت لا يلتفت إلا إذا كانت الرسالة عبارة عن رقم فقط
        if not message.content.isdigit():
            return

        # ⏱️ نظام الحد من التكرار (Cooldown) المترجم والذكي (ثانيتان)
        current_time = time.time()
        user_id = message.author.id
        
        if user_id in self.last_guess_time:
            time_passed = current_time - self.last_guess_time[user_id]
            if time_passed < 2.0: # إذا لم يمر ثانيتين
                try:
                    await message.delete() # حذف رسالة العضو فوراً لمنع السبام
                except discord.Forbidden:
                    pass # تخطي في حال عدم امتلاك صلاحية حذف الرسائل
                
                # إرسال تحذير مؤقت للعضو في الخاص لتجنب تشويه الشات
                cooldown_msg = self.get_translated(message.author, "guess_cooldown")
                try:
                    await message.author.send(cooldown_msg)
                except discord.Forbidden:
                    pass
                return

        # تحديث وقت آخر تخمين للعضو
        self.last_guess_time[user_id] = current_time

        # معالجة التخمين
        guess = int(message.content)
        secret_number = self.game_data[server_id]["secret_number"]
        role_id = self.game_data[server_id]["role_id"]
        role = message.guild.get_role(role_id)
        points_cog = self.bot.get_cog("PointsSystem")

        # 1. التخمين صحيح (الفوز!)
        if guess == secret_number:
            await message.add_reaction("🎉")
            
            # منح الرتبة للفائز
            if role:
                try:
                    await message.author.add_roles(role)
                    role_msg = f"🏆 {role.mention}"
                except:
                    role_msg = self.get_translated(message.author, "role_err")
            else:
                role_msg = self.get_translated(message.author, "role_missing")

            # إضافة 100 نقطة للفائز
            if points_cog:
                await points_cog.add_points(message.guild.id, message.author.id, 100)

            win_title = self.get_translated(message.author, "guess_win_title")
            win_desc = self.get_translated(message.author, "guess_win_desc").format(
                user=message.author.mention, 
                number=secret_number, 
                role_msg=role_msg
            )

            embed = discord.Embed(
                title=win_title,
                description=win_desc,
                color=discord.Color.gold()
            )
            await message.channel.send(embed=embed)

            # توليد رقم سري جديد تلقائياً لتبدأ جولة جديدة
            new_secret = random.randint(1, 1000)
            self.game_data[server_id]["secret_number"] = new_secret
            self.save_game_data()
            
            new_round_msg = self.get_translated(message.author, "guess_new_round")
            await message.channel.send(new_round_msg)

        # 2. إذا كان الرقم المدخل أكبر من الرقم السري (الخسارة/محاولة خاطئة)
        elif guess > secret_number:
            # إضافة نقطتين فقط للمحاولة الخاطئة دون ذكر ذلك في الرسالة
            if points_cog:
                await points_cog.add_points(message.guild.id, message.author.id, 2)
                
            too_high_text = self.get_translated(message.author, "guess_too_high").format(guess=guess)
            await message.reply(too_high_text)

        # 3. إذا كان الرقم المدخل أقل من الرقم السري (الخسارة/محاولة خاطئة)
        else:
            # إضافة نقطتين فقط للمحاولة الخاطئة دون ذكر ذلك في الرسالة
            if points_cog:
                await points_cog.add_points(message.guild.id, message.author.id, 2)
                
            too_low_text = self.get_translated(message.author, "guess_too_low").format(guess=guess)
            await message.reply(too_low_text)


async def setup(bot):
    await bot.add_cog(GuessGameCog(bot))