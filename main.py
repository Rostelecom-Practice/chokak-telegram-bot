import asyncio

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
import os
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")


class Form(StatesGroup):
    waiting_for_city = State()
    city_selection = State()
    waiting_for_category = State()

CITIES_DB = {
    'москва': ['Москва'],
    'санкт-петербург': ['Санкт-Петербург'],
    'екатеринбург': ['Екатеринбург'],
    'новосибирск': ['Новосибирск'],
    'ново-': ['Новосибирск', 'Новоалтайск'],
}

main_menu_kb = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
    [KeyboardButton(text='Куда сходить')],
    [KeyboardButton(text='Что ты можешь')]
])

def get_categories_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Рестораны и кафе', callback_data='cat_restaurants')],
        [InlineKeyboardButton(text='Кино и концерты', callback_data='cat_cinema')],
        [InlineKeyboardButton(text='Парки и музеи', callback_data='cat_parks')],
        [InlineKeyboardButton(text='Шоппинг и магазины', callback_data='cat_shopping')],
    ])

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
    for key, val in CITIES_DB.items():
        if user_input in key:
            matches.extend(val)
    matches = list(dict.fromkeys(matches))

    await state.update_data(user_input=user_input)

    if not matches:
        await message.answer("Извини, я не нашёл такой город 😔", reply_markup=main_menu_kb)
        await state.clear()
        return

    if len(matches) > 1:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=city, callback_data=f"city_{city}")] for city in matches]
        )
        await state.set_state(Form.city_selection)
        await message.answer("Уточни, пожалуйста, какой из них:", reply_markup=kb)
        return

    city = matches[0]
    await state.update_data(chosen_city=city)
    await state.set_state(Form.waiting_for_category)
    await message.answer(
        f"Отлично, ты в городе «{city}»! 🔍\nВыбери категорию:",
        reply_markup=get_categories_kb()
    )

@dp.callback_query(F.data.startswith("city_"), Form.city_selection)
async def process_city_selection(callback: CallbackQuery, state: FSMContext):
    city = callback.data[len("city_"):]
    await state.update_data(chosen_city=city)
    await callback.message.edit_reply_markup()
    await state.set_state(Form.waiting_for_category)
    await callback.message.answer(
        f"Отлично, ты выбрал «{city}»! 🔍\nТеперь выбери категорию:",
        reply_markup=get_categories_kb()
    )

@dp.callback_query(F.data.startswith("cat_"), Form.waiting_for_category)
async def process_category(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    city = data.get('chosen_city')
    category_map = {
        'cat_restaurants': 'Рестораны и кафе',
        'cat_cinema': 'Кино и концерты',
        'cat_parks': 'Парки и музеи',
        'cat_shopping': 'Шоппинг и магазины',
    }
    category_name = category_map.get(callback.data, 'Неизвестная категория')
    await callback.message.edit_reply_markup()
    await callback.message.answer(
        f"Ищем в городе «{city}» то, что относится к «{category_name}»…\n\n"
        "🔎 Пока что базы нет, поэтому это заглушка. В будущем здесь будет список мест.",
        reply_markup=main_menu_kb
    )
    await state.clear()

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
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
