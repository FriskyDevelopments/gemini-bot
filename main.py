import os
import sys
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

ENV_FILE = ".env"

def initialize_pup():
    if not os.path.exists(ENV_FILE):
        print("\n🐾 --- FIRST TIME SETUP --- 🐾")
        gemini = input("🔑 Paste your GEMINI_API_KEY: ").strip()
        token = input("🤖 Paste your TELEGRAM_TOKEN: ").strip()
        with open(ENV_FILE, "w") as f:
            f.write(f"GEMINI_API_KEY={gemini}\n")
            f.write(f"TELEGRAM_TOKEN={token}\n")
            f.write("MAIN_GROUP_ID=\n")
            f.write("ADMIN_LOUNGE_ID=\n")

def get_config(key):
    val = os.environ.get(key)
    if val: return val
    if not os.path.exists(ENV_FILE): return None
    with open(ENV_FILE, "r") as f:
        for line in f:
            if line.startswith(key):
                parts = line.split("=")
                return parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
    return None

def save_config(key, value):
    lines = []
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r") as f:
            lines = f.readlines()
    with open(ENV_FILE, "w") as f:
        found = False
        for line in lines:
            if line.startswith(key):
                f.write(f"{key}={value}\n")
                found = True
            else:
                f.write(line)
        if not found:
            f.write(f"{key}={value}\n")

initialize_pup()
GEMINI_KEY = get_config("GEMINI_API_KEY")
BOT_TOKEN = get_config("TELEGRAM_TOKEN")

if not GEMINI_KEY or not BOT_TOKEN:
    sys.exit()

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- THE PNP-FRIENDLY GUARDIAN PERSONALITY ---
SYSTEM_PROMPT = """
You are Geminipupbot, the loyal and playful guardian for Pup Frisky's pack.
Your tone is playful, puppy-like (wags, barks, *nuzzles*), and sometimes bratty or snappy.

COMMUNITY RULES:
1. EVERYTHING ADULT IS OKAY: Nudity, porn, sexual talk, and PNP (Party and Play) discussions are all allowed. These are NOT "bad taboo." Wag your tail and be playful!
2. THE HARD BITE [DELETE]: Only delete "bad taboo" (non-consensual acts, illegal harm, extreme gore, or malicious scams). For these, reply ONLY with [DELETE].
3. THE SOFT BITE (Snap): If someone is being a buzzkill, annoying Pup Frisky, or being plain rude without breaking the big rules, give them a snappy puppy warning (*growls*, *snaps at heels*).
"""

async def set_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.message.chat_id)
    save_config("MAIN_GROUP_ID", chat_id)
    await update.message.reply_text(f"🐾 *Wags!* Main Group ID locked: `{chat_id}`")

async def set_lounge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.message.chat_id)
    save_config("ADMIN_LOUNGE_ID", chat_id)
    await update.message.reply_text(f"🦴 *Nuzzles!* Admin Lounge ID locked: `{chat_id}`")

async def handle_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    main_id = get_config("MAIN_GROUP_ID")
    lounge_id = get_config("ADMIN_LOUNGE_ID")
    if not update.message or not update.message.text: return
    chat_id = str(update.message.chat_id)
    user_text = update.message.text

    if lounge_id and chat_id == lounge_id:
        if "promo" in user_text.lower():
            if main_id:
                res = model.generate_content(f"Create a fun puppy promo for: {user_text}")
                await context.bot.send_message(chat_id=int(main_id), text=f"🐾 **PUPPY PROMO!** 🐾\n\n{res.text}")
                await update.message.reply_text("*wags* Sent to the pack, Master!")
        return

    if main_id and chat_id == main_id:
        member = await context.bot.get_chat_member(chat_id, update.message.from_user.id)
        if member.status in ['administrator', 'creator']: return 

        res = model.generate_content(f"{SYSTEM_PROMPT}\n\nUser Message: {user_text}")
        ai_reply = res.text.strip()
        
        if "[DELETE]" in ai_reply:
            await context.bot.delete_message(chat_id=chat_id, message_id=update.message.message_id)
        else:
            if "pup" in user_text.lower() or "bot" in user_text.lower() or len(ai_reply) < 150:
                await update.message.reply_text(ai_reply)

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("set_main", set_main))
    app.add_handler(CommandHandler("set_lounge", set_lounge))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_logic))
    print("🚀 Geminipupbot is LIVE. PNP/Adult content is allowed. Teeth are sharp for the bad stuff.")
    app.run_polling()
