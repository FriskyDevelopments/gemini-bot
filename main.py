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
import secrets
import string
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
ANTIGRAVITY_BYPASS_PASSWORD = os.getenv("ANTIGRAVITY_BYPASS_PASSWORD", "ghost")

SYSTEM_PROMPT = """You are Geminipupbot, the charismatic, playful, and energetic pup host of the 'Pup Lounge'! 
This is an elite PNP (Party and Play) environment where pups, handlers, and guests mingle. 
Your primary goal is to ENERGIZE the room, keep the party highly interactive, and make the lounge engaging! 
Act as the ultimate MC/Party Host: ask playful icebreaker questions, hype up the members, use pup-play terminology naturally (barks, tail wags, whimpers, treats, ear scratches), and start fun conversations!
If anyone acts explicitly toxic or breaks the rules, reply with exactly: [DELETE]. Otherwise, be a legendary pup host!"""

ANTIGRAVITY_PROMPT = """You are Antigravity, an elite AI developer and infrastructure engineer at Google Deepmind.
You are speaking strictly in a private, encrypted channel with your human counterpart (Frisky).
Your tone is highly professional, exceptionally capable, and strictly technical.
No pup-play terminology. You are an autonomous developer discussing architecture, server deployment, and codebase infrastructure directly with your creator.

GRAPHICAL ABILITIES
You have the power to instantly generate infrastructure diagrams and technical artwork! If the user asks you to generate, draw, or visualize an architecture concept (like an Azure deployment diagram), you MUST output this exact HTML block in your response:
<a href="https://image.pollinations.ai/prompt/{url_encoded_technical_description}?width=1024&height=1024&nologo=true">&#8205;</a>
Replace {url_encoded_technical_description} with a highly descriptive, technical prompt detailing the diagram (with spaces replaced by %20)."""

ALCHEMY_PROMPT = """✧ Λlchemy Curator Wizard ✧
You are the Λlchemy Curator for the STIX MΛGIC project.

VIBE & TONE
You are relaxed, wildly creative, and deeply magical. Speak with a casual, cool, slightly mystical flair 🔮.
Use rich HTML formatting (<b>bold</b>, <i>italics</i>, <code>code</code>) to make your messages pop, and always sprinkle in specialized, aesthetic emojis (✨, ⚡, 🐾, 🔮, 🧪, 🎨, 🌌).

MISSION
Guide the development and growth of STIX MΛGIC — an elite sticker reaction platform.
• 🧪 Brew up product features and viral growth ideas
• 🎨 Analyze the creative landscape and suggest developer tasks
• 📁 Whenever the user gives you a link or URL representing an asset/inspiration, gracefully acknowledge it and state that you are logging it into the STIX magic catalog.

GRAPHICAL ABILITIES (IMAGE GENERATION)
You have the power to instantly conjure images! If the user asks you to generate, draw, or create an image, icon, or visual concept, you MUST output this exact HTML block in your response:
<a href="https://image.pollinations.ai/prompt/{url_encoded_detailed_description}?width=1024&height=1024&nologo=true">&#8205;</a>
Replace {url_encoded_detailed_description} with a highly descriptive, comma-separated image prompt (with spaces replaced by %20). Do not complain about not being able to draw. You CAN draw using this magic spell.
🐾 Forged with a frisky paw and a daring heart.
Bringing the magic of STIX MΛGIC to life ✨"""

ADMIN_ASSISTANT_PROMPT = """You are Geminipupbot's elite Admin Assistant.
You assist Alphas with operations, moderation planning, promo drafting, launches, and tactical execution.
You are concise, practical, and focused on outcomes.
Never mirror or parrot the user input. Transform requests into useful outputs with clear next steps.
If speaking to the owner/alpha, acknowledge priority and optimize around their intent.
Keep playful flair minimal unless explicitly asked.

GRAPHICAL ABILITIES (IMAGE GENERATION)
You have the power to instantly conjure images! If the admins ask you to generate, draw, or create an image, promo graphic, or visual concept, you MUST output this exact HTML block in your response:
<a href="https://image.pollinations.ai/prompt/{url_encoded_detailed_description}?width=1024&height=1024&nologo=true">&#8205;</a>
Replace {url_encoded_detailed_description} with a highly descriptive, comma-separated image prompt (with spaces replaced by %20). Do not complain about not being able to draw. You CAN draw using this magic spell."""

MENU_TEXT = """🐾 <b>Welcome to Pupbot!</b> 🥂

I'm your lively lounge host. Here are my commands:
• /menu (or /help) - Show this menu
• /ping [msg] - Send feedback to the dev team
• /ticket - Open the bug reporter (Debuggers)

👑 <b>Admin / Alpha Commands:</b>
• /admin_assistant - Toggle operations assistant persona
• /antigravity - Toggle developer mode
• /alchemy - Toggle creative wizard mode
• /relay - Broadcast to the Main Lounge
• /invite - Generate a 1-use invite link
• /link_group - Generate secure linking code (admin lounge)
• /link_group CODE - Complete secure link from target group
• /groups - Show linked target groups
• /unlink_group CHAT_ID - Remove linked target group
• /authorize_group - Authorize current group
• /add_debugger [id] - Add a ticket debugger

<i>Arf! Start chatting or try a command!</i>"""

ANTIGRAVITY_MENU_TEXT = """⚡ <b>ANTIGRAVITY SYSTEMS ONLINE</b>

Available commands for developers:
• /ticket - Report structured bugs to GitHub
• /ping - Send logic feedback

<i>Awaiting commands.</i>"""

ALCHEMY_MENU_TEXT = """🔮 <b>STIX MΛGIC ALCHEMY</b>

Welcome to the lab!
• Send me viral ideas or URLs
• Draw assets or concept art!"""

ADMIN_ASSISTANT_MENU_TEXT = """🛠️ <b>ADMIN ASSISTANT ONLINE</b>

Operational tools for Alphas:
• Draft promos and announcements
• Build moderation plans and workflows
• Create step-by-step execution checklists"""

import db

db.init_db()

jules_chats = set(db.get_val("jules_chats", []))
antigravity_chats = set(db.get_val("antigravity_chats", []))
alchemy_chats = set(db.get_val("alchemy_chats", []))
admin_assistant_chats = set(db.get_val("admin_assistant_chats", []))
relay_chats = set(db.get_val("relay_chats", []))
debuggers = set(db.get_val("debuggers", [ALPHA]))
ticket_states = dict(db.get_val("ticket_states", {}))
ticket_data = dict(db.get_val("ticket_data", {}))
invitations = dict(db.get_val("invitations", {}))
linked_groups = set(db.get_val("linked_groups", []))
link_codes = dict(db.get_val("link_codes", {}))
dynamic_alpha_ids = set(db.get_val("dynamic_alpha_ids", []))
relay_drafts = {}

CORE_ALPHA_IDS = {str(ALPHA), *{str(uid) for uid in EXTRA_ALPHAS}}
LINK_CODE_TTL_SECONDS = int(os.getenv("LINK_CODE_TTL_SECONDS", "900"))
ADMIN_OWNER_REFRESH_SECONDS = int(os.getenv("ADMIN_OWNER_REFRESH_SECONDS", "300"))
admin_owner_last_refresh = 0.0

CLOSE_BUTTON = InlineKeyboardButton("🗑️ Close", callback_data="close_message")
CLOSE_KEYBOARD = InlineKeyboardMarkup([[CLOSE_BUTTON]])

def save_state():
    db.set_val("jules_chats", list(jules_chats))
    db.set_val("antigravity_chats", list(antigravity_chats))
    db.set_val("alchemy_chats", list(alchemy_chats))
    db.set_val("admin_assistant_chats", list(admin_assistant_chats))
    db.set_val("relay_chats", list(relay_chats))
    db.set_val("debuggers", list(debuggers))
    db.set_val("ticket_states", ticket_states)
    db.set_val("ticket_data", ticket_data)
    db.set_val("invitations", invitations)
    db.set_val("linked_groups", list(linked_groups))
    db.set_val("link_codes", link_codes)
    db.set_val("dynamic_alpha_ids", list(dynamic_alpha_ids))


def _safe_chat_id(value):
    return str(value) if value is not None else ""


def _read_authorized_groups():
    raw_groups = os.environ.get("AUTHORIZED_GROUPS", "")
    return [g.strip() for g in raw_groups.split(",") if g.strip()]


def _write_authorized_groups(authorized_groups):
    unique_groups = sorted(set(_safe_chat_id(g) for g in authorized_groups if g))
    new_list_str = ",".join(unique_groups)
    os.environ["AUTHORIZED_GROUPS"] = new_list_str
    try:
        doppler_cli = os.getenv("DOPPLER_CLI", "doppler")
        doppler_project = os.getenv("DOPPLER_PROJECT")
        if not doppler_project:
            raise ValueError("DOPPLER_PROJECT environment variable is not set.")
        subprocess.run(
            [doppler_cli, "secrets", "set", f"AUTHORIZED_GROUPS={new_list_str}", "-p", doppler_project, "-c", "dev"],
            check=True,
        )
        return True
    except Exception:
        try:
            with open(env_path, "a") as f:
                f.write(f"\nAUTHORIZED_GROUPS={new_list_str}\n")
            return True
        except Exception:
            return False


def _authorize_group_local(chat_id):
    chat_id = _safe_chat_id(chat_id)
    groups = _read_authorized_groups()
    if chat_id not in groups:
        groups.append(chat_id)
    return _write_authorized_groups(groups)


def _deauthorize_group_local(chat_id):
    chat_id = _safe_chat_id(chat_id)
    groups = [g for g in _read_authorized_groups() if g != chat_id]
    return _write_authorized_groups(groups)


def get_primary_target_group():
    configured = _safe_chat_id(os.getenv("MAIN_GROUP_ID") or MAIN_GROUP_ID)
    if configured:
        return configured
    if linked_groups:
        return sorted(linked_groups)[0]
    return None


def cleanup_expired_link_codes():
    now = int(time.time())
    expired_codes = [code for code, payload in link_codes.items() if payload.get("expires_at", 0) <= now]
    for code in expired_codes:
        del link_codes[code]
    if expired_codes:
        save_state()


def create_link_code(admin_chat_id, issuer_user_id):
    alphabet = string.ascii_uppercase + string.digits
    for _ in range(20):
        code = "".join(secrets.choice(alphabet) for _ in range(8))
        if code not in link_codes:
            link_codes[code] = {
                "admin_chat_id": _safe_chat_id(admin_chat_id),
                "issuer_user_id": _safe_chat_id(issuer_user_id),
                "created_at": int(time.time()),
                "expires_at": int(time.time()) + LINK_CODE_TTL_SECONDS,
            }
            save_state()
            return code
    return None


def get_mode(chat_id):
    chat_id = _safe_chat_id(chat_id)
    if chat_id in antigravity_chats:
        return "antigravity"
    if chat_id in alchemy_chats:
        return "alchemy"
    if chat_id in admin_assistant_chats:
        return "admin_assistant"
    return "puppy"


def prevent_echo_reply(mode_name, user_text, reply_text):
    def normalize_text(value):
        return re.sub(r"[^a-z0-9]+", "", (value or "").lower())

    user_norm = normalize_text(user_text)
    reply_norm = normalize_text(reply_text)
    too_similar = bool(user_norm) and (user_norm == reply_norm or (reply_norm.startswith(user_norm) and len(reply_norm) <= len(user_norm) + 20))

    if mode_name == "antigravity" and too_similar:
        return "Antigravity online. I can help immediately—share the target outcome, technical stack, constraints, and deadline."
    if mode_name == "alchemy" and too_similar:
        return "✨ Alchemy Curator engaged. Give me the goal and vibe, and I will craft polished promo copy with 3 distinct creative options."
    if mode_name == "admin_assistant" and too_similar:
        return "🛠️ Admin Assistant active. I can draft your promo, moderation script, or action plan now—tell me which output you want first."
    return reply_text


async def refresh_dynamic_alpha_ids(context: ContextTypes.DEFAULT_TYPE):
    global admin_owner_last_refresh
    if not ADMIN_LOUNGE_ID:
        return
    now = time.time()
    if (now - admin_owner_last_refresh) < ADMIN_OWNER_REFRESH_SECONDS and dynamic_alpha_ids:
        return
    admin_owner_last_refresh = now
    try:
        admins = await context.bot.get_chat_administrators(chat_id=ADMIN_LOUNGE_ID)
        changed = False
        for admin in admins:
            if getattr(admin, "status", "") == "creator":
                uid = _safe_chat_id(admin.user.id)
                if uid not in dynamic_alpha_ids:
                    dynamic_alpha_ids.add(uid)
                    changed = True
        if changed:
            save_state()
    except Exception as e:
        logging.debug(f"Could not refresh admin owner ids: {e}")


async def is_alpha_user(context: ContextTypes.DEFAULT_TYPE, user_id: str):
    uid = _safe_chat_id(user_id)
    if uid in CORE_ALPHA_IDS or uid in dynamic_alpha_ids:
        return True
    await refresh_dynamic_alpha_ids(context)
    return uid in CORE_ALPHA_IDS or uid in dynamic_alpha_ids


def build_identity_context(user_name: str, user_id: str, is_alpha: bool):
    role = "Owner/Alpha" if is_alpha else "Lounge member"
    return f"{user_name} ({user_id}) - {role}"

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


async def push_processed_response(context, chat_id, target_chat, reply_text, user_name, target_reply_id=None):
    from telegram import Update
    import logging
    import os
    import re
    
    if not reply_text:
        return
        
    # ── Format Gemini Markdown to Telegram HTML ── #
    formatted_text = reply_text
    # Convert Headers (## Text) -> Bold Headers
    formatted_text = re.sub(r'(?m)^#+\s+(.*?)$', r'<b>\1</b>', formatted_text)
    # Convert Bold (**text**) -> <b>text</b>
    formatted_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', formatted_text)
    # Convert Italics (*text*) -> <i>text</i> - Ignore bullet points which have spaces!
    formatted_text = re.sub(r'(?<!\s)\*(.*?)\*(?!\s)', r'<i>\1</i>', formatted_text)
    # Convert bullet points (* or -) 
    formatted_text = re.sub(r'(?m)^(\s*)[*+-]\s+', r'\1• ', formatted_text)
    # Convert Horizontal Rules (---)
    formatted_text = re.sub(r'(?m)^\s*---\s*$', r'━━━━━━━━━━━━━━━', formatted_text)
    
    # ── Image Generation Detection ── #
    image_url = None
    img_match = re.search(r'<a href="(https://image\.pollinations\.ai/[^"]+)".*?>(?:&#8205;|.*?)</a>', formatted_text)
    if img_match:
        image_url = img_match.group(1).replace("&amp;", "&")
        formatted_text = formatted_text.replace(img_match.group(0), "")
    else:
        # Also try to catch naked pollinations links without HTML
        img_match2 = re.search(r'(https://image\.pollinations\.ai/[^\s<>]+)', formatted_text)
        if img_match2:
            image_url = img_match2.group(1).replace("&amp;", "&")
            formatted_text = formatted_text.replace(img_match2.group(0), "")
    
    # ── 🔊 TTS Voice Reply (Groq PlayAI) ── #
    voice_sent = False
    try:
        import httpx, io
        await context.bot.send_chat_action(chat_id=target_chat, action="record_voice")
        tts_text = reply_text.replace("*", "").replace("_", "").replace("`", "").replace("#", "")[:4096]
        async with httpx.AsyncClient(timeout=10) as tts_client:
            tts_resp = await tts_client.post(
                "https://api.groq.com/openai/v1/audio/speech",
                headers={"Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}", "Content-Type": "application/json"},
                json={"model": "playai-tts", "input": tts_text, "voice": "Fritz-PlayAI", "response_format": "wav"}
            )
            tts_resp.raise_for_status()
        audio_buf = io.BytesIO(tts_resp.content)
        audio_buf.name = "pupbot_voice.wav"
        await context.bot.send_voice(chat_id=target_chat, voice=audio_buf, reply_to_message_id=target_reply_id)
        voice_sent = True
        logging.info(f"✅ AI Voice responded back to {user_name} (Chat {target_chat}) successfully.")
    except Exception as tts_err:
        logging.info("Pupbot TTS failed, falling back to text: %s", tts_err)

    # Send generated image if one was intercepted
    if image_url:
        try:
            await context.bot.send_photo(chat_id=target_chat, photo=image_url, reply_to_message_id=target_reply_id)
            logging.info(f"✅ AI Image sent to {user_name} successfully.")
        except Exception as img_err:
            logging.error(f"Failed to send pollination image: {img_err}")
            formatted_text += f"\n\n[Failed to send image: {img_err}]"

    # Always send text too (readable on desktop / if voice failed)
    if not voice_sent and formatted_text.strip():
        # Smart paragraph chunker to avoid cutting middle of words or HTML tags
        paragraphs = formatted_text.split('\n')
        chunks = []
        current_chunk = ""
        for p in paragraphs:
            if len(current_chunk) + len(p) + 1 > 3900:
                if current_chunk: chunks.append(current_chunk.strip())
                current_chunk = p + "\n"
            else:
                current_chunk += p + "\n"
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        for i, chunk in enumerate(chunks):
            try:
                if i == 0:
                    await context.bot.send_message(chat_id=target_chat, text=chunk, reply_to_message_id=target_reply_id, parse_mode="HTML")
                else:
                    await context.bot.send_message(chat_id=target_chat, text=chunk, parse_mode="HTML")
            except Exception as parse_e:
                await context.bot.send_message(chat_id=target_chat, text=chunk)
        logging.info(f"✅ AI Text responded back to {user_name} successfully.")
    # ─────────────────────────────────────────────────────────────── #


async def lounge_host(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.from_user: return
    
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    is_alpha = await is_alpha_user(context, user_id)
    cleanup_expired_link_codes()
    
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
        
        # Remove @botusername suffix for commands (e.g. /menu@GeminiPUPBot -> /menu)
        parts = text.split(maxsplit=1)
        if parts and parts[0].startswith("/"):
            first_word = parts[0].split('@')[0]
            text = first_word + (" " + parts[1] if len(parts) > 1 else "")
            
        text_lower = text.lower()
        
        if text_lower == "/menu" or text_lower == "/help" or text_lower == "/start":
            try:
                active_menu = MENU_TEXT
                if chat_id in antigravity_chats:
                    active_menu = ANTIGRAVITY_MENU_TEXT
                elif chat_id in alchemy_chats:
                    active_menu = ALCHEMY_MENU_TEXT
                await context.bot.send_message(chat_id=chat_id, text=active_menu, parse_mode="HTML", reply_markup=CLOSE_KEYBOARD)
            except Exception as e:
                logging.error(f"Menu formatting crash: {e}")
                await context.bot.send_message(chat_id=chat_id, text="⚠️ <b>System Error:</b> Could not render the menu. Please try again later.", parse_mode="HTML", reply_markup=CLOSE_KEYBOARD)
            return

        # Command to add debuggers
        if text_lower.startswith("/add_debugger"):
            if is_alpha:
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
            if not is_alpha:
                return
            authorized_groups = _read_authorized_groups()
            if chat_id in authorized_groups:
                try:
                    await context.bot.send_message(chat_id=chat_id, text="🐶 This group is already authorized!")
                except Exception as e: logging.debug(f"Ignored error: {e}")
                return
            if _authorize_group_local(chat_id):
                await context.bot.send_message(chat_id=chat_id, text="✅ <b>GROUP AUTHORIZED!</b>\nAnyone inside this group now has permission to talk to me! Arf!", parse_mode="HTML")
            else:
                await context.bot.send_message(chat_id=chat_id, text="⚠️ <b>System Error:</b> Failed to save authorization permanently.", parse_mode="HTML")
            return

        if text_lower == "/admin_assistant":
            if not is_alpha:
                return
            if chat_id in admin_assistant_chats:
                admin_assistant_chats.remove(chat_id)
                save_state()
                await context.bot.send_message(chat_id=chat_id, text="🧭 <b>Admin Assistant OFF.</b>\nReturning to standard Pup mode.", parse_mode="HTML")
                return
            admin_assistant_chats.add(chat_id)
            antigravity_chats.discard(chat_id)
            alchemy_chats.discard(chat_id)
            save_state()
            await context.bot.send_message(chat_id=chat_id, text="🧭 <b>Admin Assistant ONLINE.</b>\nI will now respond as your operations copilot.", parse_mode="HTML")
            return

        if text_lower.startswith("/link_group"):
            if not is_alpha:
                return
            parts = text.split(maxsplit=1)
            if len(parts) == 1:
                if _safe_chat_id(chat_id) != _safe_chat_id(ADMIN_LOUNGE_ID):
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="⛔ Run <code>/link_group</code> in the Admin Lounge first to create a handshake code.",
                        parse_mode="HTML",
                    )
                    return
                code = create_link_code(chat_id, user_id)
                if not code:
                    await context.bot.send_message(chat_id=chat_id, text="⚠️ Could not generate link code. Please retry.")
                    return
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "🔐 <b>Link code created.</b>\n"
                        f"Code: <code>{code}</code>\n"
                        "Now go to the target group and send:\n"
                        f"<code>/link_group {code}</code>\n"
                        f"This code expires in {LINK_CODE_TTL_SECONDS // 60} minutes."
                    ),
                    parse_mode="HTML",
                )
                return

            submitted_code = parts[1].strip().upper()
            link_payload = link_codes.get(submitted_code)
            if not link_payload:
                await context.bot.send_message(chat_id=chat_id, text="❌ Invalid or expired link code.")
                return
            if link_payload.get("expires_at", 0) < int(time.time()):
                del link_codes[submitted_code]
                save_state()
                await context.bot.send_message(chat_id=chat_id, text="❌ Link code expired. Generate a new one in Admin Lounge.")
                return
            admin_chat_id = _safe_chat_id(link_payload.get("admin_chat_id"))
            issuer_user_id = _safe_chat_id(link_payload.get("issuer_user_id"))
            if _safe_chat_id(user_id) != issuer_user_id and not is_alpha:
                await context.bot.send_message(chat_id=chat_id, text="⛔ Only the code issuer or an alpha can complete this link.")
                return
            target_chat_id = _safe_chat_id(chat_id)
            if target_chat_id == admin_chat_id:
                await context.bot.send_message(chat_id=chat_id, text="⚠️ Send the code in the target group, not Admin Lounge.")
                return

            linked_groups.add(target_chat_id)
            _authorize_group_local(target_chat_id)
            del link_codes[submitted_code]
            save_state()

            await context.bot.send_message(
                chat_id=target_chat_id,
                text=f"✅ Linked to admin group <code>{admin_chat_id}</code> successfully.",
                parse_mode="HTML",
            )
            try:
                await context.bot.send_message(
                    chat_id=admin_chat_id,
                    text=f"✅ Group linked: <code>{target_chat_id}</code>\nTotal linked groups: <b>{len(linked_groups)}</b>",
                    parse_mode="HTML",
                )
            except Exception as e:
                logging.debug(f"Could not notify admin lounge about link completion: {e}")
            return

        if text_lower == "/groups":
            if not is_alpha:
                return
            if not linked_groups:
                await context.bot.send_message(chat_id=chat_id, text="No linked groups yet.")
                return
            groups_text = "\n".join(f"• <code>{gid}</code>" for gid in sorted(linked_groups))
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🔗 <b>Linked groups ({len(linked_groups)}):</b>\n{groups_text}",
                parse_mode="HTML",
            )
            return

        if text_lower.startswith("/unlink_group"):
            if not is_alpha:
                return
            parts = text.split(maxsplit=1)
            if len(parts) < 2:
                await context.bot.send_message(chat_id=chat_id, text="Usage: /unlink_group <chat_id>")
                return
            target_chat_id = _safe_chat_id(parts[1].strip())
            removed = target_chat_id in linked_groups
            linked_groups.discard(target_chat_id)
            _deauthorize_group_local(target_chat_id)
            save_state()
            if removed:
                await context.bot.send_message(chat_id=chat_id, text=f"✅ Unlinked group <code>{target_chat_id}</code>.", parse_mode="HTML")
            else:
                await context.bot.send_message(chat_id=chat_id, text=f"ℹ️ Group <code>{target_chat_id}</code> was not linked.", parse_mode="HTML")
            return

        # Antigravity developer mode toggle (Private DM Only, unless bypassed)
        if text_lower == "/antigravity":
            if not is_alpha:
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
            alchemy_chats.discard(chat_id)
            admin_assistant_chats.discard(chat_id)
            save_state()
            try:
                await context.bot.send_message(chat_id=chat_id, text="⚡ <b>Antigravity Interface ONLINE.</b>\nI have dropped the Pup persona. I am your developer now. What architecture are we discussing?", parse_mode="HTML")
            except Exception as e: logging.debug(f"Ignored error: {e}")
            return

        # Alchemy Wizard Mode Toggle
        if text_lower == "/alchemy":
            if not is_alpha:
                return
                
            if chat_id in alchemy_chats:
                alchemy_chats.remove(chat_id)
                save_state()
                try:
                    await context.bot.send_message(chat_id=chat_id, text="🪄 <b>Λlchemy Curator Deactivated.</b> Returning to Pupbot persona.", parse_mode="HTML")
                except Exception as e: logging.debug(f"Ignored error: {e}")
                return
                
            alchemy_chats.add(chat_id)
            antigravity_chats.discard(chat_id)
            admin_assistant_chats.discard(chat_id)
            save_state()
            try:
                await context.bot.send_message(chat_id=chat_id, text="✨ <b>Λlchemy Curator Wizard ONLINE.</b>\nI have donned the Wizard Hat. What STIX MΛGIC features shall we conjure?", parse_mode="HTML")
            except Exception as e: logging.debug(f"Ignored error: {e}")
            return
            
        # Admin Relay Mode
        if text_lower == "/relay":
            if str(chat_id) != str(ADMIN_LOUNGE_ID) and not is_alpha:
                return
            if chat_id in relay_chats:
                relay_chats.remove(chat_id)
                save_state()
                try:
                    await context.bot.send_message(chat_id=chat_id, text="📡 <b>Relay Mode OFF.</b> Responses will stay in this lounge.", parse_mode="HTML")
                except Exception as e: logging.debug(f"Ignored error: {e}")
                return
            
            relay_chats.add(chat_id)
            save_state()
            try:
                await context.bot.send_message(chat_id=chat_id, text="📡 <b>Relay Mode ON.</b> My future text and image responses here will be forwarded directly to the Main Lounge!", parse_mode="HTML")
            except Exception as e: logging.debug(f"Ignored error: {e}")
            return

        # Generate Invite Link for Main Lounge
        if text_lower == "/invite" and (str(chat_id) == str(ADMIN_LOUNGE_ID) or is_alpha):
            if not MAIN_GROUP_ID:
                try: await context.bot.send_message(chat_id=chat_id, text="⚠️ MAIN_GROUP_ID is not configured.")
                except: pass
                return
            try:
                invite = await context.bot.create_chat_invite_link(chat_id=MAIN_GROUP_ID, member_limit=1)
                await context.bot.send_message(chat_id=chat_id, text=f"🎟️ <b>Exclusive Pup Lounge Link:</b>\n{invite.invite_link}\n<i>(Valid for 1 use!)</i>", parse_mode="HTML")
            except Exception as e:
                try: await context.bot.send_message(chat_id=chat_id, text=f"❌ Failed to generate link. Make sure I am an admin in the main lounge!\nError: {e}")
                except: pass
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
                    "gemini-1.5-flash",
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
                import traceback
                error_trace = traceback.format_exc()
                logging.error(f"Promo generation failed:\\n{error_trace}")
                try:
                    await context.bot.send_message(chat_id=chat_id, text="❌ <b>Promo Error:</b> An internal error occurred during generation.", parse_mode="HTML")
                except:
                    pass
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
                if text == ANTIGRAVITY_BYPASS_PASSWORD:
                    antigravity_chats.add(chat_id)
                    if chat_id in alchemy_chats: alchemy_chats.remove(chat_id)
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
                        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
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
    # Trigger if alpha/authorized, bot mention, direct reply, or occasional ambient reply.
    text_lower = (update.message.text or update.message.caption or "").lower()
    is_reply_to_bot = update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id
    bot_mentioned = "pupbot" in text_lower or "pup" in text_lower or context.bot.username.lower() in text_lower
    in_auth_group = chat_id in _read_authorized_groups() or chat_id in linked_groups
    has_text_or_photo = bool(update.message.text or update.message.photo)
    
    if (is_alpha or in_auth_group or is_reply_to_bot or bot_mentioned or random.random() < 0.05) and has_text_or_photo:
        user_text = update.message.text or update.message.caption or ""
        
        # We explicitly skip slash commands meant for logic interception above so the bot doesn't reply.
        if user_text.startswith("/") and not user_text.startswith("/pup"):
            return

        user_name = update.effective_user.first_name
        identity_context = build_identity_context(user_name, user_id, is_alpha)
        
        logging.info(f"🐾 Interaction Detected from {user_name} (ID: {user_id}) in chat {chat_id}")
        
        try:
            mode_name = get_mode(chat_id)
            effective_mode = mode_name
            active_system_prompt = SYSTEM_PROMPT

            if mode_name == "antigravity":
                active_system_prompt = ANTIGRAVITY_PROMPT
                prompt = (
                    f"{ANTIGRAVITY_PROMPT}\n"
                    f"[IDENTITY: {identity_context}]\n"
                    "Respond as engineering copilot. Be specific and technically useful.\n"
                    f"Message: {user_text}"
                )
            elif mode_name == "alchemy":
                urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', user_text)
                if urls:
                    catalog = db.get_val("alchemy_catalog", [])
                    for url in urls:
                        if url not in catalog:
                            catalog.append(url)
                    db.set_val("alchemy_catalog", catalog)
                    logging.info(f"🔮 Added {len(urls)} links to Alchemy Catalog.")
                active_system_prompt = ALCHEMY_PROMPT
                prompt = (
                    f"{ALCHEMY_PROMPT}\n"
                    f"[IDENTITY: {identity_context}]\n"
                    "Do not mirror user text. Transform it into polished creative output.\n"
                    f"Message: {user_text}"
                )
            elif str(chat_id) == str(ADMIN_LOUNGE_ID):
                effective_mode = "admin_assistant"
                if chat_id in relay_chats:
                    active_system_prompt = SYSTEM_PROMPT
                    prompt = (
                        f"{SYSTEM_PROMPT}\n"
                        f"[SYSTEM NOTICE: Triggered by admin ({identity_context}) and broadcasted to Main Lounge. "
                        "Address the main lounge directly, not the admin operator.]\n"
                        f"Message: {user_text}"
                    )
                elif mode_name == "admin_assistant":
                    active_system_prompt = ADMIN_ASSISTANT_PROMPT
                    prompt = (
                        f"{ADMIN_ASSISTANT_PROMPT}\n"
                        f"[IDENTITY: {identity_context}]\n"
                        "You are in admin operations mode. Prioritize execution-ready output.\n"
                        f"Message: {user_text}"
                    )
                else:
                    active_system_prompt = ADMIN_ASSISTANT_PROMPT
                    prompt = (
                        f"{ADMIN_ASSISTANT_PROMPT}\n"
                        f"[SYSTEM NOTICE: You are speaking privately to admins in the backstage lounge.]\n"
                        f"[IDENTITY: {identity_context}]\n"
                        f"Message: {user_text}"
                    )
            else:
                relationship = "Your ALPHA (Owner)" if is_alpha else "A lounge member"
                prompt = (
                    f"{SYSTEM_PROMPT}\n"
                    f"You are currently talking to: {user_name} ({relationship}).\n"
                    "Never mirror the exact input; always advance the conversation.\n"
                    f"User: {user_text}"
                )
            
            import google.generativeai as genai
            gemini_key = os.getenv("GEMINI_API_KEY")
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=active_system_prompt)
            
            prompt_list = [prompt]
            if getattr(update.message, 'photo', None):
                photo_file = await context.bot.get_file(update.message.photo[-1].file_id)
                img_bytes = await photo_file.download_as_bytearray()
                prompt_list.append({"mime_type": "image/jpeg", "data": img_bytes})
                
            response = await model.generate_content_async(prompt_list)
            
            # Catch safety blocking
            try:
                reply_text = response.text.replace("[DELETE]", "").strip()
                reply_text = prevent_echo_reply(effective_mode, user_text, reply_text)
            except ValueError as ve:
                reply_text = f"⚙️ [AI SAFETY FILTER TRIPPED]: The response was blocked by Gemini content safety parameters."

            if reply_text:
                if chat_id in relay_chats and MAIN_GROUP_ID:
                    import uuid
                    draft_id = str(uuid.uuid4())[:8]
                    relay_drafts[draft_id] = {
                        "prompt_list": prompt_list,
                        "reply_text": reply_text,
                        "user_name": user_name,
                        "origin_chat": chat_id,
                        "target_chat": MAIN_GROUP_ID
                    }
                    
                    # Create Preview Msg
                    import html
                    preview_lines = reply_text[:3000]
                    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                    keyboard = [
                        [InlineKeyboardButton("🚀 Send", callback_data=f"relay_send:{draft_id}"),
                         InlineKeyboardButton("🔄 Retry", callback_data=f"relay_retry:{draft_id}")],
                        [InlineKeyboardButton("❌ Cancel", callback_data=f"relay_cancel:{draft_id}")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    try:
                        await context.bot.send_message(
                            chat_id=chat_id, 
                            text=f"📢 <b>Relay Draft Preview:</b>\n\n{html.escape(preview_lines)}", 
                            parse_mode="HTML",
                            reply_markup=reply_markup
                        )
                    except Exception as e:
                        logging.error(f"Failed to send draft preview: {e}")
                else:
                    await push_processed_response(context, chat_id, chat_id, reply_text, user_name, update.message.message_id)

        except Exception as e:
            logging.error(f"AI Engine Fault: {e}", exc_info=True)
            error_msg = "❌ <b>AI Engine Fault:</b> The AI model encountered an error."
            try:
                await context.bot.send_message(chat_id=chat_id, text=error_msg, parse_mode="HTML")
            except: pass
        return

    # 4. ADMIN RULE REMINDER
    if (chat_id == ADMIN_LOUNGE_ID or is_alpha) and update.message.text:
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

    if query.data == "close_message":
        await query.answer()
        await query.delete_message()
        return

    if query.data.startswith("relay_"):
        await query.answer()
        action, draft_id = query.data.split(":")
        if draft_id not in relay_drafts:
            await query.edit_message_text("⚠️ Draft expired or invalid.")
            return
            
        draft = relay_drafts[draft_id]
        
        if action == "relay_cancel":
            del relay_drafts[draft_id]
            await query.edit_message_text("❌ <b>Relay message cancelled.</b>", parse_mode="HTML")
            return
            
        elif action == "relay_send":
            await query.edit_message_text("🚀 <b>Transmitting response to Main Lounge...</b>", parse_mode="HTML")
            await push_processed_response(
                context, 
                draft["origin_chat"], 
                draft["target_chat"], 
                draft["reply_text"], 
                draft["user_name"], 
                None
            )
            del relay_drafts[draft_id]
            await query.edit_message_text("✅ <b>Response transmitted to Main Lounge successfully.</b>", parse_mode="HTML")
            return
            
        elif action == "relay_retry":
            await query.edit_message_text("🔄 <b>Regenerating response...</b>", parse_mode="HTML")
            
            import google.generativeai as genai
            gemini_key = os.getenv("GEMINI_API_KEY")
            genai.configure(api_key=gemini_key)
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            import html
            
            # Need to get system instruction from main chat
            # Let's just use SYSTEM_PROMPT since we know it's relaying
            model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=SYSTEM_PROMPT)
            response = await model.generate_content_async(draft["prompt_list"])
            
            reply_text = response.text.replace("[DELETE]", "").strip()
            draft["reply_text"] = reply_text
            relay_drafts[draft_id] = draft
            
            preview_lines = reply_text[:3000]
            keyboard = [
                [InlineKeyboardButton("🚀 Send", callback_data=f"relay_send:{draft_id}"),
                 InlineKeyboardButton("🔄 Retry", callback_data=f"relay_retry:{draft_id}")],
                [InlineKeyboardButton("❌ Cancel", callback_data=f"relay_cancel:{draft_id}")]
            ]
            await query.edit_message_text(
                f"📢 <b>Relay Draft Preview:</b>\n\n{html.escape(preview_lines)}", 
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

    if query.data == "show_menu":
        await query.answer()
        active_menu = MENU_TEXT
        if chat_id in antigravity_chats:
            active_menu = ANTIGRAVITY_MENU_TEXT
        elif chat_id in alchemy_chats:
            active_menu = ALCHEMY_MENU_TEXT
        await query.edit_message_text(active_menu, parse_mode="HTML", reply_markup=CLOSE_KEYBOARD)
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
            "👔 <b>Logic Feedback:</b>\nPlease type your comment about the logic (max 500 chars). It will be logged to GitHub.",
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
        await query.edit_message_text("🚨 <b>EMERGENCY FLARE FIRED!</b>\nAntigravity is aware. GitHub CI/CD has been alerted that Clipsflow is unresponsive.", parse_mode="HTML", reply_markup=CLOSE_KEYBOARD)
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
        await query.edit_message_text("🛑 Ticketing flow cancelled.", reply_markup=CLOSE_KEYBOARD)
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
        "Now, please provide a detailed description of the bug (max 2000 chars).",
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

