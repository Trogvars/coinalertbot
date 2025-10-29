from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging

from database import Database
from bot.keyboards.inline import get_settings_menu, get_back_button

logger = logging.getLogger(__name__)

router = Router()


class SettingsStates(StatesGroup):
    waiting_for_market_cap = State()
    waiting_for_volume = State()
    waiting_for_oi_threshold = State()
    waiting_for_liquidation_volume = State()
    waiting_for_exclude_top = State()
    waiting_for_interval = State()
    waiting_for_max_coins = State()


@router.message(Command('settings'))
async def cmd_settings(message: Message, db: Database):
    """Настройки мониторинга"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await message.answer("❌ Используйте /start для начала работы")
        return
    
    settings = user.settings
    
    settings_text = (
        "<b>⚙️ Настройки Мониторинга</b>\n\n"
        f"💰 <b>Мин. капитализация:</b> ${settings.get('min_market_cap', 0):,.0f}\n"
        f"📊 <b>Мин. объем 24ч:</b> ${settings.get('min_volume_24h', 0):,.0f}\n"
        f"📈 <b>Порог OI:</b> {settings.get('oi_threshold', 15)}%\n"
        f"💧 <b>Мин. ликвидации:</b> ${settings.get('liquidation_volume', 100000):,.0f}\n"
        f"🚫 <b>Исключить топ:</b> {settings.get('exclude_top_n', 10)} монет\n"
        f"⏱ <b>Интервал:</b> {settings.get('update_interval', 300)} сек\n"
        f"🔢 <b>Макс. монет:</b> {settings.get('max_coins_to_check', 50)} шт\n\n"
        f"✅ <b>OI алерты:</b> {'Вкл' if settings.get('enable_oi_alerts', True) else 'Выкл'}\n"
        f"💥 <b>Ликвидации:</b> {'Вкл' if settings.get('enable_liquidation_alerts', True) else 'Выкл'}\n"
        f"🟢 <b>Лонг алерты:</b> {'Вкл' if settings.get('long_alerts', True) else 'Выкл'}\n"
        f"🔴 <b>Шорт алерты:</b> {'Вкл' if settings.get('short_alerts', True) else 'Выкл'}\n"
    )
    
    await message.answer(
        settings_text,
        reply_markup=get_settings_menu(),
        parse_mode='HTML'
    )


@router.callback_query(F.data == 'set_market_cap')
async def set_market_cap(callback: CallbackQuery, state: FSMContext):
    """Установка минимальной капитализации"""
    await callback.message.answer(
        "💰 Введите минимальную капитализацию в USD\n"
        "Например: 100000000 (для $100M)\n\n"
        "Или /cancel для отмены",
        reply_markup=get_back_button()
    )
    await state.set_state(SettingsStates.waiting_for_market_cap)
    await callback.answer()


@router.message(SettingsStates.waiting_for_market_cap)
async def process_market_cap(message: Message, state: FSMContext, db: Database):
    """Обработка ввода капитализации"""
    if message.text == '/cancel':
        await state.clear()
        await message.answer("❌ Отменено")
        return
    
    try:
        value = float(message.text.replace(',', '').replace(' ', ''))
        if value < 0:
            raise ValueError("Negative value")
        
        user_id = message.from_user.id
        user = await db.get_user(user_id)
        user.settings['min_market_cap'] = value
        await db.update_user_settings(user_id, user.settings)
        
        await message.answer(
            f"✅ Минимальная капитализация установлена: ${value:,.0f}",
            reply_markup=get_settings_menu()
        )
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Неверный формат. Введите число (например: 100000000)")


@router.callback_query(F.data == 'set_volume')
async def set_volume(callback: CallbackQuery, state: FSMContext):
    """Установка минимального объема"""
    await callback.message.answer(
        "📊 Введите минимальный объем 24ч в USD\n"
        "Например: 10000000 (для $10M)",
        reply_markup=get_back_button()
    )
    await state.set_state(SettingsStates.waiting_for_volume)
    await callback.answer()


@router.message(SettingsStates.waiting_for_volume)
async def process_volume(message: Message, state: FSMContext, db: Database):
    """Обработка ввода объема"""
    if message.text == '/cancel':
        await state.clear()
        await message.answer("❌ Отменено")
        return
    
    try:
        value = float(message.text.replace(',', '').replace(' ', ''))
        if value < 0:
            raise ValueError("Negative value")
        
        user_id = message.from_user.id
        user = await db.get_user(user_id)
        user.settings['min_volume_24h'] = value
        await db.update_user_settings(user_id, user.settings)
        
        await message.answer(
            f"✅ Минимальный объем установлен: ${value:,.0f}",
            reply_markup=get_settings_menu()
        )
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Неверный формат. Введите число")


@router.callback_query(F.data == 'set_oi_threshold')
async def set_oi_threshold(callback: CallbackQuery, state: FSMContext):
    """Установка порога OI"""
    await callback.message.answer(
        "📈 Введите порог изменения Open Interest в %\n"
        "Например: 15 (для алертов при изменении &gt;15%)\n\n"
        "Рекомендуется: 5-20%",
        reply_markup=get_back_button()
    )
    await state.set_state(SettingsStates.waiting_for_oi_threshold)
    await callback.answer()


@router.message(SettingsStates.waiting_for_oi_threshold)
async def process_oi_threshold(message: Message, state: FSMContext, db: Database):
    """Обработка порога OI"""
    if message.text == '/cancel':
        await state.clear()
        await message.answer("❌ Отменено")
        return
    
    try:
        value = float(message.text)
        if value <= 0 or value > 100:
            raise ValueError("Invalid range")
        
        user_id = message.from_user.id
        user = await db.get_user(user_id)
        user.settings['oi_threshold'] = value
        await db.update_user_settings(user_id, user.settings)
        
        await message.answer(
            f"✅ Порог OI установлен: {value}%",
            reply_markup=get_settings_menu()
        )
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Введите число от 0 до 100")


@router.callback_query(F.data == 'set_liquidation_volume')
async def set_liquidation_volume(callback: CallbackQuery, state: FSMContext):
    """Установка минимального объема ликвидаций"""
    await callback.message.answer(
        "💧 Введите минимальный объем ликвидаций в USD\n"
        "Например: 100000 (для $100k)\n\n"
        "Рекомендуется: 10,000-100,000",
        reply_markup=get_back_button()
    )
    await state.set_state(SettingsStates.waiting_for_liquidation_volume)
    await callback.answer()


@router.message(SettingsStates.waiting_for_liquidation_volume)
async def process_liquidation_volume(message: Message, state: FSMContext, db: Database):
    """Обработка объема ликвидаций"""
    if message.text == '/cancel':
        await state.clear()
        await message.answer("❌ Отменено")
        return
    
    try:
        value = float(message.text.replace(',', '').replace(' ', ''))
        if value < 0:
            raise ValueError("Negative value")
        
        user_id = message.from_user.id
        user = await db.get_user(user_id)
        user.settings['liquidation_volume'] = value
        await db.update_user_settings(user_id, user.settings)
        
        await message.answer(
            f"✅ Минимальный объем ликвидаций: ${value:,.0f}",
            reply_markup=get_settings_menu()
        )
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Неверный формат. Введите число")


@router.callback_query(F.data == 'set_exclude_top')
async def set_exclude_top(callback: CallbackQuery, state: FSMContext):
    """Установка исключения топ монет"""
    await callback.message.answer(
        "🚫 Сколько топовых монет исключить?\n"
        "Например: 10 (исключит BTC, ETH и т.д.)\n\n"
        "0 = не исключать\n"
        "10 = исключить топ-10",
        reply_markup=get_back_button()
    )
    await state.set_state(SettingsStates.waiting_for_exclude_top)
    await callback.answer()


@router.message(SettingsStates.waiting_for_exclude_top)
async def process_exclude_top(message: Message, state: FSMContext, db: Database):
    """Обработка исключения топ монет"""
    if message.text == '/cancel':
        await state.clear()
        await message.answer("❌ Отменено")
        return
    
    try:
        value = int(message.text)
        if value < 0:
            raise ValueError("Negative value")
        
        user_id = message.from_user.id
        user = await db.get_user(user_id)
        user.settings['exclude_top_n'] = value
        await db.update_user_settings(user_id, user.settings)
        
        await message.answer(
            f"✅ Исключено топ: {value} монет",
            reply_markup=get_settings_menu()
        )
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Введите целое число")


@router.callback_query(F.data == 'set_interval')
async def set_interval(callback: CallbackQuery, state: FSMContext):
    """Установка интервала обновления"""
    await callback.message.answer(
        "⏱ Введите интервал обновления в секундах\n"
        "Например: 300 (для 5 минут)\n\n"
        "⚠️ Минимум: 60 секунд (1 минута)\n"
        "Рекомендуется: 300-600 секунд",
        reply_markup=get_back_button()
    )
    await state.set_state(SettingsStates.waiting_for_interval)
    await callback.answer()


@router.message(SettingsStates.waiting_for_interval)
async def process_interval(message: Message, state: FSMContext, db: Database):
    """Обработка интервала"""
    if message.text == '/cancel':
        await state.clear()
        await message.answer("❌ Отменено")
        return
    
    try:
        value = int(message.text)
        if value < 60:
            raise ValueError("Too low")
        
        user_id = message.from_user.id
        user = await db.get_user(user_id)
        user.settings['update_interval'] = value
        await db.update_user_settings(user_id, user.settings)
        
        await message.answer(
            f"✅ Интервал установлен: {value} сек ({value//60} мин)\n\n"
            f"⚠️ Изменения вступят в силу после перезапуска мониторинга",
            reply_markup=get_settings_menu()
        )
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Введите число &gt;= 60")


@router.callback_query(F.data == 'set_max_coins')
async def set_max_coins(callback: CallbackQuery, state: FSMContext):
    """Установка максимального количества монет для проверки"""
    await callback.message.answer(
        "🔢 Введите максимальное количество монет для проверки\n"
        "Например: 100\n\n"
        "⚠️ Больше монет = дольше проверка\n"
        "• 50 монет ≈ 10 сек\n"
        "• 100 монет ≈ 20 сек\n"
        "• 165 монет ≈ 33 сек\n\n"
        "Рекомендуется: 50-100",
        reply_markup=get_back_button()
    )
    await state.set_state(SettingsStates.waiting_for_max_coins)
    await callback.answer()


@router.message(SettingsStates.waiting_for_max_coins)
async def process_max_coins(message: Message, state: FSMContext, db: Database):
    """Обработка максимального количества монет"""
    if message.text == '/cancel':
        await state.clear()
        await message.answer("❌ Отменено")
        return
    
    try:
        value = int(message.text)
        if value < 10 or value > 200:
            raise ValueError("Out of range")
        
        user_id = message.from_user.id
        user = await db.get_user(user_id)
        user.settings['max_coins_to_check'] = value
        await db.update_user_settings(user_id, user.settings)
        
        estimated_time = value * 0.2
        
        await message.answer(
            f"✅ Максимум монет для проверки: {value}\n\n"
            f"⏱ Примерное время проверки: ~{estimated_time:.0f} секунд",
            reply_markup=get_settings_menu()
        )
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Введите число от 10 до 200")


# Колбэки для переключателей
@router.callback_query(F.data.startswith('toggle_'))
async def toggle_setting(callback: CallbackQuery, db: Database):
    """Переключение булевых настроек"""
    setting_key = callback.data.replace('toggle_', '')
    
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    
    # Переключаем значение
    current = user.settings.get(setting_key, True)
    user.settings[setting_key] = not current
    await db.update_user_settings(user_id, user.settings)
    
    status = "включено" if user.settings[setting_key] else "выключено"
    await callback.answer(f"✅ Настройка {status}")
    
    # Обновляем сообщение
    settings = user.settings
    
    settings_text = (
        "<b>⚙️ Настройки Мониторинга</b>\n\n"
        f"💰 <b>Мин. капитализация:</b> ${settings.get('min_market_cap', 0):,.0f}\n"
        f"📊 <b>Мин. объем 24ч:</b> ${settings.get('min_volume_24h', 0):,.0f}\n"
        f"📈 <b>Порог OI:</b> {settings.get('oi_threshold', 15)}%\n"
        f"💧 <b>Мин. ликвидации:</b> ${settings.get('liquidation_volume', 100000):,.0f}\n"
        f"🚫 <b>Исключить топ:</b> {settings.get('exclude_top_n', 10)} монет\n"
        f"⏱ <b>Интервал:</b> {settings.get('update_interval', 300)} сек\n"
        f"🔢 <b>Макс. монет:</b> {settings.get('max_coins_to_check', 50)} шт\n\n"
        f"✅ <b>OI алерты:</b> {'Вкл' if settings.get('enable_oi_alerts', True) else 'Выкл'}\n"
        f"💥 <b>Ликвидации:</b> {'Вкл' if settings.get('enable_liquidation_alerts', True) else 'Выкл'}\n"
        f"🟢 <b>Лонг алерты:</b> {'Вкл' if settings.get('long_alerts', True) else 'Выкл'}\n"
        f"🔴 <b>Шорт алерты:</b> {'Вкл' if settings.get('short_alerts', True) else 'Выкл'}\n"
    )
    
    await callback.message.edit_text(
        settings_text,
        reply_markup=get_settings_menu(),
        parse_mode='HTML'
    )


@router.callback_query(F.data == 'back_to_menu')
async def back_to_menu(callback: CallbackQuery):
    """Возврат в главное меню"""
    from bot.keyboards.inline import get_main_menu
    
    await callback.message.edit_text(
        "🏠 Главное меню",
        reply_markup=get_main_menu()
    )
    await callback.answer()
