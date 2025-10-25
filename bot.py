#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import random
import logging
import json
from typing import Dict, Any, List
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.constants import ChatAction

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === CONFIG ===
BOT_TOKEN = "8117675754:AAE6AvPtqJrcSobYXGNbrMbX5fUyOQfRWBk"
IMAGES_DIR = "images"
CHANNEL_LINK = "https://t.me/borustar"

# === STATE ===
LAST_IMAGE: Dict[int, Dict[str, Any]] = {}
LAST_STICKER_SENT: Dict[int, str] = {}
ADD_MODE: Dict[int, bool] = {}

# === STICKER CATEGORY MAP ===
STICKER_CATEGORIES = {
    "zero_two": "Zero Two 🌸",
    "hiro": "Hiro 👑",
    "general": "Umumiy sticker"
}

# === FILE UTILS ===
def load_stickers() -> List[str]:
    try:
        with open("saved_stickers.json", "r") as f:
            return json.load(f)
    except Exception:
        return []

def save_stickers(stickers: List[str]) -> None:
    with open("saved_stickers.json", "w") as f:
        json.dump(stickers, f)

def load_stickers_by_category(category: str) -> List[str]:
    filename = f"stickers_{category}.json"
    try:
        if os.path.exists(filename):
            with open(filename, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return []

def save_stickers_by_category(category: str, stickers: List[str]) -> None:
    filename = f"stickers_{category}.json"
    with open(filename, "w") as f:
        json.dump(stickers, f)

# === MENU HELPERS ===
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🖼 Rasm", callback_data="menu_img")],
        [InlineKeyboardButton("🏷 Stickerlar", callback_data="menu_stickers")],
        [InlineKeyboardButton("🎬 Video", callback_data="menu_video")]
    ])

def image_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Zero Two 🌸", callback_data="img_02")],
        [InlineKeyboardButton("Hiro 👑", callback_data="img_hiro")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")]
    ])

def sticker_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Zero Two 🌸", callback_data="stickers_zero_two")],
        [InlineKeyboardButton("Hiro 👑", callback_data="stickers_hiro")],
        [InlineKeyboardButton("Umumiy 🏷", callback_data="stickers_general")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_main")]
    ])

# === COMMAND HANDLERS ===
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 Salom! Men Starlizia botman.\n\n"
        "📁 Buyruqlar:\n"
        "/img <papka> — rasm yuboradi (02, hiro)\n"
        "/stickers — saqlangan stickerlardan tasodifiy\n"
        "/addstick — sticker qo‘shish\n"
        "/video — video havola"
    )
    await update.message.reply_text(text, reply_markup=main_menu())

async def img_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("📸 Papkani tanlang:", reply_markup=image_menu())
        return
    await send_random_image(update.message, args[0])

async def video_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🎬 Videolarni shu yerdan topasiz:\n{CHANNEL_LINK}")

async def addstick_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("Zero Two 🌸", callback_data="add_sticker_zero_two")],
        [InlineKeyboardButton("Hiro 👑", callback_data="add_sticker_hiro")],
        [InlineKeyboardButton("Umumiy 🏷", callback_data="add_sticker_general")]
    ]
    await update.message.reply_text("Qaysi kategoriyaga sticker qo‘shasiz?", reply_markup=InlineKeyboardMarkup(kb))

async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in ADD_MODE:
        del ADD_MODE[chat_id]
        await update.message.reply_text("❌ Sticker qo‘shish bekor qilindi.")
    else:
        await update.message.reply_text("Faol jarayon yo‘q.")

async def stickers_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏷 Sticker to‘plamini tanlang:", reply_markup=sticker_menu())

# === MESSAGE HANDLERS ===
async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in ADD_MODE:
        return

    category = context.user_data.get("sticker_category", "general")
    sticker_id = update.message.sticker.file_id

    stickers = load_stickers()
    if sticker_id not in stickers:
        stickers.append(sticker_id)
        save_stickers(stickers)

    cat_stickers = load_stickers_by_category(category)
    if sticker_id not in cat_stickers:
        cat_stickers.append(sticker_id)
        save_stickers_by_category(category, cat_stickers)
        await update.message.reply_text(f"✅ Sticker {STICKER_CATEGORIES.get(category)} kategoriyasiga saqlandi!")
    else:
        await update.message.reply_text("Bu sticker allaqachon saqlangan.")
    del ADD_MODE[chat_id]

# === IMAGE HANDLER ===
async def send_random_image(message, folder):
    chat_id = message.chat_id
    folder_path = os.path.join(IMAGES_DIR, folder)

    if not os.path.isdir(folder_path):
        await message.reply_text(f"❌ Papka topilmadi: {folder}")
        return

    files = [f for f in os.listdir(folder_path) if f.endswith((".jpg", ".png", ".webp"))]
    if not files:
        await message.reply_text(f"{folder} papkasida rasm yo‘q.")
        return

    last = LAST_IMAGE.get(chat_id, {}).get("file_path")
    available = [f for f in files if os.path.join(folder_path, f) != last] or files

    chosen = random.choice(available)
    file_path = os.path.join(folder_path, chosen)
    kb = [
        [InlineKeyboardButton("🔄 Yana rasm", callback_data=f"img_{folder}")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="menu_img")]
    ]
    try:
        with open(file_path, "rb") as img:
            await message.reply_photo(photo=img, caption=f"{folder} 🎨", reply_markup=InlineKeyboardMarkup(kb))
        LAST_IMAGE[chat_id] = {"file_path": file_path}
    except Exception as e:
        logger.error(e)
        await message.reply_text("⚠️ Xatolik yuz berdi.")

# === CALLBACK HANDLER ===
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back_to_main":
        await query.message.edit_text("🏠 Bosh menyu:", reply_markup=main_menu())

    elif data == "menu_img":
        await query.message.edit_text("📸 Papkani tanlang:", reply_markup=image_menu())

    elif data == "menu_stickers":
        await query.message.edit_text("🏷 Sticker kategoriyasini tanlang:", reply_markup=sticker_menu())

    elif data == "menu_video":
        await query.message.edit_text(f"🎬 Videolarni shu yerdan topasiz:\n{CHANNEL_LINK}", reply_markup=main_menu())

    elif data.startswith("img_"):
        folder = data.split("_")[1]
        await send_random_image(query.message, folder)

    elif data.startswith("stickers_"):
        category = data.split("_", 1)[1]
        stickers = load_stickers_by_category(category)
        if not stickers:
            await query.message.reply_text(f"{category} kategoriyasida sticker yo‘q.")
            return
        last = LAST_STICKER_SENT.get(query.message.chat_id)
        choices = [s for s in stickers if s != last] or stickers
        sticker_id = random.choice(choices)
        await context.bot.send_sticker(query.message.chat_id, sticker=sticker_id)
        LAST_STICKER_SENT[query.message.chat_id] = sticker_id

    elif data.startswith("add_sticker_"):
        category = data.split("_", 2)[2]
        chat_id = query.from_user.id
        ADD_MODE[chat_id] = True
        context.user_data["sticker_category"] = category
        await query.message.reply_text(
            f"🩵 Endi menga {STICKER_CATEGORIES.get(category)} stickerini yuboring.\n/cancel — bekor qilish."
        )

# === NEW MEMBER HANDLER ===
async def new_members_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            await update.message.reply_text("👋 Bot qo‘shildi! Menga media yuborish huquqini bering.")
            continue
        gif_url = "https://i.pinimg.com/originals/c0/61/08/c0610813dadc87d80dffedf6bf68641a.gif"
        await context.bot.send_animation(
            chat_id=update.effective_chat.id,
            animation=gif_url,
            caption=f"🎉 Xush kelibsiz, {member.mention_html()}!",
            parse_mode="HTML"
        )

# === MAIN ===
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("img", img_cmd))
    app.add_handler(CommandHandler("addstick", addstick_cmd))
    app.add_handler(CommandHandler("cancel", cancel_cmd))
    app.add_handler(CommandHandler("stickers", stickers_cmd))
    app.add_handler(CommandHandler("video", video_cmd))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_members_handler))
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
