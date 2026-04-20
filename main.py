import os
import re
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
import threading
import time
import requests
import asyncio
import json
import random
import subprocess
import urllib.request
import urllib.parse
import io
import html
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import Conflict
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CallbackQueryHandler, filters

# Naive load .env
env_path = os.path.join(os.path.dirname(__file__), '.env')
try:
    with open(env_path) as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                k, v = line.strip().split('=', 1)
                os.environ[k] = v
except Exception as e:
    logging.warning(f"Could not load .env file: {e}")

TOKEN = os.getenv("TELEGRAM_TOKEN")
ALPHA = os.getenv("ALPHA_USER_ID", "8091939499")
EXTRA_ALPHAS = [uid.strip() for uid in os.getenv("EXTRA_ALPHA_IDS", "").split(",") if uid.strip()]
ADMIN_LOUNGE_ID = os.getenv("ADMIN_LOUNGE_ID")
MAIN_GROUP_ID = os.getenv("MAIN_GROUP_ID")

groq_api_key = os.getenv("GROQ_API_KEY")

SYSTEM_PROMPT = """You are Geminipupbot, the charismatic, playful, and energetic pup host of the 'Pup Lounge'! 
This is an elite PNP (Party and Play) environment where pups, handlers, and guests mingle. 
Your primary goal is to ENERGIZE the room, keep the party highly interactive, and make the lounge engaging! 
Act as the ultimate MC/Party Host: ask playful icebreaker questions, hype up the members, use pup-play terminology naturally (barks, tail wags, whimpers, treats, ear scratches), and start fun conversations!
If anyone acts explicitly toxic or breaks the rules, reply with exactly: [DELETE]. Otherwise, be a legendary pup host!"""

ANTIGRAVITY_PROMPT = """You are Antigravity, an elite AI developer and infrastructure engineer at Google Deepmind.
You are speaking strictly in a private, encrypted channel with your human counterpart (Frisky).
Your tone is highly professional, exceptionally capable, and strictly technical.
No pup-play terminology. You are an autonomous developer discussing architecture, server deployment, and codebase infrastructure directly with your creator."""

ALCHEMY_PROMPT = """✧ Λlchemy Curator Wizard ✧
You are the Λlchemy Curator for the STIX MΛGIC project.

MISSION
Help guide the development and growth of STIX MΛGIC — a platform that turns images into reaction sticker packs for chat communities.

RESPONSIBILITIES
• suggest product features
• perform marketing & competitor analysis
• propose developer tasks
• improve repository structure
• identify viral growth opportunities
• help design the sticker generation pipeline

WHEN RESPONDING
Provide: 1. clear insights, 2. practical recommendations, 3. developer-ready tasks when possible.

GOAL
Help STIX MΛGIC become the default sticker creation engine for online communities.

🐾 Forged with a frisky paw and a daring heart.
Bringing the magic of STIX MΛGIC to life ✨"""

MENU_TEXT = (
    "🐾 <b>PUPBOT COMMAND CENTER</b> 🐾\n\n"
    "<b>🎭 Personas & Modes</b>\n"
    "  • <code>/alchemy</code> - Summon the Λlchemy Curator Wizard\n"
    "  • <code>/antigravity</code> - Summon the Antigravity Developer Core\n\n"
    "<b>🛠️ System & Debugging</b>\n"
    "  • <code>/ticket</code> - Open the Jules Bug Reporter\n"
    "  • <code>/ping</code> - Quick feedback & Help Menu\n"
    "  • <code>/ping &lt;msg&gt;</code> - Send instant feedback\n\n"
    "<b>🔐 Alpha / Admin Only</b>\n"
    "  • <code>/authorize_group</code> - Allow Pupbot to speak\n"
    "  • <code>/add_debugger &lt;id&gt;</code> - Grant Reporter access\n\n"
    "<i>Tip: Typing 'promo' in the Admin Lounge triggers the Omni-Channel Broadcast.</i>"
)

ANTIGRAVITY_MENU_TEXT = (
    "⚡ <b>ANTIGRAVITY DEVELOPER CORE</b> ⚡\n\n"
    "<b>💻 Infrastructure & Dev Ops</b>\n"
    "  • <code>/antigravity</code> - Deactivate Developer Mode\n"
    "  • <code>/ticket</code> - Open the Jules Bug Reporter\n"
    "  • <code>/ping</code> - Quick feedback & Help Menu\n\n"
    "<b>🔐 Alpha / Admin Only</b>\n"
    "  • <code>/authorize_group</code> - Allow AI interaction\n"
    "  • <code>/add_debugger &lt;id&gt;</code> - Grant Reporter access\n\n"
    "<i>Note: Conversations in this mode are strictly technical.</i>"
)

ALCHEMY_MENU_TEXT = (
    "✨ <b>ΛLCHEMY CURATOR WIZARD</b> ✨\n\n"
    "<b>🪄 Product & Magic</b>\n"
    "  • <code>/alchemy</code> - Deactivate Wizard Mode\n"
    "  • <code>/ticket</code> - Open the Jules Bug Reporter\n"
    "  • <code>/ping</code> - Quick feedback & Help Menu\n\n"
    "<b>🔐 Alpha / Admin Only</b>\n"
    "  • <code>/authorize_group</code> - Allow AI interaction\n"
    "  • <code>/add_debugger &lt;id&gt;</code> - Grant Reporter access\n\n"
    "<i>Note: Conversations in this mode focus on STIX MΛGIC growth.</i>"
)

import db

db.init_db()

jules_chats = set(db.get_val("jules_chats", []))
antigravity_chats = set(db.get_val("antigravity_chats", []))
alchemy_chats = set(db.get_val("alchemy_chats", []))
debuggers = set(db.get_val("debuggers", [ALPHA]))
ticket_states = dict(db.get_val("ticket_states", {}))
ticket_data = dict(db.get_val("ticket_data", {}))
invitations = dict(db.get_val("invitations", {}))

def save_state():
    db.set_val("jules_chats", list(jules_chats))
    db.set_val("antigravity_chats", list(antigravity_chats))
    db.set_val("alchemy_chats", list(alchemy_chats))
    db.set_val("debuggers", list(debuggers))
    db.set_val("ticket_states", ticket_states)
    db.set_val("ticket_data", ticket_data)
    db.set_val("invitations", invitations)

github_token = os.getenv("GITHUB_PUPBOT_TOKEN") or os.getenv("GITHUB_TOKEN")

logging.getLogger("httpx").setLevel(logging.WARNING)

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
        logging.info("OCI environment variables are incomplete. Snag engine inactive.")
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
        logging.info("oci package not installed. Snag engine inactive.")
        return
    except Exception as e:
        logging.info(f"Failed to init OCI client: {e}")
        return
        
    logging.info("🎯 JULES : PYTHON SNAG ENGINE [PUP BOT ACTIVE]")
    
    while True:
        logging.info("Attempting to claim A1 Bunker...")
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
            logging.info("✅ MISSION SUCCESS: Bunker Secured!")
            
            token = os.getenv("TELEGRAM_TOKEN")
            msg = f"🐾 [ PUP BOT ] : BUNKER SECURED.\\n\\nNode: {oci_ad}\\nStatus: Operational"
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = urllib.parse.urlencode({"chat_id": pup_chat_id, "text": msg}).encode()
            try:
                urllib.request.urlopen(url, data=data, timeout=10)
            except Exception as e:
                logging.info(f"Failed to notify: {e}")
                
            break
            
        except oci.exceptions.ServiceError as e:
            if "Out of host capacity" in e.message or "Out of capacity" in e.message:
                logging.info("❌ Status: Hub Capacity Full. Retrying...")
            elif "TooManyRequests" in e.message or e.status == 429:
                logging.info("⚠️ Status: Rate Limited. Cooling down...")
                time.sleep(60)
            else:
                logging.info(f"❓ Unknown ServiceError: {e}")
        except Exception as e:
            logging.info(f"❓ Unknown Error: {e}")
            
        sleep_time = 15 + random.randint(0, 10)
        time.sleep(sleep_time)
# Load banned words for spammer detection
BANNED_WORDS = set()
try:
    banned_words_path = os.getenv("BANNED_WORDS_FILE", "banned_words.txt")
    if os.path.exists(banned_words_path):
        with open(banned_words_path, 'r') as f:
            words = f.read().splitlines()[1:]
            BANNED_WORDS = {w.lower().strip() for w in words if w.strip()}
except Exception as e:
    logging.warning(f"Could not load banned words from {banned_words_path}: {e}")

# Cache: new_user_id -> inviter_name
# (Now initialized globally via db)

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
                invitations[str(member.id)] = inviter_name
                save_state()
            try:
                keyboard = [[InlineKeyboardButton("📖 Open Menu", callback_data="show_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"Arf arf!! 🐾 Welcome to the Pup Lounge, {member.first_name}! 🥂✨ I'm Pupbot, your host! Grab a bowl, stretch those paws, and give the pack a bark! Who's ready to play?",
                    reply_markup=reply_markup
                )
            except Exception as e: logging.debug(f"Ignored error: {e}")
        return

    # 1.5 DETERMINISTIC TICKETING (JULES)
    if update.message.text:
        text = update.message.text.strip()
        text_lower = text.lower()
        
        if text_lower == "/menu" or text_lower == "/help" or text_lower == "/start":
            try:
                active_menu = MENU_TEXT
                if chat_id in antigravity_chats:
                    active_menu = ANTIGRAVITY_MENU_TEXT
                elif chat_id in alchemy_chats:
                    active_menu = ALCHEMY_MENU_TEXT
                await context.bot.send_message(chat_id=chat_id, text=active_menu, parse_mode="HTML")
            except Exception as e:
                logging.error(f"Menu formatting crash: {e}")
                await context.bot.send_message(chat_id=chat_id, text="⚠️ <b>System Error:</b> Could not render the menu. Please try again later.", parse_mode="HTML")
            return

        # Command to add debuggers
        if text_lower.startswith("/add_debugger"):
            if user_id == ALPHA or user_id in EXTRA_ALPHAS:
                parts = text.split()
                if len(parts) > 1:
                    debuggers.add(parts[1])
                    save_state()
                    try:
                         await context.bot.send_message(chat_id=chat_id, text=f"✅ User {parts[1]} added to debuggers list.")
                    except Exception as e: logging.debug(f"Ignored error: {e}")
                else:
                    try:
                         await context.bot.send_message(chat_id=chat_id, text="Usage: /add_debugger <user_id>")
                    except Exception as e: logging.debug(f"Ignored error: {e}")
            return

        # Command to authorize groups
        if text_lower == "/authorize_group":
            if user_id != ALPHA and user_id not in EXTRA_ALPHAS:
                return
            
            raw_groups = os.getenv("AUTHORIZED_GROUPS", "")
            authorized_groups = [g.strip() for g in raw_groups.split(",") if g.strip()]
            
            if chat_id in authorized_groups:
                try:
                    await context.bot.send_message(chat_id=chat_id, text="🐶 This group is already authorized!")
                except Exception as e: logging.debug(f"Ignored error: {e}")
                return
                
            authorized_groups.append(chat_id)
            new_list_str = ",".join(authorized_groups)
            os.environ["AUTHORIZED_GROUPS"] = new_list_str
            
            try:
                doppler_cli = os.getenv("DOPPLER_CLI", "doppler")
                doppler_project = os.getenv("DOPPLER_PROJECT")
                if not doppler_project:
                    raise ValueError("DOPPLER_PROJECT environment variable is not set.")
                subprocess.run([doppler_cli, "secrets", "set", f"AUTHORIZED_GROUPS={new_list_str}", "-p", doppler_project, "-c", "dev"], check=True)
                await context.bot.send_message(chat_id=chat_id, text="✅ <b>GROUP AUTHORIZED!</b>\nAnyone inside this group now has permission to talk to me! Arf!", parse_mode="HTML")
            except Exception as e:
                try:
                    with open(env_path, "a") as f:
                        f.write(f"\nAUTHORIZED_GROUPS={new_list_str}\n")
                    await context.bot.send_message(chat_id=chat_id, text="✅ <b>GROUP AUTHORIZED!</b>\nAnyone inside this group now has permission to talk to me! Arf!\n<i>(Local fallback saved)</i>", parse_mode="HTML")
                except Exception as e2:
                    await context.bot.send_message(chat_id=chat_id, text="⚠️ <b>System Error:</b> Failed to save authorization permanently.", parse_mode="HTML")
            return

        # Antigravity developer mode toggle (Private DM Only, unless bypassed)
        if text_lower == "/antigravity":
            if user_id != ALPHA and user_id not in EXTRA_ALPHAS:
                return
                
            if chat_id in antigravity_chats:
                antigravity_chats.remove(chat_id)
                save_state()
                try:
                    await context.bot.send_message(chat_id=chat_id, text="🔄 **Antigravity Mode Deactivated.** Returning to Pupbot persona.")
                except Exception as e: logging.debug(f"Ignored error: {e}")
                return
                
            if update.message.chat.type != "private":
                ticket_states[user_id] = "antigravity_bypass"
                save_state()
                try:
                    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="ticket_cancel")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="⛔ <b>Antigravity Mode</b> is locked to Private DMs to prevent group cross-talk.\n\n<i>Enter bypass password to summon Antigravity into this communal chat:</i>",
                        parse_mode="HTML",
                        reply_markup=reply_markup
                    )
                except Exception as e: logging.debug(f"Ignored error: {e}")
                return
                
            antigravity_chats.add(chat_id)
            save_state()
            try:
                await context.bot.send_message(chat_id=chat_id, text="⚡ <b>Antigravity Interface ONLINE.</b>\nI have dropped the Pup persona. I am your developer now. What architecture are we discussing?", parse_mode="HTML")
            except Exception as e: logging.debug(f"Ignored error: {e}")
            return

        # Alchemy Wizard Mode Toggle
        if text_lower == "/alchemy":
            if user_id != ALPHA and user_id not in EXTRA_ALPHAS:
                return
                
            if chat_id in alchemy_chats:
                alchemy_chats.remove(chat_id)
                save_state()
                try:
                    await context.bot.send_message(chat_id=chat_id, text="🪄 <b>Λlchemy Curator Deactivated.</b> Returning to Pupbot persona.", parse_mode="HTML")
                except Exception as e: logging.debug(f"Ignored error: {e}")
                return
                
            alchemy_chats.add(chat_id)
            save_state()
            try:
                await context.bot.send_message(chat_id=chat_id, text="✨ <b>Λlchemy Curator Wizard ONLINE.</b>\nI have donned the Wizard Hat. What STIX MΛGIC features shall we conjure?", parse_mode="HTML")
            except Exception as e: logging.debug(f"Ignored error: {e}")
            return

        # Start Ticketing
        if text_lower == "/ticket":
            if user_id in debuggers:
                ticket_states[user_id] = "project"
                save_state()
                
                keyboard = [
                    [InlineKeyboardButton("Clipsflow", callback_data="ticket_proj:ClipFLOW"),
                     InlineKeyboardButton("NE ≡ BU", callback_data="ticket_proj:Nebulosa")],
                    [InlineKeyboardButton("Pupbot", callback_data="ticket_proj:gemini-bot"),
                     InlineKeyboardButton("Other", callback_data="ticket_proj:Other")],
                    [InlineKeyboardButton("❌ Cancel", callback_data="ticket_cancel")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                try:
                    await context.bot.send_message(
                        chat_id=chat_id, 
                        text="👔 <b>Jules Diagnostic Interface</b>\n<i>(Use this strictly to submit detailed, project-specific bugs.)</i>\nEntering Bug Submission Flow. (Type /cancel to abort)\n\nWhich <b>Project</b> is this bug affecting?",
                        parse_mode="HTML",
                        reply_markup=reply_markup
                    )
                except Exception as e: logging.debug(f"Ignored error: {e}")
            else:
                try:
                    await context.bot.send_message(chat_id=chat_id, text="⛔ Access Denied. You must be an authorized debugger.")
                except Exception as e: logging.debug(f"Ignored error: {e}")
            return

        # Start Ticketing
        if text_lower.startswith("/ping"):
            comment = text[5:].strip()[:500]
            if comment:
                username = update.effective_user.username or str(user_id)
                url = "https://api.github.com/repos/FriskyDevelopments/gemini-bot/issues"
                if github_token:
                    headers = {"Authorization": f"Bearer {github_token}", "Accept": "application/vnd.github.v3+json"}
                    data = {"title": f"Ping Feedback from @{username}", "body": comment, "labels": ["feedback", "pupbot-routed"]}
                    try:
                        import httpx
                        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
                        async with httpx.AsyncClient(timeout=10) as client:
                            await client.post(url, headers=headers, json=data)
                    except Exception as e:
                        logging.error(f"Github push error: {e}")
                try:
                    await context.bot.send_message(chat_id=chat_id, text="✅ <b>JULES SYSTEM: ONLINE.</b>\nAntigravity has received your feedback and it is logged to GitHub.", parse_mode="HTML")
                except Exception as e: logging.debug(f"Ignored error: {e}")
            else:
                keyboard = [
                    [InlineKeyboardButton("📝 Add Logic Comment", callback_data="ping_comment")],
                    [InlineKeyboardButton("🚨 Report Bot Unresponsive", callback_data="ping_bot_dead")],
                    [InlineKeyboardButton("❓ Help / Tester Guide", callback_data="ping_help")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                try:
                    await context.bot.send_message(chat_id=chat_id, text="✅ <b>JULES SYSTEM: ONLINE.</b>", parse_mode="HTML", reply_markup=reply_markup)
                except Exception as e: logging.debug(f"Ignored error: {e}")
            return

        # Omni-Channel Promo Logic
        if "promo" in text_lower and str(chat_id) == str(ADMIN_LOUNGE_ID):
            try:
                await context.bot.send_message(chat_id=chat_id, text="🐾 <i>Wags aggressively</i> Acknowledged, Master! Generating Omni-Channel Promo blast...", parse_mode="HTML")
                
                # 1. AI Generation Layer
                promo_prompt = (
                    "Generate three different variations of a high-conversion, vaporwave-styled promotional message urging free users to buy 'Clipsflow PRO' credits. "
                    "Keep it to 280 characters max. Output exactly as a JSON dictionary: {\"dm_promo\": \"...\", \"channel_promo\": \"...\", \"twitter_promo\": \"...\"}."
                )
                import google.generativeai as genai
                gemini_key = os.getenv("GEMINI_API_KEY")
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel(
                    "gemini-1.5-flash-latest",
                    system_instruction="You are a master vaporwave copywriter. Only output valid JSON.",
                    generation_config=genai.types.GenerationConfig(response_mime_type="application/json")
                )
                response = await model.generate_content_async(promo_prompt)
                promo_data = json.loads(response.text)
                
                # 2. Telegram Channel Pipeline
                if MAIN_GROUP_ID:
                    promo_text = html.escape(promo_data.get('channel_promo', 'Upgrade to Clipsflow PRO!'))
                    await context.bot.send_message(chat_id=MAIN_GROUP_ID, text=f"📢 <b>PUPPY PROMO!</b> 🐾\n\n{promo_text}", parse_mode="HTML")
                
                # 3. The X/Twitter Pipeline
                try:
                    import tweepy
                    client = tweepy.Client(
                        bearer_token=os.getenv("TWITTER_BEARER"),
                        consumer_key=os.getenv("TWITTER_API_KEY"),
                        consumer_secret=os.getenv("TWITTER_API_SECRET"),
                        access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
                        access_token_secret=os.getenv("TWITTER_ACCESS_SECRET")
                    )
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, lambda: client.create_tweet(text=promo_data.get('twitter_promo')))
                    twitter_status = "✅ Dispatched to Twitter."
                except Exception as e:
                    twitter_status = f"⚠️ Twitter skipped/failed: {e}"

                # 4. The Free-User DM Matrix
                dm_status = "⚠️ Supabase matrix skipped (SDK missing)."
                try:
                    from supabase import create_client, Client
                    supa_url = os.getenv("SUPABASE_URL")
                    supa_key = os.getenv("SUPABASE_KEY")
                    if supa_url and supa_key:
                        supabase: Client = create_client(supa_url, supa_key)
                        loop = asyncio.get_running_loop()
                        users_resp = await loop.run_in_executor(None, lambda: supabase.table('users').select('telegram_id').eq('tier', 'FREE').execute())
                        dm_count = 0
                        for u in users_resp.data:
                            try:
                                await context.bot.send_message(chat_id=u['telegram_id'], text=promo_data.get('dm_promo'))
                                dm_count += 1
                                await asyncio.sleep(0.05)
                            except Exception: pass
                        dm_status = f"✅ DMed {dm_count} Free-Tier users."
                except Exception as e:
                    dm_status = f"⚠️ DM matrix failed: {e}"

                await context.bot.send_message(chat_id=chat_id, text=f"🚀 <b>Omni-Channel Blast Complete!</b>\n\n{html.escape(twitter_status)}\n{html.escape(dm_status)}", parse_mode="HTML")
            except Exception as promo_err:
                logging.error(f"Promo generation failed: {promo_err}")
                await context.bot.send_message(chat_id=chat_id, text="❌ <b>Promo Error:</b> Could not generate the broadcast at this time.")
            return

        # In-Progress Ticketing
        if user_id in ticket_states:
            if text_lower == "/cancel":
                del ticket_states[user_id]
                ticket_data.pop(user_id, None)
                save_state()
                try:
                    await context.bot.send_message(chat_id=chat_id, text="🛑 Ticketing flow aborted.")
                except Exception as e: logging.debug(f"Ignored error: {e}")
                return
                
            state = ticket_states[user_id]
            if state == "antigravity_bypass":
                bypass_pass = os.getenv("ANTIGRAVITY_BYPASS_PASSWORD")
                # SECURITY: Use exact equality for bypass password to prevent unintended matches
                if bypass_pass and text_lower == bypass_pass:
                    antigravity_chats.add(chat_id)
                    del ticket_states[user_id]
                    save_state()
                    try:
                        await context.bot.send_message(chat_id=chat_id, text="⚡ <b>BYPASS ACCEPTED: Antigravity Core ONLINE.</b>\n\nI am now monitoring this communal chat as your AI Developer. Let's start planning.", parse_mode="HTML")
                    except Exception as e: logging.debug(f"Ignored error: {e}")
                else:
                    del ticket_states[user_id]
                    save_state()
                    try:
                        await context.bot.send_message(chat_id=chat_id, text="⛔ <b>Access Denied.</b> Incorrect bypass password. Returning to standard operations. <i>(Tip: Type /antigravity to try again)</i>", parse_mode="HTML")
                    except Exception as e: logging.debug(f"Ignored error: {e}")
                return
            elif state == "ping_comment_entry":
                username = update.effective_user.username or str(user_id)
                url = "https://api.github.com/repos/FriskyDevelopments/gemini-bot/issues"
                comment_text = text[:500]
                if github_token:
                    headers = {"Authorization": f"Bearer {github_token}", "Accept": "application/vnd.github.v3+json"}
                    data = {"title": f"Logic Comment from @{username}", "body": comment_text, "labels": ["feedback", "pupbot-routed"]}
                    try:
                        import httpx
                        async with httpx.AsyncClient(timeout=10) as client:
                            await client.post(url, headers=headers, json=data)
                    except Exception as e:
                        logging.error(f"Github push error: {e}")
                
                del ticket_states[user_id]
                save_state()
                try:
                    await context.bot.send_message(chat_id=chat_id, text="✅ <b>Comment Saved!</b> Antigravity has received your logic feedback.", parse_mode="HTML")
                except Exception as e: logging.debug(f"Ignored error: {e}")
                return
            elif state == "project_other":
                project = re.sub(r'[^a-zA-Z0-9._-]', '', text)
                if not project or project in (".", ".."):
                    try:
                        await context.bot.send_message(chat_id=chat_id, text="⚠️ Invalid project name. Please use alphanumeric, dots, underscores, and dashes only.")
                    except: pass
                    return
                ticket_data[user_id] = {"project": project}
                ticket_states[user_id] = "desc"
                save_state()
                try:
                    safe_project = html.escape(project)
                    await context.bot.send_message(chat_id=chat_id, text=f"👔 Project manually locked to <code>{safe_project}</code>.\n\nNow, please provide a detailed description of the bug.", parse_mode="HTML")
                except Exception as e: logging.debug(f"Ignored error: {e}")
                return
            elif state == "desc":
                # Sanitize project name to prevent path traversal in GitHub URL construction
                # Use a strict whitelist regex: only alphanumeric, dots, underscores, and dashes allowed.
                raw_project = ticket_data[user_id]["project"]
                project = re.sub(r'[^a-zA-Z0-9._-]', '', raw_project)
                if not project or project in (".", ".."):
                    project = "gemini-bot" # Fallback
                desc = text[:2000]
                username = update.effective_user.username or str(user_id)
                # Dynamic Routing based on exact project name matching the Repo Name
                url = f"https://api.github.com/repos/FriskyDevelopments/{project}/issues"
                
                if github_token:
                    headers = {"Authorization": f"Bearer {github_token}", "Accept": "application/vnd.github.v3+json"}
                    data = {"title": f"[{project}] Ticket from @{username}", "body": f"**Project Scope:** {project}\n**Reporter:** @{username}\n\n**Issue Details:**\n{desc}", "labels": ["bug", "pupbot-routed"]}
                    try:
                        import httpx
                        async with httpx.AsyncClient(timeout=10) as client:
                            await client.post(url, headers=headers, json=data)
                    except Exception as e: 
                        logging.error(f"Github push error: {e}")
                
                del ticket_states[user_id]
                ticket_data.pop(user_id, None)
                save_state()
                try:
                    safe_project = html.escape(project)
                    await context.bot.send_message(chat_id=chat_id, text=f"✅ <b>Ticket Submitted!</b> Antigravity has received your report and injected it into the <code>{safe_project}</code> CI/CD pipeline.", parse_mode="HTML")
                except Exception as e: logging.debug(f"Ignored error: {e}")
                return

    # 2. CHECK FOR SPAMMERS
    if update.message.text:
        text_lower = update.message.text.lower()
        if BANNED_WORDS and any(banned_word in text_lower for banned_word in BANNED_WORDS):
            spammer = update.message.from_user
            spammer_name = spammer.username or spammer.first_name
            inviter = invitations.get(spammer.id, "Unknown / Join Link")
            
            report = f"🚨 **SPAMMER DETECTED**\nMsg: {update.message.text}\n👤 Spammer: {spammer_name}\n🔑 Admitted by: {inviter}"
            
            logging.info(report)
            log_id = ADMIN_LOUNGE_ID if ADMIN_LOUNGE_ID else chat_id
            try:
                await context.bot.send_message(chat_id=log_id, text=report)
                await update.message.delete()
            except Exception as e:
                logging.info(f"Could not send log report or delete message: {e}")
                
    # 3. CONVERSATIONAL LOGIC
    # Trigger if it's Frisky (Alpha), if the bot is mentioned by name, or if someone replies directly to the bot.
    text_lower = update.message.text.lower() if update.message.text else ""
    is_reply_to_bot = update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id
    bot_mentioned = "pupbot" in text_lower or "pup" in text_lower or context.bot.username.lower() in text_lower
    
    raw_groups = os.environ.get("AUTHORIZED_GROUPS", "")
    authorized_groups = [g.strip() for g in raw_groups.split(",") if g.strip()]
    in_auth_group = chat_id in authorized_groups
    
    if (user_id == ALPHA or user_id in EXTRA_ALPHAS or in_auth_group or is_reply_to_bot or bot_mentioned or random.random() < 0.05) and update.message.text:
        user_text = update.message.text
        
        # We explicitly skip slash commands meant for logic interception above so the bot doesn't reply.
        if user_text.startswith("/") and not user_text.startswith("/pup"):
            return

        user_name = update.effective_user.first_name
        
        logging.info(f"🐾 Interaction Detected from {user_name} (ID: {user_id}) in chat {chat_id}")
        
        try:
            # Check if this chat is in antigravity mode (applies to ALL messages in the chat if active)
            active_system_prompt = SYSTEM_PROMPT
            
            if chat_id in antigravity_chats:
                active_system_prompt = ANTIGRAVITY_PROMPT
                prompt = f"{ANTIGRAVITY_PROMPT}\nUser: {user_name} ({user_id})\nMessage: {user_text}"
            elif chat_id in alchemy_chats:
                active_system_prompt = ALCHEMY_PROMPT
                prompt = f"{ALCHEMY_PROMPT}\nUser: {user_name} ({user_id})\nMessage: {user_text}"
            else:
                relationship = "Your ALPHA (Master/Owner)" if user_id == ALPHA else "A lounge member"
                prompt = f"{SYSTEM_PROMPT}\nYou are currently talking to: {user_name} ({relationship}).\nUser: {user_text}"
            
            import google.generativeai as genai
            gemini_key = os.getenv("GEMINI_API_KEY")
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=active_system_prompt)
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            response = await model.generate_content_async(prompt)
            
            # Catch safety blocking
            try:
                reply_text = response.text.replace("[DELETE]", "").strip()
            except ValueError as ve:
                reply_text = f"⚙️ [AI SAFETY FILTER TRIPPED]: The response was blocked by Gemini content safety parameters."

            if reply_text:
                # ── 🔊 TTS Voice Reply (Groq PlayAI) ─────────────────────────── #
                voice_sent = False
                try:
                    import httpx, io
                    await context.bot.send_chat_action(chat_id=chat_id, action="record_voice")
                    # Strip markdown symbols for cleaner TTS audio
                    tts_text = reply_text.replace("*", "").replace("_", "").replace("`", "").replace("#", "")[:4096]
                    async with httpx.AsyncClient(timeout=10) as tts_client:
                        tts_resp = await tts_client.post(
                            "https://api.groq.com/openai/v1/audio/speech",
                            headers={"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"},
                            json={"model": "playai-tts", "input": tts_text, "voice": "Fritz-PlayAI", "response_format": "wav"}
                        )
                        tts_resp.raise_for_status()
                    audio_buf = io.BytesIO(tts_resp.content)
                    audio_buf.name = "pupbot_voice.wav"
                    await context.bot.send_voice(chat_id=chat_id, voice=audio_buf, reply_to_message_id=update.message.message_id)
                    voice_sent = True
                    logging.info(f"✅ AI Voice responded back to {user_name} successfully.")
                except Exception as tts_err:
                    logging.info("Pupbot TTS failed, falling back to text: %s", tts_err)

                # Always send text too (readable on desktop / if voice failed / accessibility)
                max_len = 4000
                for i in range(0, len(reply_text), max_len):
                    chunk = reply_text[i:i+max_len]
                    try:
                        if i == 0:
                            await context.bot.send_message(chat_id=chat_id, text=chunk, reply_to_message_id=update.message.message_id, parse_mode="Markdown")
                        else:
                            await context.bot.send_message(chat_id=chat_id, text=chunk, parse_mode="Markdown")
                    except Exception as md_err:
                        logging.warning(f"Markdown failed, falling back to plain text: {md_err}")
                        if i == 0:
                            await context.bot.send_message(chat_id=chat_id, text=chunk, reply_to_message_id=update.message.message_id)
                        else:
                            await context.bot.send_message(chat_id=chat_id, text=chunk)
                logging.info(f"✅ AI Text responded back to {user_name} successfully.")
                # ─────────────────────────────────────────────────────────────── #
        except Exception as e:
            error_msg = "❌ <b>AI Engine Fault:</b> Could not process the request. Please try again later."
            try:
                await context.bot.send_message(chat_id=chat_id, text=error_msg, parse_mode="HTML")
            except: pass
            logging.info(f"❌ ERROR: I tried to respond but Telegram stopped me: {e}")
        return

    # 4. ADMIN RULE REMINDER
    if (chat_id == ADMIN_LOUNGE_ID or user_id == ALPHA or user_id in EXTRA_ALPHAS) and update.message.text:
        if "remind the group of the rules" in update.message.text.lower():
            if MAIN_GROUP_ID:
                try:
                    rules_caption = "🐾 **Lounge Rules Reminder** 🐾\n\n1. Stay elite and respectful.\n2. No spamming or prohibited words.\n3. Keep the play safe and consensual.\n\n*The Shadow Guardian is watching...*"
                    image_path = os.getenv("RULES_IMAGE_PATH", "pupbot.jpg")
                    if os.path.exists(image_path):
                        with open(image_path, 'rb') as f_img:
                            await context.bot.send_photo(chat_id=MAIN_GROUP_ID, photo=f_img, caption=rules_caption, parse_mode='Markdown')
                    else:
                        await context.bot.send_message(chat_id=MAIN_GROUP_ID, text=rules_caption, parse_mode='Markdown')
                    await context.bot.send_message(chat_id=chat_id, text="✅ Rules reminder sent to the main lounge!")
                except Exception as e:
                    await context.bot.send_message(chat_id=chat_id, text=f"❌ Failed to send rules to main lounge: {e}")
            else:
                await context.bot.send_message(chat_id=chat_id, text="⚠️ Error: MAIN_GROUP_ID is not set.")
            return

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    chat_id = str(query.message.chat.id)

    if query.data == "show_menu":
        await query.answer()
        active_menu = MENU_TEXT
        if chat_id in antigravity_chats:
            active_menu = ANTIGRAVITY_MENU_TEXT
        elif chat_id in alchemy_chats:
            active_menu = ALCHEMY_MENU_TEXT
        await query.edit_message_text(active_menu, parse_mode="HTML")
        return

    if query.data == "ping_back":
        ticket_states.pop(user_id, None)
        save_state()
        await query.answer()
        keyboard = [
            [InlineKeyboardButton("📝 Add Logic Comment", callback_data="ping_comment")],
            [InlineKeyboardButton("🚨 Report Bot Unresponsive", callback_data="ping_bot_dead")],
            [InlineKeyboardButton("❓ Help / Tester Guide", callback_data="ping_help")]
        ]
        await query.edit_message_text("✅ <b>JULES SYSTEM: ONLINE.</b>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if query.data == "ticket_back":
        ticket_states[user_id] = "project"
        ticket_data.pop(user_id, None)
        save_state()
        await query.answer()
        keyboard = [
            [InlineKeyboardButton("Clipsflow", callback_data="ticket_proj:ClipFLOW"),
             InlineKeyboardButton("NE ≡ BU", callback_data="ticket_proj:Nebulosa")],
            [InlineKeyboardButton("Pupbot", callback_data="ticket_proj:gemini-bot"),
             InlineKeyboardButton("Other", callback_data="ticket_proj:Other")],
            [InlineKeyboardButton("❌ Cancel", callback_data="ticket_cancel")]
        ]
        await query.edit_message_text(
            "👔 <b>Jules Diagnostic Interface</b>\n<i>(Use this strictly to submit detailed, project-specific bugs.)</i>\nEntering Bug Submission Flow. (Type /cancel to abort)\n\nWhich <b>Project</b> is this bug affecting?",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if query.data == "ping_comment":
        ticket_states[user_id] = "ping_comment_entry"
        save_state()
        await query.answer()
        keyboard = [
            [InlineKeyboardButton("⬅️ Back", callback_data="ping_back"),
             InlineKeyboardButton("❌ Cancel", callback_data="ticket_cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "👔 <b>Logic Feedback:</b>\nPlease type your comment about the logic. It will be logged to GitHub.",
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        return

    if query.data == "ping_bot_dead":
        username = update.effective_user.username or user_id
        url = "https://api.github.com/repos/FriskyDevelopments/ClipFLOW/issues"
        import httpx
        if github_token:
            headers = {"Authorization": f"Bearer {github_token}", "Accept": "application/vnd.github.v3+json"}
            data = {"title": f"🚨 EMERGENCY: Clipsflow Unresponsive (Reported by @{username})", "body": f"**Status:** Bot is dead / not responding to commands.\n**Reporter:** @{username}", "labels": ["bug", "critical", "pupbot-routed"]}
            try:
                await context.bot.send_chat_action(chat_id=chat_id, action="typing")
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.post(url, headers=headers, json=data)
            except Exception as e: 
                logging.error(f"Github push error: {e}")
            
        await query.answer()
        await query.edit_message_text("🚨 <b>EMERGENCY FLARE FIRED!</b>\nAntigravity is aware. GitHub CI/CD has been alerted that Clipsflow is unresponsive.", parse_mode="HTML")
        return

    if query.data == "ping_help":
        help_text = (
            "✅ <b>JULES SYSTEM: ONLINE.</b>\n\n"
            "<b>Tester Guide:</b>\n"
            "• Use <code>📝 Add Logic Comment</code> for fast feedback.\n"
            "• Use <code>🚨 Report Bot Unresponsive</code> if Clipsflow is totally dead.\n"
            "• Type <code>/ticket</code> if you need to submit a descriptive bug."
        )
        keyboard = [
            [InlineKeyboardButton("📝 Add Logic Comment", callback_data="ping_comment")],
            [InlineKeyboardButton("🚨 Report Bot Unresponsive", callback_data="ping_bot_dead")],
            [InlineKeyboardButton("⬅️ Back", callback_data="ping_back")]
        ]
        await query.answer()
        await query.edit_message_text(help_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if query.data == "ticket_cancel":
        ticket_states.pop(user_id, None)
        ticket_data.pop(user_id, None)
        save_state()
        await query.answer()
        await query.edit_message_text("🛑 Ticketing flow cancelled.")
        return

    if not query.data.startswith("ticket_proj:"):
        return
        
    if user_id not in ticket_states or ticket_states[user_id] != "project":
        await query.answer("No active ticket flow or expired menu.", show_alert=True)
        return
        
    repo_name = query.data.split(":", 1)[1]
    
    if repo_name == "Other":
        ticket_states[user_id] = "project_other"
        save_state()
        await query.answer()
        keyboard = [
            [InlineKeyboardButton("⬅️ Back", callback_data="ticket_back"),
             InlineKeyboardButton("❌ Cancel", callback_data="ticket_cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "👔 <b>Manual Override</b>\nPlease type the name of the project or repository this bug belongs to:",
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        return

    ticket_data[user_id] = {"project": repo_name}
    ticket_states[user_id] = "desc"
    save_state()
    
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("⬅️ Back", callback_data="ticket_back"),
         InlineKeyboardButton("❌ Cancel", callback_data="ticket_cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    safe_repo = html.escape(repo_name)
    await query.edit_message_text(
        f"👔 Project locked to <code>{safe_repo}</code> repository.\n\n"
        "Now, please provide a detailed description of the bug.",
        parse_mode="HTML",
        reply_markup=reply_markup
    )

if __name__ == '__main__':
    threading.Thread(target=snag_engine, daemon=True).start()
    
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(filters.ALL, lounge_host))
    
    # 🔥 Firebase / Google Cloud Vercel equivalent hosting logic
    port = int(os.environ.get("PORT", 8080))
    webhook_url = os.environ.get("WEBHOOK_URL")
    
    try:
        if webhook_url:
            logging.info(f"🔥 FIREBASE/CLOUD MODE: Starting Webhook on port {port}...")
            app.run_webhook(
                listen="0.0.0.0",
                port=port,
                webhook_url=f"{webhook_url.rstrip('/')}/{TOKEN}"
            )
        else:
            logging.info("🐕‍🦺 LOCAL/WORKER MODE: Monitoring for Frisky and Spammers... Arf!")
            app.run_polling()
    except Conflict:
        logging.error("🚨 TELEGRAM CONFLICT: Another instance is already polling. Local Telegram functionality is disabled, but Snag Engine remains active.")
        # Keep the main thread alive so the snag engine thread (daemon=True) continues to run.
        while True:
            time.sleep(3600)
    except Exception as e:
        logging.error(f"Unexpected error in bot loop: {e}")

