from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu() -> InlineKeyboardMarkup:
    """Главное меню"""
    keyboard = [
        [
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings"),
            InlineKeyboardButton(text="📊 Статус", callback_data="status")
        ],
        [
            InlineKeyboardButton(text="▶️ Запустить", callback_data="start_monitoring"),
            InlineKeyboardButton(text="⏹ Остановить", callback_data="stop_monitoring")
        ],
        [
            InlineKeyboardButton(text="📋 Монеты", callback_data="coins"),
            InlineKeyboardButton(text="📖 Помощь", callback_data="help")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_settings_menu() -> InlineKeyboardMarkup:
    """Меню настроек"""
    keyboard = [
        [
            InlineKeyboardButton(text="💰 Капитализация", callback_data="set_market_cap"),
            InlineKeyboardButton(text="📊 Объем 24ч", callback_data="set_volume")
        ],
        [
            InlineKeyboardButton(text="📈 Порог OI", callback_data="set_oi_threshold"),
            InlineKeyboardButton(text="💧 Ликвидации", callback_data="set_liquidation_volume")
        ],
        [
            InlineKeyboardButton(text="🚫 Исключить топ", callback_data="set_exclude_top"),
            InlineKeyboardButton(text="⏱ Интервал", callback_data="set_interval")
        ],
        [
            InlineKeyboardButton(text="✅ OI алерты", callback_data="toggle_enable_oi_alerts"),
            InlineKeyboardButton(text="💥 Ликв. алерты", callback_data="toggle_enable_liquidation_alerts")
        ],
        [
            InlineKeyboardButton(text="🟢 Лонги", callback_data="toggle_long_alerts"),
            InlineKeyboardButton(text="🔴 Шорты", callback_data="toggle_short_alerts")
        ],
        [
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_back_button() -> InlineKeyboardMarkup:
    """Кнопка назад"""
    keyboard = [
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_confirmation_keyboard(action: str) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения"""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_{action}"),
            InlineKeyboardButton(text="❌ Нет", callback_data="back_to_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
