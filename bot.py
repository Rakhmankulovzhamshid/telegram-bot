import random
import requests
import os
import json
from urllib.parse import quote_plus

from geopy.geocoders import Nominatim

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto

# ---------------- CONFIG ----------------

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 8687088054
ADMIN_USERNAME = "Orderly1"

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

geolocator = Nominatim(user_agent="service_bot_v2", timeout=5)

orders_users = {}

MENU_BUTTONS = ["🏠 Accommodation", "🚕 Taxi", "🍽 Food", "🔙 Back", "💬 Support"]

CANCEL_TEXT = "❌ Cancel"

# ---------------- MENU ----------------

def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🏠 Accommodation")
    kb.add("🚕 Taxi")
    kb.add("🍽 Food")
    kb.add("💬 Support")
    return kb

# ---------------- STATES ----------------

class TaxiOrder(StatesGroup):
    from_location = State()
    to_location = State()

# ---------------- HOUSING JSON ----------------

def load_houses():
    try:
        with open("houses.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

# ---------------- HOUSING VIEW ----------------

async def send_housing(message, index=0):

    houses = load_houses()

    if not houses:
        await message.answer("❌ No housing available")
        return

    if index < 0 or index >= len(houses):
        return

    item = houses[index]
    photos = item.get("photos", [])

    media = []

    for i, photo in enumerate(photos):
        try:
            if i == 0:
                media.append(InputMediaPhoto(
                    media=open(photo, "rb"),
                    caption=f"""🏠 {item['title']}

{item['description']}

💰 {item['price']}"""
                ))
            else:
                media.append(InputMediaPhoto(media=open(photo, "rb")))
        except:
            continue

    if media:
        await bot.send_media_group(message.chat.id, media=media)

    kb = InlineKeyboardMarkup(row_width=2)

    if index > 0:
        kb.insert(InlineKeyboardButton("⬅️ Prev", callback_data=f"house_{index-1}"))

    if index < len(houses) - 1:
        kb.insert(InlineKeyboardButton("Next ➡️", callback_data=f"house_{index+1}"))

    kb.add(
        InlineKeyboardButton(
            "🗺 Map",
            url=f"https://www.google.com/maps/search/?api=1&query={quote_plus(item['address'])}"
        ),
        InlineKeyboardButton("💬 Contact Admin", url=f"https://t.me/{ADMIN_USERNAME}")
    )

    await message.answer("👇 Contact for booking:", reply_markup=kb)

# ---------------- CANCEL ----------------

@dp.message_handler(lambda m: m.text == CANCEL_TEXT, state="*")
async def cancel_any_state(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("❌ Cancelled", reply_markup=main_menu())

# ---------------- TAXI ----------------

def is_menu(text: str):
    return text in MENU_BUTTONS

def safe_geocode(query):
    try:
        return geolocator.geocode(query)
    except:
        return None

def calculate_distance(coord1, coord2):
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{coord1[1]},{coord1[0]};{coord2[1]},{coord2[0]}?overview=false"
        r = requests.get(url, timeout=5)
        data = r.json()
        if data.get("routes"):
            return data["routes"][0]["distance"] / 1000
    except:
        pass
    return 1.0

# ---------------- START ----------------

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Welcome 👋", reply_markup=main_menu())

# ---------------- HOUSING ----------------

@dp.message_handler(lambda m: m.text == "🏠 Accommodation")
async def housing(message: types.Message):
    await send_housing(message, 0)

@dp.callback_query_handler(lambda c: c.data.startswith("house_"))
async def switch_house(callback: types.CallbackQuery):
    index = int(callback.data.split("_")[1])
    await callback.answer()
    await send_housing(callback.message, index)

# ---------------- TAXI ----------------

@dp.message_handler(lambda m: m.text == "🚕 Taxi")
async def taxi_start(message: types.Message):

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(CANCEL_TEXT)

    await message.answer("""🚕 Цены в боте — это тарифы городского такси.  
Мы предоставляем поездки на 20% дешевле этих цен.

Enter pickup location:""", reply_markup=kb)

    await TaxiOrder.from_location.set()

@dp.message_handler(state=TaxiOrder.from_location)
async def taxi_from(message: types.Message, state: FSMContext):

    if message.text == CANCEL_TEXT:
        await state.finish()
        return await message.answer("❌ Cancelled", reply_markup=main_menu())

    if is_menu(message.text):
        return await message.answer("❗ Enter real pickup address.")

    loc = safe_geocode(message.text)

    if not loc:
        return await message.answer("❌ Address not found.")

    await state.update_data(from_coords=(loc.latitude, loc.longitude), from_text=message.text)

    await message.answer("📍 Enter destination:")
    await TaxiOrder.to_location.set()

@dp.message_handler(state=TaxiOrder.to_location)
async def taxi_to(message: types.Message, state: FSMContext):

    if message.text == CANCEL_TEXT:
        await state.finish()
        return await message.answer("❌ Cancelled", reply_markup=main_menu())

    if is_menu(message.text):
        return await message.answer("❗ Enter real destination.")

    loc = safe_geocode(message.text)

    if not loc:
        return await message.answer("❌ Destination not found.")

    data = await state.get_data()

    from_coords = data["from_coords"]
    from_text = data["from_text"]

    to_coords = (loc.latitude, loc.longitude)
    to_text = message.text

    distance = calculate_distance(from_coords, to_coords)
    price = round(3 + distance * 1.8, 2)

    maps = f"https://www.google.com/maps/dir/{quote_plus(from_text)}/{quote_plus(to_text)}"

    order_id = random.randint(1000, 9999)
    orders_users[order_id] = message.from_user.id

    user = message.from_user

    text = (
        f"🚕 ORDER #{order_id}\n\n"
        f"👤 Client: {user.full_name}\n"
        f"📛 Username: @{user.username if user.username else 'no_username'}\n"
        f"🆔 ID: {user.id}\n\n"
        f"📍 From: {from_text}\n"
        f"📍 To: {to_text}\n\n"
        f"📏 Distance: {distance:.2f} km\n"
        f"💰 Price: €{price}\n\n"
        f"🗺 Route:\n{maps}"
    )

    await message.answer(
        text,
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("💬 Contact Admin", url=f"https://t.me/{ADMIN_USERNAME}")
        )
    )

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ Accept", callback_data=f"accept_{order_id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"reject_{order_id}")
    )

    await bot.send_message(ADMIN_ID, text, reply_markup=kb)

    await state.finish()

# ---------------- ADMIN ----------------

@dp.callback_query_handler(lambda c: c.data.startswith("accept_") or c.data.startswith("reject_"))
async def admin(callback: types.CallbackQuery):

    action, oid = callback.data.split("_")
    oid = int(oid)

    user_id = orders_users.get(oid)

    msg = "Accepted 👍" if action == "accept" else "Rejected ❌"

    if user_id:
        await bot.send_message(user_id, msg)

    await callback.answer("Done")

# ---------------- FOOD ----------------
@dp.message_handler(lambda m: m.text == "🍽 Food")
async def food_menu(message: types.Message):

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🥟 Khinkali")
    kb.add("🔙 Back")

    await message.answer(
        "🍽 Choose Georgian dish / Выберите блюдо:",
        reply_markup=kb
    )

@dp.message_handler(lambda m: m.text == "🥟 Khinkali")
async def khinkali(message: types.Message):

    caption = (
        "🥟 Khinkali\n\n"

        " Домашние вкусные, большие сочные хинкали из говядины 😋\n\n"
        "Такую вкуснятину вы ещё не пробовали.\n\n"

        "💶 1 шт — 1€\n"
        "📦 Минимальный заказ: 20 шт\n\n"

        "🚚 Доставка в районы:\n"
        "Municipio XI, XII, XIII — 8€"
    )

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton(
            "🛒 Order / Заказать",
            url=f"https://t.me/{ADMIN_USERNAME}"
        )
    )

    try:
        with open("photos/khinkali.jpg", "rb") as photo:
            await message.answer_photo(
                photo=photo,
                caption=caption,
                reply_markup=kb
            )
    except:
        await message.answer(caption, reply_markup=kb)

# ---------------- SUPPORT ----------------

@dp.message_handler(lambda m: m.text == "💬 Support")
async def support(message: types.Message):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💬 Chat with Admin", url=f"https://t.me/{ADMIN_USERNAME}"))
    await message.answer("Contact support 👇", reply_markup=kb)

# ---------------- BACK ----------------

@dp.message_handler(lambda m: m.text == "🔙 Back")
async def back(message: types.Message):
    await message.answer("Main menu 👇", reply_markup=main_menu())

# ---------------- RUN ----------------

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
