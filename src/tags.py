# tags.py
import discord
from discord.ext import commands
from discord import app_commands
import json
import os

class TagsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.json_file = "tags_data.json"
        self.text_database = self.load_tags()

    def load_tags(self):
        if os.path.exists(self.json_file):
            try:
                with open(self.json_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"خطأ أثناء قراءة ملف JSON: {e}")
                return {}
        return {}

    def save_tags(self):
        try:
            with open(self.json_file, "w", encoding="utf-8") as f:
                json.dump(self.text_database, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"خطأ أثناء حفظ ملف JSON: {e}")

    # 1️⃣ أمر عرض النص المائل /say
    @app_commands.command(name="say", description="عرض نص محفوظ باستخدام كلمة مفتاحية")
    async def say_tag(self, interaction: discord.Interaction, keyword: str = None):
        server_id = str(interaction.guild_id) # جلب رقم السيرفر الحالي وتحويله لنص
        
        # التحقق إذا كان السيرفر له بيانات أصلاً
        if server_id not in self.text_database or not self.text_database[server_id]:
            await interaction.response.send_message("📭 لا توجد أي نصوص مسجلة في هذا السيرفر بعد!", ephemeral=True)
            return

        # إذا لم يكتب المستخدم كلمة، نعرض له الكلمات المتاحة في سيرفره فقط
        if keyword is None:
            available_keywords = ", ".join([f"`{k}`" for k in self.text_database[server_id].keys()])
            await interaction.response.send_message(f"ℹ️ الكلمات المتاحة في هذا السيرفر: {available_keywords}", ephemeral=True)
            return

        keyword_lower = keyword.lower()
        if keyword_lower in self.text_database[server_id]:
            await interaction.response.send_message(self.text_database[server_id][keyword_lower])
        else:
            await interaction.response.send_message(f"❌ الكلمة `{keyword}` غير مسجلة  .", ephemeral=True)

    # 2️⃣ أمر إضافة نص جديد /add_tag (مخصص لكل سيرفر)
    @app_commands.command(name="add_tag", description="إضافة نص وتذكره في هذا السيرفر")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def add_tag(self, interaction: discord.Interaction, keyword: str, text: str):
        server_id = str(interaction.guild_id)
        keyword_lower = keyword.lower()
        
        # إذا كان السيرفر يدخل لأول مرة، ننشئ له مكان في الملف
        if server_id not in self.text_database:
            self.text_database[server_id] = {}
            
        self.text_database[server_id][keyword_lower] = text
        self.save_tags()
        
        await interaction.response.send_message(f"✅ تم حفظ وتذكر الكلمة `{keyword}` لهذا السيرفر بنجاح!")

    # 3️⃣ أمر حذف نص /del_tag
    @app_commands.command(name="del_tag", description="حذف نص مسجل من هذا السيرفر")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def delete_tag(self, interaction: discord.Interaction, keyword: str):
        server_id = str(interaction.guild_id)
        keyword_lower = keyword.lower()
        
        if server_id in self.text_database and keyword_lower in self.text_database[server_id]:
            del self.text_database[server_id][keyword_lower]
            self.save_tags()
            await interaction.response.send_message(f"🗑️ تم حذف الكلمة `{keyword}` من هذا السيرفر.")
        else:
            await interaction.response.send_message(f"❌ الكلمة `{keyword}` غير موجودة في هذا السيرفر.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(TagsCog(bot))