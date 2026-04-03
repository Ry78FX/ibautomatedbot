#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════╗
║         RayBot — JustMarkets IB Assistant Bot            ║
║         Built for @RRaytrade | OG Ray                    ║
╚══════════════════════════════════════════════════════════╝
"""

import os
import json
import logging
import csv
from datetime import datetime
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ─────────────────────────────────────────────────────────────────
# CONFIG — UPDATE THESE BEFORE DEPLOYING
# ─────────────────────────────────────────────────────────────────

BOT_TOKEN      = os.getenv("BOT_TOKEN",      "8644964080:AAHuIdSEjmBSObllppccc7AEkzpe1ktDnHo")
RAY_IB_LINK    = os.getenv("RAY_IB_LINK",    "https://one.justmarkets.link/a/xe17r0mut1")
RAY_EBOOK_LINK = os.getenv("RAY_EBOOK_LINK", "https://t.me/RRaytrade")
RAY_TELEGRAM   = "RRaytrade"        # Your username (no @)
CHANNEL_LINK   = "https://t.me/RRaytrade"
RAY_IB_ID      = "xe17r0mut1"      # Your JustMarkets IB Partner ID

# ── RAY'S personal Telegram chat ID ─────────────────────────────
# Get yours: message @userinfobot on Telegram, it will reply with your ID
RAY_CHAT_ID    = int(os.getenv("RAY_CHAT_ID", "0"))  # ← set this in Railway env vars

# ── Where client data is saved ──────────────────────────────────
CLIENTS_FILE   = Path("clients.json")
CLIENTS_CSV    = Path("clients.csv")

# ─────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
# CLIENT DATA STORAGE
# ─────────────────────────────────────────────────────────────────

def load_clients() -> list:
    if CLIENTS_FILE.exists():
        with open(CLIENTS_FILE, "r") as f:
            return json.load(f)
    return []


def save_client(record: dict) -> None:
    """Append a new client record to both JSON and CSV."""
    clients = load_clients()

    # Check if MT5 already exists — update if so
    for c in clients:
        if c.get("mt5_id") == record.get("mt5_id"):
            c.update(record)
            break
    else:
        clients.append(record)

    # Save JSON
    with open(CLIENTS_FILE, "w") as f:
        json.dump(clients, f, indent=2, ensure_ascii=False)

    # Save / update CSV
    fieldnames = ["timestamp", "client_name", "username", "telegram_id", "mt5_id", "type", "notes"]
    write_header = not CLIENTS_CSV.exists()
    with open(CLIENTS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerow(record)

    logger.info(f"Client saved: {record}")


# ─────────────────────────────────────────────────────────────────
# KEYBOARD BUILDERS
# ─────────────────────────────────────────────────────────────────

def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 Daftar JustMarkets", callback_data="register"),
            InlineKeyboardButton("🔄 Tukar IB ke Ray",   callback_data="change_ib"),
        ],
        [
            InlineKeyboardButton("📚 Free Ebook & Ilmu", callback_data="ebook"),
            InlineKeyboardButton("❓ FAQ Trading",        callback_data="faq"),
        ],
        [
            InlineKeyboardButton("💰 Masalah Deposit",    callback_data="deposit_help"),
            InlineKeyboardButton("💸 Masalah Withdrawal", callback_data="withdrawal_help"),
        ],
        [
            InlineKeyboardButton("🌐 Join Channel Ray", url=CHANNEL_LINK),
            InlineKeyboardButton("📞 DM Ray Terus",     url=f"https://t.me/{RAY_TELEGRAM}"),
        ],
    ])


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu")],
    ])


def back_and_contact_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📞 DM Ray Terus", url=f"https://t.me/{RAY_TELEGRAM}")],
        [InlineKeyboardButton("🏠 Menu Utama",   callback_data="main_menu")],
    ])


# ─────────────────────────────────────────────────────────────────
# /START  &  /MENU
# ─────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Clear any waiting state when user resets
    context.user_data.clear()

    user       = update.effective_user
    first_name = user.first_name if user.first_name else "Trader"

    text = (
        f"Assalamualaikum / Hey {first_name}! 👋\n\n"
        "Aku *RayBot* — assistant rasmi untuk komuniti trading *OG Ray (@RRaytrade)*.\n\n"
        "Aku boleh bantu kau dengan:\n"
        "✅ Daftar akaun JustMarkets\n"
        "✅ Tukar IB kepada Ray\n"
        "✅ Submit MT5 account number kau\n"
        "✅ Dapatkan free ebook & ilmu trading\n"
        "✅ FAQ & masalah deposit/withdrawal\n\n"
        "Tekan butang di bawah untuk mula 👇"
    )

    if update.message:
        await update.message.reply_text(
            text, reply_markup=main_menu_keyboard(), parse_mode="Markdown"
        )
    else:
        await update.callback_query.edit_message_text(
            text, reply_markup=main_menu_keyboard(), parse_mode="Markdown"
        )


# ─────────────────────────────────────────────────────────────────
# MAIN CALLBACK ROUTER
# ─────────────────────────────────────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data

    simple_routes = {
        "main_menu":       start,
        "ebook":           show_ebook,
        "faq":             show_faq,
        "deposit_help":    show_deposit_help,
        "withdrawal_help": show_withdrawal_help,
    }

    if data in simple_routes:
        await simple_routes[data](update, context)

    # ── REGISTER FLOW ──────────────────────────────────────────
    elif data == "register":
        await show_register(update, context)
    elif data == "register_verified":
        await show_new_mt5_guide(update, context, client_type="new_registration")
    elif data == "register_pending":
        await show_register_pending(update, context)

    # ── CHANGE IB FLOW ─────────────────────────────────────────
    elif data == "change_ib":
        await show_change_ib(update, context)
    elif data == "change_ib_done":
        await show_new_mt5_guide(update, context, client_type="ib_transfer")
    elif data == "change_ib_pending":
        await show_change_ib_pending(update, context)

    # ── FAQ ────────────────────────────────────────────────────
    elif data.startswith("faq_"):
        await show_faq_answer(update, data)


# ─────────────────────────────────────────────────────────────────
# SECTION: REGISTER
# ─────────────────────────────────────────────────────────────────

async def show_register(update: Update, context: ContextTypes.DEFAULT_TYPE = None) -> None:
    text = (
        "📝 *Cara Daftar Akaun JustMarkets dengan Ray sebagai IB*\n\n"
        "⚠️ *PENTING:* Kau MESTI daftar guna link Ray di bawah.\n"
        "Kalau dah ada akaun lain tanpa link ni, tekan *'Tukar IB'* di menu.\n\n"
        "*Step-by-step:*\n\n"
        "1️⃣ Tekan butang *'Daftar Sekarang'* di bawah\n"
        "2️⃣ Isi nama penuh, email & nombor telefon\n"
        "3️⃣ Verify IC (depan & belakang + selfie) — proses 1–24 jam\n"
        "4️⃣ Download MT5 dari App Store / Play Store\n"
        "5️⃣ Login MT5 dengan ID akaun dari email JustMarkets\n"
        "6️⃣ Buat deposit pertama (minimum $10, rekomen $100–$300)\n\n"
        "💡 _Mulakan dengan jumlah yang kau selesa. "
        "RM500–RM1,000 dah cukup untuk belajar dengan betul._\n\n"
        "─────────────────────────\n"
        "✅ Lepas daftar & verify IC, tekan butang bawah untuk step seterusnya."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Daftar Sekarang (Link Ray)", url=RAY_IB_LINK)],
        [InlineKeyboardButton("✅ Dah Daftar & Verify IC",     callback_data="register_verified")],
        [InlineKeyboardButton("⏳ Belum Verify Lagi",          callback_data="register_pending")],
        [InlineKeyboardButton("🏠 Menu Utama",                 callback_data="main_menu")],
    ])
    await update.callback_query.edit_message_text(
        text, reply_markup=keyboard, parse_mode="Markdown"
    )


async def show_register_pending(update: Update, context: ContextTypes.DEFAULT_TYPE = None) -> None:
    text = (
        "⏳ *Verify IC Belum Complete*\n\n"
        "Takpe! Proses verify biasanya ambil *1–24 jam* (hari bekerja).\n\n"
        "*Tips untuk lulus verify laju:*\n"
        "• 📸 Gambar IC kena jelas & tak blur — semua 4 penjuru nampak\n"
        "• 🤳 Selfie dengan IC — muka & IC kena nampak sama\n"
        "• 📄 Proof of address dalam 3 bulan (bil utiliti / penyata bank)\n"
        "• ✏️ Nama & alamat dalam dokumen kena match dengan form daftar\n\n"
        "Lepas verify IC siap, *come back sini dan tekan 'Dah Verify'* untuk step seterusnya.\n\n"
        "❓ Ada masalah dengan verify? DM Ray — dia boleh guide."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Dah Verify — Teruskan",  callback_data="register_verified")],
        [InlineKeyboardButton("📞 DM Ray untuk Bantuan",   url=f"https://t.me/{RAY_TELEGRAM}")],
        [InlineKeyboardButton("🏠 Menu Utama",             callback_data="main_menu")],
    ])
    await update.callback_query.edit_message_text(
        text, reply_markup=keyboard, parse_mode="Markdown"
    )


# ─────────────────────────────────────────────────────────────────
# SECTION: CHANGE IB
# ─────────────────────────────────────────────────────────────────

async def show_change_ib(update: Update, context: ContextTypes.DEFAULT_TYPE = None) -> None:
    text = (
        "🔄 *Cara Tukar IB ke Ray (JustMarkets)*\n\n"
        "Ada akaun JustMarkets tapi IB kau bukan Ray? Boleh request tukar.\n\n"
        "*Syarat sebelum tukar:*\n"
        "• ✅ Tiada open trade (kena close semua dulu)\n"
        "• ✅ Akaun dah verified\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "*Step-by-step:*\n\n"
        "1️⃣ Log masuk ke *portal.justmarkets.com*\n"
        "2️⃣ Pergi ke *Support → Live Chat*\n"
        "3️⃣ Copy & hantar mesej ni kepada support:\n\n"
        "```\n"
        "Hello, I would like to request an IB transfer for my account.\n"
        f"My account number is [ACCOUNT NUMBER].\n"
        f"I would like to be transferred under IB Partner ID: {RAY_IB_ID}.\n"
        "Please assist. Thank you.\n"
        "```\n\n"
        "4️⃣ Support akan proses dalam *1–3 hari bekerja*\n"
        "5️⃣ Lepas confirmed, tekan *'Dah Tukar IB'* di bawah\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📌 _Nak tahu IB Partner ID Ray?_\n"
        "DM Ray terus — dia akan bagi ID yang betul untuk kau tulis dalam request."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Dah Tukar IB — Teruskan",   callback_data="change_ib_done")],
        [InlineKeyboardButton("⏳ Belum / Masih Pending",      callback_data="change_ib_pending")],
        [InlineKeyboardButton("📞 DM Ray untuk IB ID",         url=f"https://t.me/{RAY_TELEGRAM}")],
        [InlineKeyboardButton("🌐 JustMarkets Portal",         url="https://portal.justmarkets.com")],
        [InlineKeyboardButton("🏠 Menu Utama",                 callback_data="main_menu")],
    ])
    await update.callback_query.edit_message_text(
        text, reply_markup=keyboard, parse_mode="Markdown"
    )


async def show_change_ib_pending(update: Update, context: ContextTypes.DEFAULT_TYPE = None) -> None:
    text = (
        "⏳ *IB Transfer Masih Pending*\n\n"
        "Takpe, normal! JustMarkets Support biasanya process dalam *1–3 hari bekerja*.\n\n"
        "*Kalau dah 3 hari bekerja tapi belum confirm:*\n"
        "1️⃣ Log masuk portal JustMarkets\n"
        "2️⃣ Pergi Support → check ticket status kau\n"
        "3️⃣ Kalau masih tak ada response, submit ticket baru\n"
        "4️⃣ Atau DM Ray — dia boleh follow up untuk kau\n\n"
        "⚠️ *Jangan buat trade dulu* sebelum IB transfer confirmed ya.\n\n"
        "Lepas dapat confirmation email dari JustMarkets, *come back dan tekan 'Dah Tukar IB'* untuk step seterusnya."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Dah Confirmed — Teruskan", callback_data="change_ib_done")],
        [InlineKeyboardButton("📞 DM Ray untuk Follow Up",  url=f"https://t.me/{RAY_TELEGRAM}")],
        [InlineKeyboardButton("🏠 Menu Utama",              callback_data="main_menu")],
    ])
    await update.callback_query.edit_message_text(
        text, reply_markup=keyboard, parse_mode="Markdown"
    )


# ─────────────────────────────────────────────────────────────────
# SECTION: NEW MT5 ACCOUNT GUIDE + MT5 UID COLLECTION
# ─────────────────────────────────────────────────────────────────

async def show_new_mt5_guide(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    client_type: str,
) -> None:
    """
    Called after:
    - New registration → verified ✅
    - IB transfer → confirmed ✅
    Shows how to create a NEW MT5 account and prompts for the MT5 UID.
    """
    # Set state: bot is now waiting for MT5 UID
    context.user_data["awaiting_mt5"] = True
    context.user_data["client_type"]  = client_type

    if client_type == "new_registration":
        header = "🎉 *Akaun Verified! Step Seterusnya — Create MT5 Account Baru*"
        note   = "_Kau baru je daftar guna link Ray — bagus!_"
    else:
        header = "🎉 *IB Transfer Confirmed! Step Seterusnya — Create MT5 Account Baru*"
        note   = "_Akaun kau dah di bawah Ray sekarang._"

    text = (
        f"{header}\n\n"
        f"{note}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ *PENTING — Baca Ini Dulu:*\n\n"
        "🔴 *Rebate HANYA apply untuk MT5 account yang BARU dibuka* selepas kau:\n"
        "   • Daftar guna link Ray (untuk new registration), ATAU\n"
        "   • IB transfer confirmed (untuk yang dah ada akaun)\n\n"
        "MT5 account lama yang ada sebelum ni *tidak* dapat rebate.\n"
        "Sebab tu kau kena *create account baru* sekarang. 👇\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📱 *Cara Create MT5 Account Baru:*\n\n"
        "1️⃣ Log masuk *portal.justmarkets.com*\n"
        "2️⃣ Pergi ke *Trading Accounts → Open New Account*\n"
        "3️⃣ Pilih account type: *Standard* (rekomen untuk start)\n"
        "4️⃣ Pilih leverage: *1:500* atau ikut keselesaan\n"
        "5️⃣ Click *'Create Account'*\n"
        "6️⃣ Portal akan show kau *MT5 Account Number* (contoh: 12345678)\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📩 *Lepas dapat MT5 Account Number kau:*\n\n"
        "Hantar nombor tu dekat sini (reply dalam chat ni) supaya:\n"
        "✅ Ray tahu kau dah ready\n"
        "✅ Ray boleh verify rebate kau active\n"
        "✅ Ray personally guide kau untuk trade pertama\n\n"
        "💬 *Hantar MT5 Account Number kau sekarang:*"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Buka JustMarkets Portal", url="https://portal.justmarkets.com")],
        [InlineKeyboardButton("📞 DM Ray Terus",            url=f"https://t.me/{RAY_TELEGRAM}")],
        [InlineKeyboardButton("🏠 Menu Utama",              callback_data="main_menu")],
    ])
    await update.callback_query.edit_message_text(
        text, reply_markup=keyboard, parse_mode="Markdown"
    )


async def handle_mt5_submission(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process MT5 UID sent by user, save it and forward to Ray."""
    user        = update.effective_user
    mt5_raw     = update.message.text.strip()
    client_type = context.user_data.get("client_type", "unknown")

    # Basic validation — MT5 IDs are typically 7–10 digit numbers
    if not mt5_raw.replace(" ", "").isdigit() or not (5 <= len(mt5_raw.replace(" ", "")) <= 12):
        await update.message.reply_text(
            "⚠️ Hmm, tu nampak macam bukan MT5 account number.\n\n"
            "MT5 account number biasanya 7–10 digit nombor sahaja.\n"
            "Contoh: `12345678`\n\n"
            "Boleh check balik dalam portal JustMarkets kau dan hantar semula?",
            parse_mode="Markdown"
        )
        return

    mt5_id = mt5_raw.replace(" ", "")

    # ── Build record ────────────────────────────────────────────
    now    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    uname  = f"@{user.username}" if user.username else "no username"
    fname  = user.first_name or "Unknown"
    lname  = user.last_name  or ""
    fullname = f"{fname} {lname}".strip()
    tg_id  = user.id

    type_label = "New Registration" if client_type == "new_registration" else "IB Transfer"

    record = {
        "timestamp":   now,
        "client_name": fullname,
        "username":    uname,
        "telegram_id": tg_id,
        "mt5_id":      mt5_id,
        "type":        type_label,
        "notes":       "",
    }

    # ── Save to file ─────────────────────────────────────────────
    save_client(record)

    # ── Forward to Ray ───────────────────────────────────────────
    if RAY_CHAT_ID and RAY_CHAT_ID != 0:
        ray_msg = (
            f"🆕 *CLIENT BARU SUBMIT MT5 UID*\n\n"
            f"👤 *Nama:* {fullname}\n"
            f"📱 *Telegram:* {uname} (ID: `{tg_id}`)\n"
            f"📊 *MT5 Account:* `{mt5_id}`\n"
            f"🏷️ *Jenis:* {type_label}\n"
            f"🕐 *Masa:* {now}\n\n"
            f"➡️ Reply /clients untuk tengok semua client list."
        )
        try:
            await context.bot.send_message(
                chat_id=RAY_CHAT_ID,
                text=ray_msg,
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(f"Could not forward to Ray: {e}")

    # ── Clear state ───────────────────────────────────────────────
    context.user_data.pop("awaiting_mt5",  None)
    context.user_data.pop("client_type",   None)

    # ── Confirm to user ───────────────────────────────────────────
    confirm_text = (
        f"✅ *MT5 Account Number Dah Received!*\n\n"
        f"📊 MT5 ID kau: `{mt5_id}`\n\n"
        "Ray dah dapat notification dan akan verify rebate kau *active* dalam masa terdekat.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎯 *Step Seterusnya:*\n\n"
        "1️⃣ Buat deposit ke MT5 account baru kau\n"
        "2️⃣ DM Ray — dia akan guide kau untuk *trade pertama*\n"
        "3️⃣ Join channel Ray untuk daily analysis & education\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💰 *Ingat:* Rebate kau akan dikira automatically setiap kali kau trade.\n"
        "Tak perlu buat apa-apa — duit masuk sendiri. 🔥\n\n"
        "_Welcome to Ray's trading family!_ 🤝"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel Ray",    url=CHANNEL_LINK)],
        [InlineKeyboardButton("📞 DM Ray Terus",        url=f"https://t.me/{RAY_TELEGRAM}")],
        [InlineKeyboardButton("🏠 Menu Utama",          callback_data="main_menu")],
    ])
    await update.message.reply_text(
        confirm_text, reply_markup=keyboard, parse_mode="Markdown"
    )


# ─────────────────────────────────────────────────────────────────
# /CLIENTS — Ray can DM the bot to see all saved clients
# ─────────────────────────────────────────────────────────────────

async def show_clients(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Only accessible by Ray (RAY_CHAT_ID)."""
    if update.effective_user.id != RAY_CHAT_ID:
        return  # Silently ignore

    clients = load_clients()
    if not clients:
        await update.message.reply_text("📋 Belum ada client lagi.")
        return

    lines = [f"📋 *Client List — {len(clients)} orang*\n"]
    for i, c in enumerate(clients, 1):
        uname = c.get("username", "–")
        name  = c.get("client_name", "–")
        mt5   = c.get("mt5_id", "–")
        ctype = c.get("type", "–")
        ts    = c.get("timestamp", "–")
        lines.append(
            f"{i}. *{name}* | {uname}\n"
            f"   MT5: `{mt5}` | {ctype}\n"
            f"   📅 {ts}\n"
        )

    # Telegram has 4096 char limit — split if needed
    full = "\n".join(lines)
    if len(full) > 4000:
        chunks = [full[i:i+4000] for i in range(0, len(full), 4000)]
        for chunk in chunks:
            await update.message.reply_text(chunk, parse_mode="Markdown")
    else:
        await update.message.reply_text(full, parse_mode="Markdown")


# ─────────────────────────────────────────────────────────────────
# SECTION: EBOOK / EDUCATION
# ─────────────────────────────────────────────────────────────────

async def show_ebook(update: Update, context: ContextTypes.DEFAULT_TYPE = None) -> None:
    text = (
        "📚 *Free Education & Ebook dari Ray*\n\n"
        "Ray percaya — _trader yang belajar betul akan survive lama dalam game ni._\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📖 *Apa yang ada dalam Free Ebook:*\n"
        "• Asas Full Margin Trading\n"
        "• Risk Management yang sebenar\n"
        "• Psychology trader yang profitable\n"
        "• 10 kesilapan trader baru (dan cara elak)\n"
        "• Macam mana Ray bina income dari IB\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📊 *Apa yang Ray share setiap hari di channel:*\n"
        "• Morning market bias & key levels\n"
        "• Live trade breakdown (win & loss)\n"
        "• Weekly concept education\n"
        "• Member journey & milestone\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎓 *Topik popular:*\n"
        "• Full Margin vs Hedging\n"
        "• Cara baca confluence\n"
        "• Entry & exit strategy\n"
        "• Kenapa 90% trader forex Malaysia rugi\n\n"
        "Semua ni *percuma*. Ray tak jual signal — dia ajar kau jadi trader sendiri. 💪"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 Claim Free Ebook",  url=RAY_EBOOK_LINK)],
        [InlineKeyboardButton("📢 Join Channel Ray",  url=CHANNEL_LINK)],
        [InlineKeyboardButton("🏠 Menu Utama",        callback_data="main_menu")],
    ])
    await update.callback_query.edit_message_text(
        text, reply_markup=keyboard, parse_mode="Markdown"
    )


# ─────────────────────────────────────────────────────────────────
# SECTION: FAQ
# ─────────────────────────────────────────────────────────────────

async def show_faq(update: Update, context: ContextTypes.DEFAULT_TYPE = None) -> None:
    text = "❓ *FAQ — Soalan Lazim*\n\nPilih soalan yang kau nak tahu 👇"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Minimum deposit berapa?",       callback_data="faq_min_deposit")],
        [InlineKeyboardButton("📱 Cara download & setup MT5?",    callback_data="faq_mt5")],
        [InlineKeyboardButton("⏱️ Berapa lama proses verify IC?", callback_data="faq_verify")],
        [InlineKeyboardButton("💸 Cara buat withdrawal?",         callback_data="faq_how_withdraw")],
        [InlineKeyboardButton("🔄 Boleh ada lebih 1 akaun?",      callback_data="faq_multi_acc")],
        [InlineKeyboardButton("📊 Apa itu lot & rebate?",         callback_data="faq_lot_rebate")],
        [InlineKeyboardButton("🏠 Menu Utama",                    callback_data="main_menu")],
    ])
    await update.callback_query.edit_message_text(
        text, reply_markup=keyboard, parse_mode="Markdown"
    )


FAQ_ANSWERS = {
    "faq_min_deposit": (
        "💰 *Minimum Deposit JustMarkets*\n\n"
        "Minimum deposit adalah *$10 USD* (lebih kurang RM47).\n\n"
        "Ray rekomen start dengan *$100–$300* (RM470–RM1,400).\n"
        "Dengan modal tu, kau ada cukup margin untuk trade dengan betul dan belajar risk management tanpa risiko margin call cepat.\n\n"
        "🧠 _Ingat: Bukan pasal berapa besar modal, tapi pasal betapa betulnya kau manage risk._"
    ),
    "faq_mt5": (
        "📱 *Cara Download & Setup MetaTrader 5 (MT5)*\n\n"
        "*Download:*\n"
        "• iOS: App Store → cari _'MetaTrader 5'_\n"
        "• Android: Play Store → cari _'MetaTrader 5'_\n"
        "• PC/Mac: mt5.com → Download\n\n"
        "*Setup:*\n"
        "1️⃣ Buka app MT5\n"
        "2️⃣ Tap _'Log in to an existing account'_\n"
        "3️⃣ Search server: ketik *'JustMarkets'*\n"
        "4️⃣ Masukkan Login ID & password dari email JustMarkets\n"
        "5️⃣ Tap Connect — done! ✅\n\n"
        "❓ Stuck mana-mana step? DM Ray — dia akan guide kau."
    ),
    "faq_verify": (
        "⏱️ *Proses Verify Akaun JustMarkets*\n\n"
        "Masa biasa: *1–24 jam* (hari bekerja)\n\n"
        "*Dokumen yang diperlukan:*\n"
        "✅ IC atau passport (depan & belakang, jelas, tak blur)\n"
        "✅ Selfie dengan IC di tangan (muka & IC kena nampak)\n"
        "✅ Proof of address dalam 3 bulan (bil utiliti / penyata bank)\n\n"
        "*Tips untuk lulus laju:*\n"
        "• Gambar IC tak kabur, ada pencahayaan yang cukup\n"
        "• Nama & alamat dalam dokumen kena match dengan form daftar\n"
        "• Semua 4 penjuru IC kena nampak dalam gambar\n\n"
        "Kalau verify lambat lebih 24 jam, contact JustMarkets Support terus."
    ),
    "faq_how_withdraw": (
        "💸 *Cara Withdrawal dari JustMarkets*\n\n"
        "1️⃣ Log masuk *portal.justmarkets.com*\n"
        "2️⃣ Pergi ke *Finance → Withdrawal*\n"
        "3️⃣ Pilih method (Bank Transfer / e-Wallet / Crypto)\n"
        "4️⃣ Masukkan jumlah & butiran bank/wallet\n"
        "5️⃣ Submit & tunggu confirmation\n\n"
        "*Masa processing:*\n"
        "• E-wallet / Crypto: 1–24 jam\n"
        "• Bank transfer: 1–3 hari bekerja\n\n"
        "⚠️ _Withdrawal method kena sama dengan deposit method pertama kau._\n\n"
        "Ada masalah? Pergi ke menu *Masalah Withdrawal* untuk penyelesaian lanjut."
    ),
    "faq_multi_acc": (
        "🔄 *Boleh Ada Lebih Dari 1 Akaun?*\n\n"
        "✅ *Ya, boleh!* JustMarkets benarkan multiple trading accounts.\n\n"
        "*Jenis akaun yang tersedia:*\n"
        "• Standard — spread-based, sesuai untuk trader baru\n"
        "• Pro — tighter spread + commission, untuk trader experienced\n"
        "• Cent — trade dengan amount sangat kecil, sesuai untuk practice\n\n"
        "💡 Semua account tetap di bawah IB Ray selagi kau daftar guna link dia.\n\n"
        "⚠️ *Ingat:* Rebate hanya apply untuk *MT5 account yang baru dibuka* selepas daftar atau IB transfer confirmed."
    ),
    "faq_lot_rebate": (
        "📊 *Apa Itu Lot & Rebate?*\n\n"
        "*Lot* = unit size untuk trade forex.\n"
        "• 1 Standard Lot = 100,000 unit base currency\n"
        "• 0.1 Lot = 10,000 unit (mini lot)\n"
        "• 0.01 Lot = 1,000 unit (micro lot)\n\n"
        "*Rebate* = komisyen yang Ray dapat sebagai IB setiap kali client dia trade.\n\n"
        "*Macam mana kau untung dari rebate:*\n"
        "Rebate ni bukan kau yang dapat terus — tapi sebab Ray ada incentive dari kau, dia lebih motivated untuk pastikan kau berjaya dalam trading.\n\n"
        "Ray fokus ajar kau trade dengan betul — more active trading = more income Ray = Ray lagi dedicated untuk support kau.\n\n"
        "💡 _Win-win untuk dua-dua pihak._"
    ),
}


async def show_faq_answer(update: Update, data: str) -> None:
    text = FAQ_ANSWERS.get(data, "Maklumat tidak tersedia. Sila hubungi Ray terus.")
    await update.callback_query.edit_message_text(
        text, reply_markup=back_and_contact_keyboard(), parse_mode="Markdown"
    )


# ─────────────────────────────────────────────────────────────────
# SECTION: DEPOSIT HELP
# ─────────────────────────────────────────────────────────────────

async def show_deposit_help(update: Update, context: ContextTypes.DEFAULT_TYPE = None) -> None:
    text = (
        "💰 *Masalah Deposit JustMarkets — Penyelesaian*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "❌ *Deposit Pending Lama*\n"
        "• Normal: 1–24 jam. Weekend mungkin lambat sikit.\n"
        "• Semak status: *Finance → Transaction History*\n"
        "• Dah 24 jam? Submit support ticket dengan bukti bayaran.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "❌ *Deposit Declined / Rejected*\n"
        "• Pastikan nama dalam bank sama dengan nama akaun JustMarkets\n"
        "• Cuba method lain: FPX, e-wallet, atau USDT crypto\n"
        "• Akaun kena verified dulu sebelum boleh deposit\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "❌ *Dah Transfer Tapi Balance Tak Masuk*\n"
        "• Simpan screenshot / receipt transfer kau\n"
        "• Hantar ke support dengan: Account ID, Jumlah, Tarikh, Screenshot\n"
        "• Support: support@justmarkets.com atau Live Chat\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "❌ *Tak Tau Cara Deposit (Malaysia)*\n"
        "Method deposit yang tersedia:\n"
        "✅ FPX / Online Banking (Maybank, CIMB, RHB, dll)\n"
        "✅ TNG eWallet / GrabPay / ShopeePay\n"
        "✅ USDT (TRC20) — paling laju, recommend!\n"
        "✅ Kad Kredit/Debit Visa/Mastercard\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Masalah lain? DM Ray — dia boleh escalate untuk kau. 👇"
    )
    await update.callback_query.edit_message_text(
        text, reply_markup=back_and_contact_keyboard(), parse_mode="Markdown"
    )


# ─────────────────────────────────────────────────────────────────
# SECTION: WITHDRAWAL HELP
# ─────────────────────────────────────────────────────────────────

async def show_withdrawal_help(update: Update, context: ContextTypes.DEFAULT_TYPE = None) -> None:
    text = (
        "💸 *Masalah Withdrawal JustMarkets — Penyelesaian*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "❌ *Withdrawal Pending Lama*\n"
        "• Processing time normal: 1–3 hari bekerja\n"
        "• Weekend atau public holiday mungkin delayed\n"
        "• Check status: *Finance → Transaction History*\n"
        "• Kalau 3 hari bekerja dah lepas, contact support\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "❌ *Withdrawal Rejected*\n"
        "Sebab paling biasa:\n"
        "• Method tidak match dengan deposit method pertama\n"
        "• Bank details salah (semak nombor akaun & nama)\n"
        "• Account belum fully verified\n"
        "• Ada bonus yang belum memenuhi syarat withdrawal\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "❌ *Tak Boleh Withdraw — Error Message*\n"
        "• Pastikan KYC (verify IC) dah complete\n"
        "• Minimum withdrawal biasanya $10\n"
        "• Kalau ada bonus, check T&C bonus dulu\n"
        "• Free margin kena cukup (close some trades kalau perlu)\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "❌ *Wang Masuk Tapi Jumlah Tidak Betul*\n"
        "• Ada processing fee dari payment provider (normal)\n"
        "• Check breakdown di transaction history\n"
        "• Kalau ada discrepancy besar, screenshot dan report ke support\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📞 *JustMarkets Support:*\n"
        "• Live Chat: justmarkets.com\n"
        "• Email: support@justmarkets.com\n"
        "• Telegram: @JustMarketsSupport\n\n"
        "Masalah specific tak selesai? DM Ray — dia boleh escalate untuk kau. 👇"
    )
    await update.callback_query.edit_message_text(
        text, reply_markup=back_and_contact_keyboard(), parse_mode="Markdown"
    )


# ─────────────────────────────────────────────────────────────────
# FALLBACK MESSAGE HANDLER
# ─────────────────────────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route text messages — either collect MT5 UID or show main menu."""

    # If bot is waiting for MT5 UID from this user
    if context.user_data.get("awaiting_mt5"):
        await handle_mt5_submission(update, context)
        return

    # Default: show main menu
    text = (
        "Hey! Guna butang di bawah untuk pilih apa yang kau perlukan 👇\n\n"
        "_Kalau ada soalan yang tak ada dalam senarai, DM Ray terus di @RRaytrade 😊_"
    )
    await update.message.reply_text(
        text, reply_markup=main_menu_keyboard(), parse_mode="Markdown"
    )


# ─────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────────

def main() -> None:
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        raise ValueError(
            "⛔  BOT_TOKEN not set! "
            "Set it as environment variable: export BOT_TOKEN=your_token_here"
        )

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",   start))
    app.add_handler(CommandHandler("menu",    start))
    app.add_handler(CommandHandler("clients", show_clients))   # Ray only
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🤖 RayBot is live and polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
