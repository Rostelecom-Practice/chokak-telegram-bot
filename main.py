import asyncio
import os

from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from api import get_cities_from_api, prepare_cities_db, fetch_organizations

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")

class Form(StatesGroup):
    waiting_for_city = State()
    city_selection = State()
    waiting_for_category = State()

CITIES_DB = {}

main_menu_kb = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
    [KeyboardButton(text='Куда сходить')],
    [KeyboardButton(text='Что ты можешь')]
])


def get_categories_kb():
    builder = InlineKeyboardBuilder()

    categories = {
        'RESTAURANTS_AND_CAFES': 'Рестораны и кафе',
        'CINEMA_AND_CONCERTS': 'Кино и концерты',
        'PARKS_AND_MUSEUMS': 'Парки и музеи',
        'SHOPPING_AND_STORES': 'Шоппинг и магазины',
        'HOTELS_AND_HOSTELS': 'Отели и хостелы',
    }

    for category_code, category_name in categories.items():
        builder.button(text=category_name, callback_data=f"cat_{category_code}")

    builder.adjust(3)

    return builder.as_markup()

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

@dp.message(F.text.lower().in_(['привет', 'здравствуйте', 'хай', 'добрый день']))
async def greeting_handler(message: Message):
    await message.answer(f"Привет, {message.from_user.first_name}! 😊", reply_markup=main_menu_kb)

@dp.message(F.text == 'Что ты можешь')
async def what_can_you_do(message: Message):
    await message.answer(
        "Этот бот может помочь тебе:\n"
        "• Найти рестораны и кафе в твоём городе;\n"
        "• Узнать, какие кино и концерты проходят;\n"
        "• Получить информацию о парках и музеях;\n"
        "• А также о шоппинге, магазинах и т. д.\n\n"
        "Для начала нажми «Куда сходить», и я спрошу у тебя город.",
        reply_markup=main_menu_kb
    )

@dp.message(F.text == 'Куда сходить')
async def where_to_go(message: Message, state: FSMContext):
    await state.set_state(Form.waiting_for_city)
    await message.answer(
        f"{message.from_user.first_name}, в каком городе ты находишься?",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(Form.waiting_for_city)
async def process_city(message: Message, state: FSMContext):
    user_input = message.text.strip().lower()
    matches = []

    for key, info in CITIES_DB.items():
        if user_input in key:
            matches.append(info['name'])

    await state.update_data(user_input=user_input)

    if not matches:
        await message.answer("Извини, я не нашёл такой город 😔", reply_markup=main_menu_kb)
        await state.clear()
        return

    if len(matches) > 1:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=city, callback_data=f"city_{city}")]
            for city in matches
        ])
        await state.set_state(Form.city_selection)
        await message.answer("Уточни, пожалуйста, какой из них:", reply_markup=kb)
        return

    chosen = matches[0]
    await state.update_data(chosen_city=chosen)
    await state.set_state(Form.waiting_for_category)
    await message.answer(
        f"Отлично, ты в городе «{chosen}»! 🔍\nВыбери категорию:",
        reply_markup=get_categories_kb()
    )

@dp.callback_query(F.data.startswith("cat_"), Form.waiting_for_category)
async def process_category(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    city_info = CITIES_DB.get(data['chosen_city'].lower())
    if not city_info:
        return await callback.message.answer("Город не найден в базе.", reply_markup=main_menu_kb)

    cat_code = callback.data[len("cat_"):]
    request_body = {
        "cityId":  city_info['id'],
        "type":    cat_code,
        "criteria":"RELEVANCE",
        "to":      2
    }
    results = await fetch_organizations(request_body)

    if not results:
        return await callback.message.answer(
            f"К сожалению, в «{city_info['name']}» ничего не нашлось в выбранной категории.",
            reply_markup=main_menu_kb
        )

    messages = []
    for org in results:
        name    = org.get('name', 'Без названия')
        address = org.get('address', 'Адрес не указан')
        rating  = org.get('rating', 0)
        stars = max(0, min(5, int(round(rating))))
        stars_line = '⭐' * stars + '☆' * (5 - stars)

        block = (
            f"<b>{name}</b>\n"
            f"{address}\n"
            f"{stars_line}  ({rating:.1f})"
        )
        messages.append(block)

    text = "\n\n".join(messages)
    await callback.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=main_menu_kb
    )

@dp.message(F.text.startswith('/start'))
async def cmd_start(message: Message):
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        "Я помогу тебе найти интересные места в твоём городе. Нажми «Куда сходить» для начала!",
        reply_markup=main_menu_kb
    )

@dp.message(F.text.startswith('/help'))
async def cmd_help(message: Message):
    await what_can_you_do(message)

@dp.message()
async def fallback(message: Message):
    await message.answer("Я не понял тебя. Используй кнопки ниже:", reply_markup=main_menu_kb)

async def main():
    global CITIES_DB
    cities = await get_cities_from_api()
    CITIES_DB = prepare_cities_db(cities)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
