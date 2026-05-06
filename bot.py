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

MENU_BUTTONS = ["🏠 Accommodation", "🚕 Taxi", "🍽 Food", "💆 Beauty & Health Services", "🔙 Back", "💬 Support"]

CANCEL_TEXT = "❌ Cancel"

# ---------------- MENU ----------------

def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🏠 Accommodation")
    kb.add("🚕 Taxi")
    kb.add("🍽 Food")
    kb.add("💆 Beauty & Health Services")
    kb.add("💬 Support")
    return kb

# ---------------- STATES ----------------

class TaxiOrder(StatesGroup):
    from_location = State()
    to_location = State()

# ---------------- HOUSING ----------------

def load_houses():
    try:
        with open("houses.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

# ---------------- START ----------------

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Welcome 👋", reply_markup=main_menu())

# ---------------- BEAUTY & HEALTH ----------------

@dp.message_handler(lambda m: m.text == "💆 Beauty & Health Services")
async def beauty_services(message: types.Message):

    await message.answer(
        "💆 Beauty & Health Services\n\n"
        "🇬🇧 Coming soon...\n"
        "🇷🇺 Скоро будет добавлено...",
        reply_markup=main_menu()
    )

# ---------------- BACK ----------------

@dp.message_handler(lambda m: m.text == "🔙 Back")
async def back(message: types.Message):
    await message.answer("Main menu 👇", reply_markup=main_menu())

# ---------------- SUPPORT ----------------

@dp.message_handler(lambda m: m.text == "💬 Support")
async def support(message: types.Message):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💬 Chat with Admin", url=f"https://t.me/{ADMIN_USERNAME}"))
    await message.answer("Contact support 👇", reply_markup=kb)

# ---------------- FOOD ----------------

@dp.message_handler(lambda m: m.text == "🍽 Food")
async def food(message: types.Message):

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🥟 Khinkali")
    kb.add("🔙 Back")

    await message.answer("🍽 Choose dish:", reply_markup=kb)

@dp.message_handler(lambda m: m.text == "🥟 Khinkali")
async def khinkali(message: types.Message):

    caption = (
        "🥟 Khinkali\n\n"
        "🇬🇧 Delicious Georgian khinkali 😋\n"
        "🇷🇺 Вкусные грузинские хинкали 😋"
    )

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🛒 Order", url=f"https://t.me/{ADMIN_USERNAME}"))

    await message.answer(caption, reply_markup=kb)

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

@dp.message_handler(lambda m: m.text == "🚕 Taxi")
async def taxi_start(message: types.Message):

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(CANCEL_TEXT)

    await message.answer("""🚕 Taxi service

We offer rides 20% cheaper than city taxi prices.

Enter pickup location:""", reply_markup=kb)

    await TaxiOrder.from_location.set()

# ---------------- CANCEL ----------------

@dp.message_handler(lambda m: m.text == CANCEL_TEXT, state="*")
async def cancel(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Cancelled ❌", reply_markup=main_menu())

# ---------------- FALLBACK ----------------

@dp.message_handler()
async def fallback(message: types.Message):
    await message.answer("Use menu 👇", reply_markup=main_menu())

# ---------------- RUN ----------------

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
