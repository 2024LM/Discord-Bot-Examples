# meme_poster.py
import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
import random
import copy

class MemePosterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # حفظ الإعدادات بمفتاح  يجمع السيرفر واللغة: "guildId_lang" لمنع أي تداخل نهائياً
        # البنية: { "guildId_lang": {"channel_id": int, "interval": int, "lang": str, "active": bool, "minutes_counter": 0} }
        self.guild_settings = {}
        
        # مصادر مجتمعات Reddit
        self.meme_sources = {
            "ar": ["arabicsub", "Siriuseon", "saudi"],
            "en": ["WholesomeMemes", "CleanMemes", "HistoryMemes", "mathmemes"],
            "ru": ["Pikabu", "ru"]
        }
        
        # مخزون احتياطي للميمز لضمان العمل حتى لو فشل سيرفر Reddit أو كان المجتمع خاصاً
        self.fallback_memes = {
            "ar": [
                "https://i.imgur.com/vHdfDk4.jpeg",
                "https://i.imgur.com/rN30V1m.png",
                "https://i.imgur.com/6Xm7S9Q.jpeg",
                "https://i.imgur.com/8QpY9fT.jpeg"
            ],
            "ru": [
                "https://i.imgur.com/KdfG3sd.jpeg",
                "https://i.imgur.com/UvX9W4e.png",
                "https://i.imgur.com/pYt6Rwq.jpeg"
            ],
            "en": [
                "https://i.imgur.com/XT7pOn6.png",
                "https://i.imgur.com/pS8bA92.png",
                "https://i.imgur.com/YgZ8D3s.png"
            ]
        }
        
        # بدء المهمة المتكررة في الخلفية
        self.meme_sender_task.start()

    def cog_unload(self):
        self.meme_sender_task.cancel()

    # --- 1. أمر الإعداد والتشغيل  ---
    @app_commands.command(name="meme_setup", description="إعداد وتشغيل نشر الميمز التلقائي للغة معينة في هذا السيرفر")
    @app_commands.choices(lang=[
        app_commands.Choice(name="العربية (Arabic)", value="ar"),
        app_commands.Choice(name="English (الإنجليزية)", value="en"),
        app_commands.Choice(name="Русский (الروسية)", value="ru")
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def meme_setup(self, interaction: discord.Interaction, channel: discord.TextChannel, lang: str, interval_minutes: int):
        await interaction.response.defer(ephemeral=True)
        
        if interval_minutes < 10:
            await interaction.followup.send("⚠️ عذراً يا صديقي، الحد الأدنى للوقت هو **10 دقائق** لمنع الضغط وتجميد البوت.", ephemeral=True)
            return

        guild_id = interaction.guild_id
        # مفتاح  يدمج السيرفر واللغة معاً
        setup_key = f"{guild_id}_{lang}"
        
        self.guild_settings[setup_key] = {
            "channel_id": channel.id,
            "interval": interval_minutes,
            "lang": lang,
            "active": True,
            "minutes_counter": 0
        }
        
        lang_map = {"ar": "العربية 🇸🇦", "en": "الإنجليزية 🇬🇧", "ru": "الروسية 🇷🇺"}
        
        await interaction.followup.send(
            f"✅ **تم تفعيل نشر الميمز بنجاح!**\n"
            f"🔸 القناة المحددة: {channel.mention}\n"
            f"🔸 اللغة المعتمدة: **{lang_map[lang]}**\n"
            f"⏱️ معدل النشر: كل **{interval_minutes}** دقيقة.\n"
            f"💡 *ملاحظة: يمكنك تشغيل لغات أخرى في قنوات مختلفة دون تداخل!*",
            ephemeral=True
        )

    # --- 2. أمر قائمة الإعدادات النشطة ---
    @app_commands.command(name="meme_status", description="عرض حالة اللغات النشطة لإرسال الميمز في هذا السيرفر")
    @app_commands.checks.has_permissions(administrator=True)
    async def meme_status(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        lang_map = {"ar": "العربية 🇸🇦", "en": "الإنجليزية 🇬🇧", "ru": "الروسية 🇷🇺"}
        
        active_services = []
        for key, settings in self.guild_settings.items():
            if key.startswith(str(guild_id)) and settings["active"]:
                channel = self.bot.get_channel(settings["channel_id"])
                channel_mention = channel.mention if channel else "قناة غير صالحة"
                rem_time = settings["interval"] - settings["minutes_counter"]
                active_services.append(
                    f"🔸 **اللغة:** {lang_map[settings['lang']]} | **القناة:** {channel_mention} | **متبقي:** {rem_time} دقيقة."
                )
                
        if not active_services:
            await interaction.response.send_message("❌ لا توجد أي خدمات ميمز نشطة حالياً في هذا السيرفر.", ephemeral=True)
            return
            
        report = "📊 **حالة إعدادات الميمز النشطة في السيرفر:**\n" + "\n".join(active_services)
        await interaction.response.send_message(report, ephemeral=True)

    # --- 3. أمر إيقاف لغة معينة أو الكل ---
    @app_commands.command(name="meme_stop", description="إيقاف تفعيل لغة ميمز محددة في هذا السيرفر")
    @app_commands.choices(lang=[
        app_commands.Choice(name="العربية (Arabic)", value="ar"),
        app_commands.Choice(name="English (الإنجليزية)", value="en"),
        app_commands.Choice(name="Русский (الروسية)", value="ru"),
        app_commands.Choice(name="إيقاف جميع اللغات (All)", value="all")
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def meme_stop(self, interaction: discord.Interaction, lang: str):
        guild_id = interaction.guild_id
        lang_map = {"ar": "العربية 🇸🇦", "en": "الإنجليزية 🇬🇧", "ru": "الروسية 🇷🇺", "all": "جميع اللغات"}
        
        if lang == "all":
            stopped_any = False
            for key in list(self.guild_settings.keys()):
                if key.startswith(str(guild_id)):
                    self.guild_settings[key]["active"] = False
                    stopped_any = True
            if stopped_any:
                await interaction.response.send_message("🛑 تم إيقاف جميع لغات نشر الميمز في هذا السيرفر بنجاح.", ephemeral=True)
            else:
                await interaction.response.send_message("⚠️ لا توجد أي خدمات نشطة لإيقافها.", ephemeral=True)
            return

        setup_key = f"{guild_id}_{lang}"
        if setup_key in self.guild_settings and self.guild_settings[setup_key]["active"]:
            self.guild_settings[setup_key]["active"] = False
            await interaction.response.send_message(f"🛑 تم إيقاف نشر الميمز باللغة **{lang_map[lang]}** في هذا السيرفر.", ephemeral=True)
        else:
            await interaction.response.send_message(f"⚠️ الخدمة باللغة **{lang_map[lang]}** متوقفة بالفعل في هذا السيرفر.", ephemeral=True)

    # --- 4. دالة جلب الميم ذكياً (مع نظام الحماية الذاتي) ---
    async def fetch_clean_meme(self, lang):
        subreddits = self.meme_sources.get(lang, self.meme_sources["en"])
        subreddit = random.choice(subreddits)
        url = f"https://meme-api.com/gimme/{subreddit}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=8) as response:
                    if response.status == 200:
                        data = await response.json()
                        # التحقق لضمان المحتوى المحترم
                        if not data.get("nsfw", False) and data.get("url"):
                            return {
                                "title": data.get("title", "Meme!"),
                                "url": data.get("url"),
                                "post_link": data.get("postLink", "https://reddit.com")
                            }
        except Exception as e:
            print(f"⚠️ تعذر الجلب التلقائي من Reddit للغة {lang} ({e})، سيتم الاستعانة بالمستودع الاحتياطي.")
            
        # الحل البديل والذكي: إذا فشل جلب الرابط نختار ميم عشوائي ومحترم من قائمتنا الاحتياطية المضمونة
        fallback_url = random.choice(self.fallback_memes.get(lang, self.fallback_memes["en"]))
        return {
            "title": "ميم رائع ولطيف ✨",
            "url": fallback_url,
            "post_link": "https://reddit.com"
        }

    # --- 5. محرك الخلفية المعزول تماماً وثنائي الأبعاد ---
    @tasks.loop(minutes=1)
    async def meme_sender_task(self):
        # عمل نسخة مؤقتة لتفادي التعارض وتغيير البيانات أثناء الدوران (RuntimeError)
        current_settings = copy.deepcopy(self.guild_settings)
        
        for setup_key, settings in current_settings.items():
            if not settings["active"]:
                continue
                
            # زيادة العداد محلياً
            new_counter = self.guild_settings[setup_key]["minutes_counter"] + 1
            self.guild_settings[setup_key]["minutes_counter"] = new_counter
            
            # إذا حان وقت الإرسال المحدد لهذا السيرفر وهذه اللغة بالتحديد
            if new_counter >= settings["interval"]:
                self.guild_settings[setup_key]["minutes_counter"] = 0 # تصفير العداد الفعلي
                
                channel = self.bot.get_channel(settings["channel_id"])
                if not channel:
                    continue
                
                # جلب الميم المناسب
                meme_data = await self.fetch_clean_meme(settings["lang"])
                if meme_data:
                    lang = settings["lang"]
                    if lang == "ar":
                        embed_title = "ميم مضحك ولطيف ✨"
                        footer_text = "😄 ميم عربي مضحك ومحترم"
                        color = discord.Color.orange()
                    elif lang == "ru":
                        embed_title = "Веселый мем ✨"
                        footer_text = "😄 Русский мем"
                        color = discord.Color.green()
                    else:
                        embed_title = meme_data["title"]
                        footer_text = "😄 Wholesome Meme"
                        color = discord.Color.blurple()
                        
                    embed = discord.Embed(
                        title=embed_title,
                        url=meme_data["post_link"],
                        color=color
                    )
                    embed.set_image(url=meme_data["url"])
                    embed.set_footer(text=footer_text)
                    
                    try:
                        await channel.send(embed=embed)
                    except Exception as e:
                        print(f"❌ فشل إرسال منشور الميمز للمفتاح {setup_key}: {e}")

    @meme_sender_task.before_loop
    async def before_meme_sender(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(MemePosterCog(bot))
