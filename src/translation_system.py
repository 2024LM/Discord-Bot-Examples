import discord
from discord import app_commands
from discord.ext import commands
import json
import os

class TranslationSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.translations = {}
        self.load_translations()

    def load_translations(self):
        """تحميل نصوص اللغات من ملف JSON بشكل ديناميكي"""
        if os.path.exists("locale.json"):
            with open("locale.json", "r", encoding="utf-8") as f:
                self.translations = json.load(f)
            print(f"✅ تم تحميل اللغات بنجاح: {list(self.translations.keys())}")
        else:
            print("⚠️ ملف locale.json غير موجود!")

    def get_text(self, member: discord.Member, key: str) -> str:
        """دالة ذكية لمعرفة لغة العضو بناءً على رتبته وجلب النص الصحيح"""
        # افتراضياً، إذا لم يكن لديه رتبة لغة، نستخدم الإنجليزية أو العربية كاحتياطية
        user_lang = "en" 
        
        # البحث في رتب العضو عن رتبة تطابق أسماء اللغات المعرفة في الـ JSON
        for role in member.roles:
            for lang_code, lang_data in self.translations.items():
                if role.name == lang_data.get("role_name"):
                    user_lang = lang_code
                    break
        
        # جلب النص المطلوب بناءً على اللغة المحددة
        lang_dict = self.translations.get(user_lang, self.translations.get("en", {}))
        return lang_dict.get(key, f"Missing Translation: {key}")

    async def create_language_roles(self, guild: discord.Guild):
        """دالة لإنشاء رتب اللغات تلقائياً في السيرفر إذا لم تكن موجودة"""
        for lang_code, lang_data in self.translations.items():
            role_name = lang_data.get("role_name")
            # التحقق مما إذا كانت الرتبة موجودة مسبقاً لمنع التكرار
            existing_role = discord.utils.get(guild.roles, name=role_name)
            if not existing_role:
                try:
                    await guild.create_role(
                        name=role_name, 
                        mentionable=True, 
                        reason="رتبة لغة تلقائية للبوت"
                    )
                    print(f"✨ تم إنشاء رتبة لغة جديدة: {role_name} في سيرفر {guild.name}")
                except discord.Forbidden:
                    print(f"❌ لا توجد صلاحيات لإنشاء الرتب في سيرفر {guild.name}")

    # --- أحدث 1: تشغيل فحص الرتب عند انضمام البوت لسيرفر جديد ---
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await self.create_language_roles(guild)

    # --- أحدث 2: فحص الرتب لجميع السيرفرات المتصل بها البوت عند إقلاعه ---
    @commands.Cog.listener()
    async def on_ready():
        # هذه الدالة اختيارية ويمكن استدعاؤها في main.py لمزامنة الرتب عند الإقلاع
        pass

    # --- أمر مائل لتغيير اللغة ---
    @app_commands.command(name="language", description="تغيير لغة البوت الخاصة بك عن طريق تعيين رتبة اللغة")
    @app_commands.choices(lang=[
        app_commands.Choice(name="العربية 🇸🇦", value="ar"),
        app_commands.Choice(name="English 🇬🇧", value="en"),
        app_commands.Choice(name="Русский 🇷🇺", value="ru")
    ])
    async def change_language(self, interaction: discord.Interaction, lang: str):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        member = interaction.user

        # تأكيد تحميل الترجمات للتأكد من وجود اللغة المطلوبة
        self.load_translations()
        if lang not in self.translations:
            await interaction.followup.send("⚠️ هذه اللغة غير متوفرة حالياً في ملف الإعدادات.")
            return

        # التأكد من وجود رتب اللغات في السيرفر أولاً وإنشائها إن نقصت
        await self.create_language_roles(guild)

        # 1. إزالة جميع رتب اللغات السابقة المخزنة في الـ JSON من العضو
        roles_to_remove = []
        for lang_code, lang_data in self.translations.items():
            role = discord.utils.get(guild.roles, name=lang_data.get("role_name"))
            if role and role in member.roles:
                roles_to_remove.append(role)
        
        if roles_to_remove:
            await member.remove_roles(*roles_to_remove)

        # 2. إضافة رتبة اللغة الجديدة المطلوبة للعضو
        target_role_name = self.translations[lang].get("role_name")
        target_role = discord.utils.get(guild.roles, name=target_role_name)
        
        if target_role:
            await member.add_roles(target_role)
            # جلب رسالة النجاح باللغة الجديدة التي اختارها المستخدم فوراً!
            success_message = self.get_text(member, "language_changed")
            await interaction.followup.send(success_message)
        else:
            await interaction.followup.send("❌ حدث خطأ أثناء محاولة العثور على رتبة اللغة المحددة.")

async def setup(bot: commands.Bot):
    await bot.add_cog(TranslationSystem(bot))