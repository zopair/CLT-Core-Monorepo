
import os
import time
try:
    import telebot
    from groq import Groq
    print("✅ Libraries Loaded Successfully")
except Exception as e:
    print(f"❌ Library Error: {e}")
    os.system("pip install pyTelegramBotAPI groq")
    import telebot

bot = telebot.TeleBot(os.getenv('TELEGRAM_BOT_TOKEN'))

@bot.message_handler(commands=['start'])
def s(m): bot.reply_to(m, "👑 OrbitX Global AI: ONLINE 2026")

print("🚀 Engine is Fired Up!")
bot.infinity_polling(timeout=10, long_polling_timeout=5)
