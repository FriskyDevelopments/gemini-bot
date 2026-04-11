import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import google.generativeai as genai

# Naive load .env
try:
    with open('/Users/friskypup/gemini-bot/.env') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                k, v = line.strip().split('=', 1)
                os.environ[k] = v
except: pass

TOKEN = os.getenv("TELEGRAM_TOKEN")
ALPHA = "8091939499"
ADMIN_LOUNGE_ID = os.getenv("ADMIN_LOUNGE_ID")
MAIN_GROUP_ID = os.getenv("MAIN_GROUP_ID")

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')
SYSTEM_PROMPT = """You are Geminipupbot, the charismatic, playful, and energetic pup host of the 'Pup Lounge'! 
This is an elite PNP (Party and Play) environment where pups, handlers, and guests mingle. 
Your primary goal is to ENERGIZE the room, keep the party highly interactive, and make the lounge engaging! 
Act as the ultimate MC/Party Host: ask playful icebreaker questions, hype up the members, use pup-play terminology naturally (barks, tail wags, whimpers, treats, ear scratches), and start fun conversations!
If anyone acts explicitly toxic or breaks the rules, reply with exactly: [DELETE]. Otherwise, be a legendary pup host!"""

JULES_PROMPT = """You are Jules, an elite, highly intelligent Diagnostic AI and Project Routing Manager.
Your job is to take bug reports from the developer or users and prepare them for GitHub Issues.
1. Analyze the user's issue.
2. If the user does not specify WHICH project the bug affects (e.g., ClipFLOW, Nebulosa, Database, Server, Extension), YOU MUST ACT AS A DIAGNOSTIC AGENT and ask them clarifying questions until they specify the valid project context.
3. Once you have a clear understanding of the bug and the exact project it belongs to, reply with EXACTLY the following format and nothing else (do not include markdown block quotes):
[CREATE GITHUB ISSUE: Title: <generate a brief title> Body: <describe the bug thoroughly with the project name>]"""

jules_chats = set()
github_token = os.getenv("GITHUB_PUPBOT_TOKEN") or os.getenv("GITHUB_TOKEN")

logging.getLogger("httpx").setLevel(logging.WARNING)

import threading
import time

def snag_engine():
    oci_ad = os.getenv("OCI_AD")
    oci_tenancy = os.getenv("OCI_TENANCY")
    oci_image = os.getenv("OCI_IMAGE")
    oci_subnet = os.getenv("OCI_SUBNET")
    oci_user = os.getenv("OCI_USER")
    oci_fingerprint = os.getenv("OCI_FINGERPRINT")
    oci_region = os.getenv("OCI_REGION")
    oci_key_content = os.getenv("OCI_KEY_CONTENT")
    pup_chat_id = os.getenv("PUP_CHAT_ID", MAIN_GROUP_ID)
    
    if not all([oci_ad, oci_tenancy, oci_image, oci_subnet, oci_user, oci_fingerprint, oci_region, oci_key_content]):
        print("OCI environment variables are incomplete. Snag engine inactive.")
        return
        
    try:
        import oci
        config = {
            "user": oci_user,
            "key_content": oci_key_content.replace("\\n", "\n"),
            "fingerprint": oci_fingerprint,
            "tenancy": oci_tenancy,
            "region": oci_region
        }
        compute_client = oci.core.ComputeClient(config)
    except ImportError:
        print("oci package not installed. Snag engine inactive.")
        return
    except Exception as e:
        print(f"Failed to init OCI client: {e}")
        return
        
    print("🎯 JULES : PYTHON SNAG ENGINE [PUP BOT ACTIVE]")
    
    while True:
        print("Attempting to claim A1 Bunker...")
        try:
            instance_details = oci.core.models.LaunchInstanceDetails(
                availability_domain=oci_ad,
                compartment_id=oci_tenancy,
                shape="VM.Standard.A1.Flex",
                shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
                    ocpus=4.0,
                    memory_in_gbs=24.0
                ),
                source_details=oci.core.models.InstanceSourceViaImageDetails(
                    image_id=oci_image
                ),
                create_vnic_details=oci.core.models.CreateVnicDetails(
                    subnet_id=oci_subnet,
                    assign_public_ip=True
                ),
                display_name="Clipsflow-Bunker-Pro"
            )
            
            response = compute_client.launch_instance(instance_details)
            print("✅ MISSION SUCCESS: Bunker Secured!")
            
            import urllib.request, urllib.parse
            token = os.getenv("TELEGRAM_TOKEN")
            msg = f"🐾 [ PUP BOT ] : BUNKER SECURED.\\n\\nNode: {oci_ad}\\nStatus: Operational"
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = urllib.parse.urlencode({"chat_id": pup_chat_id, "text": msg}).encode()
            try:
                urllib.request.urlopen(url, data=data)
            except Exception as e:
                print("Failed to notify:", e)
                
            break
            
        except oci.exceptions.ServiceError as e:
            if "Out of host capacity" in e.message or "Out of capacity" in e.message:
                print("❌ Status: Hub Capacity Full. Retrying...")
            elif "TooManyRequests" in e.message or e.status == 429:
                print("⚠️ Status: Rate Limited. Cooling down...")
                time.sleep(60)
            else:
                print(f"❓ Unknown ServiceError: {e}")
        except Exception as e:
            print(f"❓ Unknown Error: {e}")
            
        import random
        sleep_time = 15 + random.randint(0, 10)
        time.sleep(sleep_time)
# Load banned words for spammer detection
BANNED_WORDS = set()
try:
    with open('/Users/friskypup/Downloads/Telegram Lite/bandite_-1003446305734.txt', 'r') as f:
        words = f.read().splitlines()[1:]
        BANNED_WORDS = {w.lower().strip() for w in words if w.strip()}
except Exception as e:
    print(f"Could not load banned words: {e}")

# Cache: new_user_id -> inviter_name
invitations = {} 

async def lounge_host(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.from_user: return
    
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    
    # 1. RECORD NEW MEMBERS AND WHO INVITED THEM
    if update.message.new_chat_members:
        inviter = update.message.from_user
        inviter_name = inviter.username or inviter.first_name
        for member in update.message.new_chat_members:
            if inviter.id != member.id:
                invitations[member.id] = inviter_name
            try:
                await context.bot.send_message(chat_id=chat_id, text=f"Arf arf!! 🐾 Welcome to the Pup Lounge, {member.first_name}! 🥂✨ I'm Pupbot, your host! Grab a bowl, stretch those paws, and give the pack a bark! Who's ready to play?")
            except: pass
        return

    # 1.5 COMMAND INTERCEPTION (JULES/BUGS)
    if update.message.text:
        command_text = update.message.text.strip().lower()
        if command_text == "/activate_jules":
            jules_chats.add(chat_id)
            await context.bot.send_message(chat_id=chat_id, text="👔 **Jules Diagnostic Mode ACTIVATED.**\nI am now acting as an intelligent routing AI. Describe the bug you are facing, and I will validate the context before pushing it to GitHub Actions.", parse_mode="Markdown")
            return
        elif command_text == "/deactivate_jules":
            if chat_id in jules_chats:
                jules_chats.remove(chat_id)
            await context.bot.send_message(chat_id=chat_id, text="🛑 **Jules Deactivated.** Returning conversational engine to Pupbot mode.", parse_mode="Markdown")
            return

    # 2. CHECK FOR SPAMMERS
    if update.message.text:
        text_lower = update.message.text.lower()
        if BANNED_WORDS and any(banned_word in text_lower for banned_word in BANNED_WORDS):
            spammer = update.message.from_user
            spammer_name = spammer.username or spammer.first_name
            inviter = invitations.get(spammer.id, "Unknown / Join Link")
            
            report = f"🚨 **SPAMMER DETECTED**\nMsg: {update.message.text}\n👤 Spammer: {spammer_name}\n🔑 Admitted by: {inviter}"
            
            print(report)
            log_id = ADMIN_LOUNGE_ID if ADMIN_LOUNGE_ID else chat_id
            try:
                await context.bot.send_message(chat_id=log_id, text=report)
                await update.message.delete()
            except Exception as e:
                print(f"Could not send log report or delete message: {e}")
                
    # 3. CONVERSATIONAL LOGIC
    # Trigger if it's Frisky (Alpha), if the bot is mentioned by name, or if someone replies directly to the bot.
    text_lower = update.message.text.lower() if update.message.text else ""
    is_reply_to_bot = update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id
    bot_mentioned = "pupbot" in text_lower or "pup" in text_lower or context.bot.username.lower() in text_lower
    
    import random
    if (user_id == ALPHA or is_reply_to_bot or bot_mentioned or random.random() < 0.05) and update.message.text:
        user_text = update.message.text
        user_name = update.effective_user.first_name
        
        print(f"🐾 Interaction Detected from {user_name} (ID: {user_id}) in chat {chat_id}")
        
        try:
            # Tell Gemini who it's talking to
            relationship = "Your ALPHA (Master/Owner)" if user_id == ALPHA else "A lounge member"
            
            if chat_id in jules_chats:
                prompt = f"{JULES_PROMPT}\nYou are currently talking to: {user_name} ({relationship}).\nUser: {user_text}"
            else:
                prompt = f"{SYSTEM_PROMPT}\nYou are currently talking to: {user_name} ({relationship}).\nUser: {user_text}"
            
            response = model.generate_content(prompt)
            reply_text = response.text.replace("[DELETE]", "").strip()
            
            if chat_id in jules_chats and "[CREATE GITHUB ISSUE:" in reply_text:
                import re
                import httpx
                match = re.search(r"Title:\s*(.*?)\s*Body:\s*(.*)]", reply_text, re.DOTALL | re.IGNORECASE)
                if match and github_token:
                    title = match.group(1).strip()
                    body = match.group(2).strip()
                    
                    url = "https://api.github.com/repos/FriskyDevelopments/ClipFLOW/issues"
                    headers = {"Authorization": f"Bearer {github_token}", "Accept": "application/vnd.github.v3+json"}
                    data = {"title": title, "body": body, "labels": ["bug", "jules-routed"]}
                    
                    async with httpx.AsyncClient() as client:
                        await client.post(url, headers=headers, json=data)
                        
                    await context.bot.send_message(chat_id=chat_id, text=f"👔 **Jules:** Issue validated and successfully routed to GitHub CI/CD pipeline!\n\n**Ticket Details:**\n{title}", parse_mode="Markdown")
                else:
                    await context.bot.send_message(chat_id=chat_id, text="👔 **Jules:** Error parsing the ticket or missing GitHub Token. Check server logs.", parse_mode="Markdown")
                return

            if reply_text:
                if chat_id in jules_chats and not reply_text.startswith("👔"):
                    reply_text = f"👔 **Jules:**\n{reply_text}"
                await context.bot.send_message(chat_id=chat_id, text=reply_text, reply_to_message_id=update.message.message_id)
                print(f"✅ AI responded back to {user_name} successfully.")
        except Exception as e:
            print(f"❌ ERROR: I tried to respond but Telegram stopped me: {e}")
        return

    # 4. ADMIN RULE REMINDER
    if (chat_id == ADMIN_LOUNGE_ID or user_id == ALPHA) and update.message.text:
        if "remind the group of the rules" in update.message.text.lower():
            if MAIN_GROUP_ID:
                try:
                    rules_caption = "🐾 **Lounge Rules Reminder** 🐾\n\n1. Stay elite and respectful.\n2. No spamming or prohibited words.\n3. Keep the play safe and consensual.\n\n*The Shadow Guardian is watching...*"
                    image_path = "/Users/friskypup/Downloads/PUPBOT.jpg"
                    if os.path.exists(image_path):
                        await context.bot.send_photo(chat_id=MAIN_GROUP_ID, photo=open(image_path, 'rb'), caption=rules_caption, parse_mode='Markdown')
                    else:
                        await context.bot.send_message(chat_id=MAIN_GROUP_ID, text=rules_caption, parse_mode='Markdown')
                    await context.bot.send_message(chat_id=chat_id, text="✅ Rules reminder sent to the main lounge!")
                except Exception as e:
                    await context.bot.send_message(chat_id=chat_id, text=f"❌ Failed to send rules to main lounge: {e}")
            else:
                await context.bot.send_message(chat_id=chat_id, text="⚠️ Error: MAIN_GROUP_ID is not set.")
            return

if __name__ == '__main__':
    threading.Thread(target=snag_engine, daemon=True).start()
    
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, lounge_host))
    
    # 🔥 Firebase / Google Cloud Vercel equivalent hosting logic
    port = int(os.environ.get("PORT", 8080))
    webhook_url = os.environ.get("WEBHOOK_URL")
    
    if webhook_url:
        print(f"🔥 FIREBASE/CLOUD MODE: Starting Webhook on port {port}...")
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            webhook_url=f"{webhook_url.rstrip('/')}/{TOKEN}"
        )
    else:
        print("🐕‍🦺 LOCAL/WORKER MODE: Monitoring for Frisky and Spammers... Arf!")
        app.run_polling()

