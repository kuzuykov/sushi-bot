import asyncio
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# Load environment variables
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

storage = MemoryStorage()
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

# Static menu
category_map = {
    "rolls": "🍣 Rolls",
    "sets": "🍱 Sets",
    "extras": "🥗 Extras",
    "drinks": "🥤 Drinks",
}

menus = {
    "rolls": [("Philadelphia Classic", 490), ("California Crab", 460), ("Okinawa", 410), ("Spicy Tuna", 470), ("Ebi Roll", 450)],
    "sets": [("Set 'Classic'", 1250), ("Set 'Big Catch'", 1950), ("Set 'Light'", 890)],
    "extras": [("Wasabi", 30), ("Ginger", 30), ("Soy Sauce", 30), ("Chopsticks", 0)],
    "drinks": [("Coca-Cola 0.5L", 100), ("Sprite 0.5L", 100), ("Mineral Water", 80), ("Iced Tea", 120)]
}

user_data = {}
AUDIO_URL = "https://upload.wikimedia.org/wikipedia/commons/1/14/Beep-beep.ogg"

class OrderState(StatesGroup):
    name = State()
    address = State()
    phone = State()

def get_main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📋 Menu"), KeyboardButton(text="🛒 Cart")],
        [KeyboardButton(text="🧾 Order"), KeyboardButton(text="✏️ Edit Cart")]
    ], resize_keyboard=True)

@router.message(F.text == "/start")
async def start(message: types.Message, state: FSMContext):
    user_data[message.chat.id] = {"cart": []}
    await message.answer("Welcome! Please choose an option:", reply_markup=get_main_kb())
    await state.clear()

@router.message(F.text == "📋 Menu")
async def show_categories(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=category_map[key], callback_data=f"cat:{key}")]
        for key in category_map
    ])
    await message.answer("Choose a category:", reply_markup=kb)

@router.callback_query(F.data.startswith("cat:"))
async def show_items(callback: types.CallbackQuery):
    cat_key = callback.data.split(":")[1]
    items = menus[cat_key]
    kb = [[InlineKeyboardButton(text=f"{item} – {price}₴", callback_data=f"add:{item}:{price}")] for item, price in items]
    kb.append([InlineKeyboardButton(text="⬅️ Back", callback_data="back")])
    await callback.message.edit_text(f"{category_map[cat_key]}:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await bot.send_voice(callback.from_user.id, types.FSInputFile.from_url(AUDIO_URL))

@router.callback_query(F.data == "back")
async def back_to_categories(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=category_map[key], callback_data=f"cat:{key}")]
        for key in category_map
    ])
    await callback.message.edit_text("Choose a category:", reply_markup=kb)

@router.callback_query(F.data.startswith("add:"))
async def add_item(callback: types.CallbackQuery):
    _, item, price = callback.data.split(":")
    cart = user_data[callback.from_user.id]["cart"]
    cart.append((item, int(price)))
    await callback.answer(f"{item} added ✅")
    await bot.send_voice(callback.from_user.id, types.FSInputFile.from_url(AUDIO_URL))

@router.message(F.text == "🛒 Cart")
async def view_cart(message: types.Message):
    cart = user_data[message.chat.id]["cart"]
    if not cart:
        await message.answer("Cart is empty.")
        return
    total = sum(price for _, price in cart)
    lines = "\n".join([f"• {item} – {price}₴" for item, price in cart])
    await message.answer(f"🛒 Your cart:\n{lines}\n\n💰 Total: {total}₴")

@router.message(F.text == "✏️ Edit Cart")
async def edit_cart(message: types.Message):
    await show_cart_editor(message.chat.id, message)

async def show_cart_editor(user_id, message_obj):
    cart = user_data[user_id]["cart"]
    if not cart:
        await message_obj.answer("Cart is empty.")
        return
    total = sum(p for _, p in cart)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"❌ {item}", callback_data=f"remove:{i}")]
        for i, (item, _) in enumerate(cart)
    ])
    msg = "\n".join([f"{i+1}. {item} – {price}₴" for i, (item, price) in enumerate(cart)])
    await message_obj.answer(f"{msg}\n\n💰 Total: {total}₴", reply_markup=kb)

@router.callback_query(F.data.startswith("remove:"))
async def remove_item(callback: types.CallbackQuery):
    index = int(callback.data.split(":")[1])
    cart = user_data[callback.from_user.id]["cart"]
    removed_item = cart.pop(index)[0]
    await callback.answer(f"{removed_item} removed ❌")
    await callback.message.delete()
    await show_cart_editor(callback.from_user.id, callback.message)

@router.message(F.text == "🧾 Order")
async def start_order(message: types.Message, state: FSMContext):
    cart = user_data[message.chat.id]["cart"]
    if not cart:
        await message.answer("Your cart is empty.")
        return
    await message.answer("Enter your name:")
    await state.set_state(OrderState.name)

@router.message(OrderState.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Enter delivery address:")
    await state.set_state(OrderState.address)

@router.message(OrderState.address)
async def get_address(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text)
    await message.answer("Enter your phone number:")
    await state.set_state(OrderState.phone)

@router.message(OrderState.phone)
async def confirm_order(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    data = await state.get_data()
    cart = user_data[message.chat.id]["cart"]
    total = sum(p for _, p in cart)
    items = "\n".join([f"• {item} – {price}₴" for item, price in cart])

    summary = (
        f"📦 *New Order!*\n\n"
        f"👤 Name: {data['name']}\n"
        f"📍 Address: {data['address']}\n"
        f"📞 Phone: {data['phone']}\n\n"
        f"🛒 Items:\n{items}\n\n💰 Total: {total}₴"
    )

    await message.answer(
        f"✅ Your order has been placed!\n\n{summary}\n\n"
        f"We will contact you shortly.\n\nTo place a new order, press /start"
    )
    await bot.send_message(ADMIN_ID, summary)
    user_data[message.chat.id]["cart"] = []
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
