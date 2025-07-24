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

# 🔐 Load .env
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

storage = MemoryStorage()
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

menus = {
    "en": {
        "🍣 Rolls": [("Philadelphia Classic", 490), ("California Crab", 460), ("Okinawa", 410), ("Spicy Tuna", 470), ("Ebi Roll", 450)],
        "🍱 Sets": [("Set 'Classic'", 1250), ("Set 'Big Catch'", 1950), ("Set 'Light'", 890)],
        "🥗 Extras": [("Wasabi", 30), ("Ginger", 30), ("Soy Sauce", 30), ("Chopsticks", 0)],
        "🥤 Drinks": [("Coca-Cola 0.5L", 100), ("Sprite 0.5L", 100), ("Mineral Water", 80), ("Iced Tea", 120)]
    }
}

user_data = {}

class OrderState(StatesGroup):
    lang = State()
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
    user_data[message.chat.id] = {"cart": [], "lang": "en"}
    await message.answer("Welcome! Please use the menu below 👇", reply_markup=get_main_kb())
    await state.clear()

@router.message(F.text == "📋 Menu")
async def show_categories(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=category, callback_data=f"cat:{category}")]
        for category in menus["en"]
    ])
    await message.answer("Choose category:", reply_markup=kb)

@router.callback_query(F.data.startswith("cat:"))
async def show_items(callback: types.CallbackQuery):
    category = callback.data.split("cat:")[1]
    items = menus["en"][category]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{item} – {price}₴", callback_data=f"add:{item}:{price}")]
        for item, price in items
    ])
    await callback.message.edit_text(f"{category}:\n", reply_markup=kb)

@router.callback_query(F.data.startswith("add:"))
async def add_item(callback: types.CallbackQuery):
    _, item, price = callback.data.split(":")
    user_data[callback.from_user.id]["cart"].append((item, int(price)))
    await callback.answer(f"{item} added ✅")

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
        [InlineKeyboardButton(text=f"❌ Remove {item}", callback_data=f"remove:{i}")]
        for i, (item, _) in enumerate(cart)
    ])
    msg = "\n".join([f"{i+1}. {item} – {price}₴" for i, (item, price) in enumerate(cart)])
    await message_obj.answer(f"{msg}\n\nTotal: {total}₴", reply_markup=kb)

@router.callback_query(F.data.startswith("remove:"))
async def remove_item(callback: types.CallbackQuery):
    index = int(callback.data.split(":")[1])
    removed_item = user_data[callback.from_user.id]["cart"].pop(index)[0]
    await callback.answer(f"{removed_item} removed ❌")
    await callback.message.delete()
    await show_cart_editor(callback.from_user.id, callback.message)

@router.message(F.text == "🧾 Order")
async def start_order(message: types.Message, state: FSMContext):
    if not user_data[message.chat.id]["cart"]:
        await message.answer("Your cart is empty.")
        return
    await message.answer("Enter your name:")
    await state.set_state(OrderState.name)

@router.message(OrderState.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Enter address:")
    await state.set_state(OrderState.address)

@router.message(OrderState.address)
async def get_address(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text)
    await message.answer("Enter phone number:")
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

    await message.answer("✅ Your order has been placed!\n\n" + summary)
    await bot.send_message(ADMIN_ID, summary)
    user_data[message.chat.id]["cart"] = []
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
