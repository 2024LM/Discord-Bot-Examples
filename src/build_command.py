import discord
from discord import app_commands
from discord.ext import commands

class BuildServerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # --- أمر بناء وهيكلة السيرفر الاحترافي تلقائياً ---
    @app_commands.command(name="build_server", description="يبني السيرفر بالكامل مع الفئات والقنوات والمنتديات والإيموجي فوراً")
    @app_commands.checks.has_permissions(administrator=True)
    async def build_server(self, interaction: discord.Interaction):
        # الرد الفوري والسريع جداً لتجنب انتهاء مهلة الـ 3 ثوانٍ
        await interaction.response.send_message("⚙️ **جاري البدء في بناء وتنسيق قنوات السيرفر، يرجى الانتظار قليلاً...**", ephemeral=True)
        guild = interaction.guild

        try:
            # --- 1. فئة المعلومات العامة ---
            info_category = await guild.create_category(name="📢 INFO & NEWS")
            
            await guild.create_text_channel(name="📌┃rules", category=info_category)
            
            # إنشاء القنوات النصية بشكل مستقر تماماً دون المعامل 'type' المسبب للخطأ
            await guild.create_text_channel(
                name="📢┃announcements", 
                category=info_category
            )
            await guild.create_text_channel(
                name="🌐┃global-news", 
                category=info_category
            )
            
            await guild.create_text_channel(name="🚀┃update-log", category=info_category)
            await guild.create_text_channel(name="🎉┃giveaways", category=info_category)

            # --- 2. فئة قنوات الدردشة والشات باللغات ---
            chat_category = await guild.create_category(name="💬 CHAT ROOMS")
            await guild.create_text_channel(name="🌍┃global-chat", category=chat_category)
            await guild.create_text_channel(name="🇸🇦┃شات-عربي", category=chat_category)
            await guild.create_text_channel(name="🇬🇧┃english-chat", category=chat_category)
            await guild.create_text_channel(name="🇷🇺┃чат-русский", category=chat_category)

            # --- 3. فئة منطقة الألعاب والميمز ---
            play_category = await guild.create_category(name="🎮 PLAYGROUND")
            await guild.create_text_channel(name="🤖┃bot-commands", category=play_category)
            await guild.create_text_channel(name="🎮┃games", category=play_category)
            await guild.create_text_channel(name="📸┃daily-memes", category=play_category)
            
            # إنشاء قنوات المنتديات بالطريقة الرسمية والمضمونة
            await guild.create_forum_channel(name="📝┃forum-articles", category=play_category)
            await guild.create_forum_channel(name="✨┃تجارب-الأعضاء", category=play_category)

            # --- 4. فئة الدعم والبلاغات ---
            support_category = await guild.create_category(name="🤝 SUPPORT")
            await guild.create_text_channel(name="💡┃suggestions", category=support_category)
            await guild.create_text_channel(name="🎫┃open-ticket", category=support_category)
            await guild.create_text_channel(name="🚨┃users-reports", category=support_category)

            # --- 5. فئة الإدارة والتطوير والتعليمات (مخفية ومعربة بالكامل) ---
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True)
            }
            
            staff_category = await guild.create_category(name="👑 قسم الإدارة والعمليات", overwrites=overwrites)
            await guild.create_text_channel(name="💬┃شات-الإدارة", category=staff_category)
            await guild.create_text_channel(name="🚨┃بلاغات-البوتات", category=staff_category)
            await guild.create_text_channel(name="📊┃سجلات-الأخطاء", category=staff_category)
            await guild.create_text_channel(name="🧪┃التجارب-الداخلية", category=staff_category)
            
            # إنشاء منتدى دليل تشغيل البوتات للإدارة
            

            # تعديل الرسالة السابقة لتأكيد النجاح بعد اكتمال البناء تماماً
            await interaction.edit_original_response(content="🚀 **تم بناء هيكلية السيرفر بالكامل مع الإيموجي وتنسيق القنوات والمنتديات بنجاح باهر!**")
            
        except discord.Forbidden:
            await interaction.edit_original_response(content="❌ فشل بناء السيرفر. يرجى التأكد من أن البوت لديه صلاحية **Administrator** (مدير عام) وتفعيل ميزة **Community** في السيرفر لإنشاء قنوات المنتديات.")
        except Exception as e:
            await interaction.edit_original_response(content=f"❌ حدث خطأ غير متوقع أثناء البناء: {e}")

# دالة أساسية لربط الكود بملف البوت الرئيسي تلقائياً عند استدعائه
async def setup(bot: commands.Bot):
    await bot.add_cog(BuildServerCog(bot))