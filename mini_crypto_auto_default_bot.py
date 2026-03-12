# mini_crypto_auto_default_bot.py
import json
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# --- Environment variables (Railway uchun) ---
API_TOKEN = os.environ.get('API_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID'))

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

COINS_FILE = 'coins.json'
USERS_FILE = 'users.json'

# --- FSM for adding coins ---
class AddCoinState(StatesGroup):
    waiting_name = State()
    waiting_emoji = State()

# --- Helper functions ---
def load_coins():
    if not os.path.exists(COINS_FILE):
        # Agar coins.json yo‘q bo‘lsa, default coinlar
        default_coins = [
            {"name": "BTC", "emoji": "<tg-emoji emoji-id='5298576341325618295'>🙂</tg-emoji>"},
            {"name": "ETH", "emoji": "<tg-emoji emoji-id='5298576341325618296'>😎</tg-emoji>"},
            {"name": "BNB", "emoji": "<tg-emoji emoji-id='5298576341325618297'>🟠</tg-emoji>"}
        ]
        save_coins(default_coins)
        return default_coins
    try:
        with open(COINS_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_coins(coins):
    with open(COINS_FILE, 'w') as f:
        json.dump(coins, f, indent=2)

def load_users():
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def get_main_menu():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💰 Sotib olish", callback_data='buy'))
    kb.add(InlineKeyboardButton("💸 Sotish", callback_data='sell'))
    kb.add(InlineKeyboardButton("📊 Balans", callback_data='balance'))
    return kb

# --- /start ---
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    users = load_users()
    if str(message.from_user.id) not in users:
        users[str(message.from_user.id)] = {"balance": 1000, "portfolio": {}}
        save_users(users)
    await message.answer("MiniCrypto Pro Botga xush kelibsiz!", reply_markup=get_main_menu())

# --- /admin ---
@dp.message_handler(commands=['admin'])
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("Siz admin emassiz.")
        return
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("⚙️ Valyutalarni boshqarish", callback_data='admin_coins'))
    await message.answer("Admin panel", reply_markup=kb)

# --- Callback handler ---
@dp.callback_query_handler(lambda c: True, state='*')
async def process_callback(callback_query: types.CallbackQuery, state: FSMContext):
    data = callback_query.data
    coins = load_coins()
    users = load_users()

    # --- Foydalanuvchi menyusi ---
    if data == 'buy' or data == 'sell':
        if not coins:
            await bot.answer_callback_query(callback_query.id, "Hozircha coinlar mavjud emas.")
            return
        kb = InlineKeyboardMarkup()
        for coin in coins:
            kb.add(InlineKeyboardButton(f"{coin['emoji']} {coin['name']}", callback_data=f"{data}_{coin['name']}"))
        await bot.send_message(callback_query.from_user.id, "Coin tanlang:", reply_markup=kb)

    elif data.startswith('buy_') or data.startswith('sell_'):
        action, coin_name = data.split('_')
        await bot.send_message(callback_query.from_user.id, f"{action.title()} {coin_name} miqdorini kiriting (masalan: 0.01)")

    elif data == 'balance':
        user = users.get(str(callback_query.from_user.id))
        if user:
            portfolio_text = "\n".join([f"{k}: {v}" for k, v in user['portfolio'].items()]) or "Portfolio bo'sh"
            await bot.send_message(callback_query.from_user.id,
                                   f"Balans: ${user['balance']}\nPortfolio:\n{portfolio_text}")
        else:
            await bot.send_message(callback_query.from_user.id, "Balans topilmadi.")

    # --- Admin panel valyutalar boshqaruvi ---
    elif data == 'admin_coins':
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("➕ Coin qo‘shish", callback_data='add_coin'))
        kb.add(InlineKeyboardButton("➖ Coin o‘chirish", callback_data='remove_coin'))
        await bot.send_message(callback_query.from_user.id, "Valyutalarni boshqarish", reply_markup=kb)

    elif data == 'add_coin':
        await bot.send_message(callback_query.from_user.id, "Coin nomini kiriting:")
        await AddCoinState.waiting_name.set()

    elif data == 'remove_coin':
        if not coins:
            await bot.send_message(callback_query.from_user.id, "Hozircha coinlar mavjud emas.")
            return
        kb = InlineKeyboardMarkup()
        for coin in coins:
            kb.add(InlineKeyboardButton(f"{coin['emoji']} {coin['name']}", callback_data=f"del_{coin['name']}"))
        await bot.send_message(callback_query.from_user.id, "O‘chirmoqchi bo‘lgan coinni tanlang:", reply_markup=kb)

    elif data.startswith('del_'):
        name = data.split('_')[1]
        coins = [c for c in coins if c['name'].upper() != name.upper()]
        save_coins(coins)
        await bot.send_message(callback_query.from_user.id, f"Coin o‘chirildi: {name}")

# --- FSM handlers for adding coin ---
@dp.message_handler(state=AddCoinState.waiting_name)
async def coin_name_received(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.upper())
    await message.reply("Emoji ID kiriting: `<tg-emoji emoji-id='...'>` (shu jumladan animated emoji)")
    await AddCoinState.waiting_emoji.set()

@dp.message_handler(state=AddCoinState.waiting_emoji)
async def coin_emoji_received(message: types.Message, state: FSMContext):
    data = await state.get_data()
    coin_name = data['name']
    coin_emoji = message.text
    coins = load_coins()
    coins.append({"name": coin_name, "emoji": coin_emoji})
    save_coins(coins)
    await message.reply(f"Coin qo‘shildi: {coin_emoji} {coin_name}")
    await state.finish()

# --- Run bot ---
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
