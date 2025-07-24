import asyncio
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

API_TOKEN = "7566264545:AAGXj_fDkzeiVMdZTJqTADwxQPB6MNOwLEk"  # Replace with your actual token
ADMIN_ID = 1329699633         # Replace with your Telegram ID

storage = MemoryStorage()
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

# Menu in both languages
menus = {
    "en": {
        "🍣 Rolls": [("Philadelphia Classic", 490), ("California Crab", 460), ("Okinawa", 410), ("Spicy Tuna", 470), ("Ebi Roll", 450)],
        "🍱 Sets": [("Set 'Classic'", 1250), ("Set 'Big Catch'", 1950), ("Set 'Light'", 890)],
        "🥗 Extras": [("Wasabi", 30), ("Ginger", 30), ("Soy Sauce", 30), ("Chopsticks", 0)],
        "🥤 Drinks": [("Coca-Cola 0.5L", 100), ("Sprite 0.5L", 100), ("Mineral Water", 80), ("Iced Tea", 120)]
    },
    "uk": {
        "🍣 Роли": [("Філадельфія класик", 490), ("Каліфорнія з крабом", 460), ("Окінава", 410), ("Спайсі тунець", 470), ("Ебі рол", 450)],
        "🍱 Сети": [("Сет 'Класик'", 1250), ("Сет 'Великий улов'", 1950), ("Сет 'Лайт'", 890)],
        "🥗 Додатково": [("Васабі", 30), ("Імбир", 30), ("Соєвий соус", 30), ("Палички", 0)],
        "🥤 Напої": [("Кока-Кола 0.5л", 100), ("Спрайт 0.5л", 100), ("Мінералка", 80), ("Холодний чай", 120)]
    }
}

user_data = {}

class OrderState(StatesGroup):
    lang = State()
    name = State()
    address = State()
    phone = State()

def get_main_kb(lang):
    if lang == "en":
        return ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text="📋 Menu"), KeyboardButton(text="🛒 Cart")],
            [KeyboardButton(text="🧾 Order"), KeyboardButton(text="✏️ Edit Cart")]
        ], resize_keyboard=True)
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📋 Меню"), KeyboardButton(text="🛒 Кошик")],
        [KeyboardButton(text="🧾 Замовити"), KeyboardButton(text="✏️ Редагувати кошик")]
    ], resize_keyboard=True)

@router.message(F.text == "/start")
async def start(message: types.Message, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en")],
        [InlineKeyboardButton(text="🇺🇦 Українська", callback_data="lang:uk")]
    ])
    await message.answer("Please choose your language / Оберіть мову:", reply_markup=kb)
    await state.set_state(OrderState.lang)

@router.callback_query(F.data.startswith("lang:"))
async def set_language(callback: types.CallbackQuery, state: FSMContext):
    lang = callback.data.split(":")[1]
    user_data[callback.from_user.id] = {"cart": [], "lang": lang}
    await callback.message.answer("Language set ✅" if lang == "en" else "Мову встановлено ✅",
                                  reply_markup=get_main_kb(lang))
    await state.clear()

@router.message(lambda msg: msg.text in ["📋 Menu", "📋 Меню"])
async def show_categories(message: types.Message):
    lang = user_data[message.chat.id]["lang"]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=category, callback_data=f"cat:{category}")]
        for category in menus[lang]
    ])
    await message.answer("Choose category:" if lang == "en" else "Оберіть категорію:", reply_markup=kb)

@router.callback_query(F.data.startswith("cat:"))
async def show_items(callback: types.CallbackQuery):
    category = callback.data.split("cat:")[1]
    lang = user_data[callback.from_user.id]["lang"]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{item} – {price}₴", callback_data=f"add:{item}:{price}")]
        for item, price in menus[lang][category]]
    )
    await callback.message.edit_text(f"{category}:\n", reply_markup=kb)

@router.callback_query(F.data.startswith("add:"))
async def add_item(callback: types.CallbackQuery):
    _, item, price = callback.data.split(":")
    cart = user_data[callback.from_user.id]["cart"]
    cart.append((item, int(price)))
    await callback.answer(f"{item} added ✅")

@router.message(lambda msg: msg.text in ["🛒 Cart", "🛒 Кошик"])
async def view_cart(message: types.Message):
    lang = user_data[message.chat.id]["lang"]
    cart = user_data[message.chat.id]["cart"]
    if not cart:
        await message.answer("Cart is empty." if lang == "en" else "Кошик порожній.")
        return
    total = sum(price for _, price in cart)
    lines = "\n".join([f"• {item} – {price}₴" for item, price in cart])
    await message.answer(f"🛒 Your cart:\n{lines}\n\n💰 Total: {total}₴")

@router.message(lambda msg: msg.text in ["✏️ Edit Cart", "✏️ Редагувати кошик"])
async def edit_cart(message: types.Message):
    await show_cart_editor(message.chat.id, message)

async def show_cart_editor(user_id, message_obj):
    lang = user_data[user_id]["lang"]
    cart = user_data[user_id]["cart"]
    if not cart:
        await message_obj.answer("Cart is empty." if lang == "en" else "Кошик порожній.")
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
    cart = user_data[callback.from_user.id]["cart"]
    removed_item = cart.pop(index)[0]
    await callback.answer(f"{removed_item} removed ❌")
    await callback.message.delete()
    await show_cart_editor(callback.from_user.id, callback.message)

@router.message(lambda msg: msg.text in ["🧾 Order", "🧾 Замовити"])
async def start_order(message: types.Message, state: FSMContext):
    cart = user_data[message.chat.id]["cart"]
    if not cart:
        await message.answer("Your cart is empty." if user_data[message.chat.id]["lang"] == "en" else "Кошик порожній.")
        return
    await message.answer("Enter your name:" if user_data[message.chat.id]["lang"] == "en" else "Введіть ім’я:")
    await state.set_state(OrderState.name)

@router.message(OrderState.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Enter address:" if user_data[message.chat.id]["lang"] == "en" else "Введіть адресу:")
    await state.set_state(OrderState.address)

@router.message(OrderState.address)
async def get_address(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text)
    await message.answer("Enter phone number:" if user_data[message.chat.id]["lang"] == "en" else "Введіть телефон:")
    await state.set_state(OrderState.phone)

@router.message(OrderState.phone)
async def confirm_order(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    data = await state.get_data()
    cart = user_data[message.chat.id]["cart"]
    lang = user_data[message.chat.id]["lang"]
    total = sum(p for _, p in cart)
    items = "\n".join([f"• {item} – {price}₴" for item, price in cart])

    summary = (
        f"📦 *New Order!*\n\n"
        f"👤 Name: {data['name']}\n"
        f"📍 Address: {data['address']}\n"
        f"📞 Phone: {data['phone']}\n\n"
        f"🛒 Items:\n{items}\n\n💰 Total: {total}₴"
    )

    user_text = (
        f"✅ {'Your order has been placed!' if lang == 'en' else 'Ваше замовлення прийнято!'}\n\n"
        f"{summary}\n\n"
        f"{'We will contact you shortly.' if lang == 'en' else 'Ми скоро з вами зв’яжемося.'}\n\n"
        f"{'To place a new order, press /start' if lang == 'en' else 'Щоб зробити нове замовлення, натисніть /start'}"
    )

    await message.answer(user_text)
    await bot.send_message(ADMIN_ID, summary)
    user_data[message.chat.id]["cart"] = []
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
