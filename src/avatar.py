# avatar.py
import discord
from discord import app_commands
from discord.ext import commands
import sqlite3

class AvatarCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "points_database.db"

    def get_translated_text(self, member: discord.Member, key: str) -> str:
        """جلب النص المترجم ديناميكياً بناءً على رتبة العضو"""
        translation_cog = self.bot.get_cog("TranslationSystem")
        if translation_cog:
            return translation_cog.get_text(member, key)
        # نصوص احتياطية افتراضية بالإنجليزية
        fallbacks = {
            "avatar_title": "👤 User Profile: {name}",
            "account_link": "🔗 Quick Account Link",
            "created_at": "📅 Account Created At",
            "joined_at": "📥 Joined Server At",
            "roles_display": "🏆 Roles & Promotions",
            "user_points_label": "📊 Interaction Points",
            "points_suffix": "{points} points",
            "current_lang_label": "🌐 User's Current Language",
            "unknown": "Unknown",
            "no_roles": "No roles at the moment",
            "requested_by": "Requested by: {name}",
            "developer_badge": "👑 [Verified Bot Developer]"
        }
        return fallbacks.get(key, key)

    def get_user_points(self, guild_id: int, user_id: int) -> int:
        """جلب نقاط العضو الكلية من قاعدة بيانات نظام النقاط"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT points FROM user_points WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else 0
        except Exception:
            return 0

    @app_commands.command(name="avatar", description="يعرض الصورة الشخصية ومعلومات الحساب كاملة مع نقاط التفاعل")
    async def avatar(self, interaction: discord.Interaction, member: discord.Member = None):
        try:
            # إذا لم يتم تحديد عضو، يتم عرض معلومات الشخص الذي كتب الأمر
            member = member or interaction.user
            guild = interaction.guild

            # 1. معالجة التواريخ بأمان ومترجمة
            unknown_text = self.get_translated_text(interaction.user, "unknown")
            
            if member.created_at:
                created_timestamp = int(member.created_at.timestamp())
                created_at = f"<t:{created_timestamp}:F> (<t:{created_timestamp}:R>)"
            else:
                created_at = unknown_text

            if member.joined_at:
                joined_timestamp = int(member.joined_at.timestamp())
                joined_at = f"<t:{joined_timestamp}:F> (<t:{joined_timestamp}:R>)"
            else:
                joined_at = unknown_text
            
            # 2. جلب الأدوار (الرتب) التي يشغلها العضو باستثناء @everyone
            roles = [role.mention for role in member.roles if role.name != "@everyone"]
            no_roles_text = self.get_translated_text(interaction.user, "no_roles")
            roles_display = ", ".join(roles) if roles else no_roles_text

            # 3. جلب نقاط تفاعل العضو من قاعدة البيانات
            points = self.get_user_points(guild.id, member.id)
            points_suffix = self.get_translated_text(interaction.user, "points_suffix")
            points_display = points_suffix.format(points=points)

            # 4. التحقق من لغة العضو الحالية لعرضها في البروفايل
            translation_cog = self.bot.get_cog("TranslationSystem")
            current_lang = "English 🇬🇧" # الافتراضي
            if translation_cog:
                # التحقق من الرتبة التي يمتلكها العضو لمعرفة لغته
                for role in member.roles:
                    for lang_code, lang_data in translation_cog.translations.items():
                        if role.name == lang_data.get("role_name"):
                            current_lang = role.name
                            break

            # 5. التحقق مما إذا كان هذا العضو هو مبرمج ومالك البوت الفعلي لإضافة الرمز المميز له
            is_developer = await self.bot.is_owner(member)
            dev_badge = ""
            if is_developer:
                dev_badge = f" {self.get_translated_text(interaction.user, 'developer_badge')}"

            # 6. بناء بطاقة المعلومات (Embed)
            avatar_title_raw = self.get_translated_text(interaction.user, "avatar_title")
            embed = discord.Embed(
                title=avatar_title_raw.format(name=member.name) + dev_badge,
                color=member.color if member.color else discord.Color.blue()
            )
            
            embed.add_field(name=self.get_translated_text(interaction.user, "account_link"), value=f"{member.mention} (ID: `{member.id}`)", inline=False)
            embed.add_field(name=self.get_translated_text(interaction.user, "user_points_label"), value=f"🏆 **{points_display}**", inline=True)
            embed.add_field(name=self.get_translated_text(interaction.user, "current_lang_label"), value=f"💬 **{current_lang}**", inline=True)
            embed.add_field(name=self.get_translated_text(interaction.user, "created_at"), value=created_at, inline=False)
            embed.add_field(name=self.get_translated_text(interaction.user, "joined_at"), value=joined_at, inline=False)
            embed.add_field(name=self.get_translated_text(interaction.user, "roles_display"), value=roles_display, inline=False)
            
            # وضع الصورة الشخصية
            if member.display_avatar:
                embed.set_image(url=member.display_avatar.url)
            
            footer_raw = self.get_translated_text(interaction.user, "requested_by")
            embed.set_footer(text=footer_raw.format(name=interaction.user.name), icon_url=interaction.user.display_avatar.url)

            # إرسال البطاقة
            await interaction.response.send_message(embed=embed)
            
        except Exception as error:
            print(f"حدث خطأ في أمر الآفاتار: {error}")
            await interaction.response.send_message(f"❌ Error: `{error}`", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AvatarCog(bot))