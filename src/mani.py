# main.py (الملف الرئيسي المطور والداعم لنظام النقاط واللغات)
import discord
from discord.ext import commands

# 1. تفعيل كافة الصلاحيات اللازمة لقراءة الرسائل (للشات) ورتب الأعضاء (للغات)
intents = discord.Intents.default()
intents.message_content = True  # لقراءة الرسائل واحتساب نقاط التفاعل بالشات
intents.members = True          # ضروري جداً لكي يتعرف البوت على رتب اللغات للأعضاء ويمنحها لهم

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # --- تحميل ملفات نظام اللغات والترجمة ونظام النقاط الجديدة ---
        await self.load_extension("translation_system")
        await self.load_extension("points_system")

        # --- تحميل بقية ملفات الأوامر والألعاب الخاصة بك ---
        await self.load_extension('avatar') 
        await self.load_extension('tags')
        await self.load_extension('guess_game')
        await self.load_extension('xo_game')
        await self.load_extension('chess_game')
        await self.load_extension('forum_poster')
        await self.load_extension('جلكه')
        await self.load_extension('meme_poster')  
        await self.load_extension("build_command")   
        
        print("🚀 تم تحميل كافة ملفات الأوامر والأنظمة المتكاملة بنجاح")

bot = MyBot()

@bot.event
async def on_ready():
    print(f'🤖 تم تسجيل الدخول باسم: {bot.user.name}')

# 👑 الأمر السحري للمزامنة الإجبارية (لك أنت فقط كصاحب البوت)
@bot.command(name="sync")
@commands.is_owner() # للتأكد أنك أنت فقط من تشغله
async def sync_commands(ctx):
    await ctx.send("⏳ جاري مزامنة أوامر المائل مع ديسكورد...")
    try:
        # يزامن الأوامر في السيرفر الحالي الذي كتبت فيه الأمر فوراً
        bot.tree.copy_global_to(guild=ctx.guild)
        synced = await bot.tree.sync(guild=ctx.guild)
        await ctx.send(f"✅ نجحت المزامنة! تم إجبار ظهور {len(synced)} أمر مائل (Slash Command) في هذا السيرفر فوراً!")
    except Exception as e:
        await ctx.send(f"❌ فشلت المزامنة بسبب: {e}")

# تشغيل البوت بالتوكن الخاص بك
# ⚠️ تذكير هام يا صديقي: يرجى عمل Reset لهذا التوكن من لوحة التحكم واستبداله لحماية بوتك!

bot.run('TOKEN')
