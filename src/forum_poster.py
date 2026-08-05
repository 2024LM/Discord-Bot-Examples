# forum_poster.py
import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import aiohttp
import io
import asyncio

class ForumPosterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.folder_path = r"استخراج معلومات احداث لعبة نجاة في صقيع/JK/json/events" 

    def split_text_smart(self, text, max_chars=1000):
        chunks = []
        while len(text) > max_chars:
            split_index = text.rfind('\n', 0, max_chars)
            if split_index == -1:
                split_index = text.rfind(' ', 0, max_chars)
            if split_index == -1:
                split_index = max_chars
            
            chunks.append(text[:split_index].strip())
            text = text[split_index:].strip()
        if text:
            chunks.append(text)
        return chunks

    @app_commands.command(name="publish_posts", description="نشر موسوعة الفعاليات حسب اللغة المختارة بالتفريق الصارم")
    @app_commands.choices(lang=[
        app_commands.Choice(name="العربية (Arabic)", value="ar"),
        app_commands.Choice(name="English (الإنجليزية)", value="en"),
        app_commands.Choice(name="Русский (الروسية)", value="ru")
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def publish_posts(self, interaction: discord.Interaction, forum_channel: discord.ForumChannel, lang: str):
        await interaction.response.defer(ephemeral=True)

        if not os.path.exists(self.folder_path):
            os.makedirs(self.folder_path)
            await interaction.followup.send(f"❌ المجلد `{self.folder_path}` غير موجود.", ephemeral=True)
            return

        success_count = 0
        failed_count = 0

        # رسائل واجهة المستخدم حسب لغة النشر المحددة
        loading_messages = {
            "ar": "مرحباً بكم في دليل حدث:",
            "en": "Welcome to the event guide for:",
            "ru": "Добро пожаловать в руководство по мероприятию:"
        }

        async with aiohttp.ClientSession() as session:
            for file_name in os.listdir(self.folder_path):
                if file_name.endswith('.json'):
                    file_path = os.path.join(self.folder_path, file_name)
                    
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        
                        # سحب البيانات بناءً على اللغة المختارة من ديسكورد
                        if "translations" in data and lang in data["translations"]:
                            lang_data = data["translations"][lang]
                            main_title = lang_data.get("title", "").strip()
                            sections = lang_data.get("sections", [])
                        else:
                            # نظام حماية احتياطي في حال عدم ترجمة الملف بعد
                            main_title = data.get("title", file_name.replace('.json', '')).strip()
                            sections = data.get("sections", [])

                        if not sections:
                            continue

                        posted_images = set()

                        # --- 1. معالجة وإنشاء المنشور بالقسم الأول ---
                        first_section = sections[0]
                        first_sec_contents = first_section.get("content", [])
                        first_sec_images = first_section.get("images", [])

                        intro_builder = []
                        for item in first_sec_contents:
                            if isinstance(item, str) and item.strip() and "الملخص مقدمة" not in item:
                                intro_builder.append(item.strip())
                            elif isinstance(item, list):
                                for sub_item in item:
                                    if isinstance(sub_item, str) and sub_item.strip():
                                        intro_builder.append(f"• {sub_item.strip()}")

                        intro_text = "\n\n".join(intro_builder).strip()
                        if not intro_text:
                            intro_text = f"{loading_messages[lang]} **{main_title}**"

                        intro_chunks = self.split_text_smart(intro_text, max_chars=1200)
                        
                        thread_channel = await forum_channel.create_thread(
                            name=main_title,
                            content=intro_chunks[0]
                        )
                        await asyncio.sleep(2)

                        for remaining_intro in intro_chunks[1:]:
                            if remaining_intro.strip():
                                await thread_channel.thread.send(content=remaining_intro)
                                await asyncio.sleep(2)
                        
                        await self.download_and_send_images(session, thread_channel.thread, first_sec_images, posted_images)
                        await asyncio.sleep(3)

                        # --- 2. نشر بقية الأقسام المترجمة ---
                        for section in sections[1:]:
                            sec_title = section.get("title", "").strip()
                            sec_contents = section.get("content", [])
                            sec_images = section.get("images", [])

                            if "Terms of Service" in str(sec_contents) or "Privacy Policy" in str(sec_contents):
                                continue

                            sec_text_builder = []
                            for item in sec_contents:
                                if isinstance(item, str) and item.strip():
                                    sec_text_builder.append(item.strip())
                                elif isinstance(item, list):
                                    for sub_item in item:
                                        if isinstance(sub_item, str) and sub_item.strip():
                                            sec_text_builder.append(f"• {sub_item.strip()}")

                            section_text = "\n\n".join(sec_text_builder).strip()

                            if not section_text and not sec_images:
                                continue

                            if sec_title and sec_title != main_title:
                                await thread_channel.thread.send(content=f"\n✨ **━━━━━━━━━━━━━━━**\n### 🔸 {sec_title}")
                                await asyncio.sleep(2)
                            
                            if section_text:
                                text_chunks = self.split_text_smart(section_text, max_chars=1000)
                                for chunk in text_chunks:
                                    if chunk.strip():
                                        await thread_channel.thread.send(content=chunk)
                                        await asyncio.sleep(2.5)

                            # سحب الصور المنظمة من نفس القسم الحرة وغير المتأثرة بالترجمة
                            await self.download_and_send_images(session, thread_channel.thread, sec_images, posted_images)
                            await asyncio.sleep(3)

                        success_count += 1
                        print(f"✅ [{lang.upper()}] تم نشر ملف: {main_title}")
                        await asyncio.sleep(6.0)

                    except Exception as e:
                        print(f"❌ خطأ في معالجة الملف {file_name}: {e}")
                        failed_count += 1

        await interaction.followup.send(
            f"🎯 اكتمل نشر الموسوعة باللغة المختارة ({lang.upper()})!\n"
            f"🔹 تم نشر **{success_count}** موضوع بنجاح.\n"
            f"⚠️ ملفات فشلت: **{failed_count}**", 
            ephemeral=True
        )

    async def download_and_send_images(self, session, thread, image_urls, posted_images):
        for index, img_url in enumerate(image_urls):
            if "content-button-bg.png" in img_url or "common_btn_up.png" in img_url or "cropped-logo-arb.png" in img_url:
                continue
            if not img_url.startswith("http"):
                continue
            if img_url in posted_images:
                continue
                
            try:
                async with session.get(img_url, timeout=10) as resp:
                    if resp.status == 200:
                        img_bytes = await resp.read()
                        data_file = io.BytesIO(img_bytes)
                        discord_file = discord.File(data_file, filename=f"img_{len(posted_images)}.png")
                        
                        await thread.send(file=discord_file)
                        posted_images.add(img_url)
                        await asyncio.sleep(2)
            except Exception:
                pass
            
async def setup(bot):
    await bot.add_cog(ForumPosterCog(bot))