import asyncio
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from database import Database

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command('start_monitoring'))
@router.callback_query(F.data == 'start_monitoring')
async def start_monitoring(event: Message | CallbackQuery, db: Database):
    """Запуск мониторинга"""
    if isinstance(event, CallbackQuery):
        message = event.message
        user_id = event.from_user.id
        await event.answer()
    else:
        message = event
        user_id = event.from_user.id
    
    user = await db.get_user(user_id)
    
    if not user:
        await message.answer("❌ Используйте /start для начала работы")
        return
    
    if user.is_monitoring:
        await message.answer("⚠️ Мониторинг уже активен!")
        return
    
    # Активируем мониторинг
    await db.set_monitoring_status(user_id, True)
    
    response_text = (
        "✅ <b>Мониторинг запущен!</b>\n\n"
        "Вы будете получать уведомления о:\n"
        "• 📈 Резких изменениях Open Interest\n"
        "• 💥 Крупных ликвидациях\n\n"
        f"Интервал проверки: {user.settings.get('update_interval', 300)} сек\n\n"
        "Для остановки используйте /stop_monitoring"
    )
    
    await message.answer(response_text, parse_mode='HTML')
    logger.info(f"User {user_id} started monitoring")


@router.message(Command('stop_monitoring'))
@router.callback_query(F.data == 'stop_monitoring')
async def stop_monitoring(event: Message | CallbackQuery, db: Database):
    """Остановка мониторинга"""
    if isinstance(event, CallbackQuery):
        message = event.message
        user_id = event.from_user.id
        await event.answer()
    else:
        message = event
        user_id = event.from_user.id
    
    user = await db.get_user(user_id)
    
    if not user:
        await message.answer("❌ Используйте /start для начала работы")
        return
    
    if not user.is_monitoring:
        await message.answer("⚠️ Мониторинг уже остановлен!")
        return
    
    # Останавливаем мониторинг
    await db.set_monitoring_status(user_id, False)
    
    await message.answer(
        "⏹ <b>Мониторинг остановлен</b>\n\n"
        "Вы не будете получать уведомления.\n"
        "Для возобновления используйте /start_monitoring",
        parse_mode='HTML'
    )
    logger.info(f"User {user_id} stopped monitoring")


@router.message(Command('test_alert'))
async def test_alert(message: Message, db: Database):
    """Тестовый алерт"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await message.answer("❌ Используйте /start")
        return
    
    test_message = (
        "🔔 <b>Тестовый Алерт</b>\n\n"
        "📈 <b>BTCUSDT</b> OI increase: +18.5%\n"
        "Current: 12,345,678\n\n"
        "💥 <b>ETHUSDT</b> LONG Liquidation\n"
        "Volume: $1,250,000\n"
        "Orders: 24"
    )
    
    await message.answer(test_message, parse_mode='HTML')


@router.message(Command('liquidations'))
async def cmd_liquidations(message: Message, db: Database):
    """Просмотр последних крупных ликвидаций через Binance"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await message.answer("❌ Используйте /start")
        return
    
    await message.answer("⏳ Загружаю данные о ликвидациях (Binance)...")
    
    try:
        from api import BinanceAPI
        
        # Список популярных монет для проверки
        symbols = ['BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'DOGE', 'ADA', 'AVAX', 'DOT', 'MATIC']
        
        liq_text = "<b>💥 Ликвидации за последние 5 минут (Binance)</b>\n\n"
        
        total_liquidations = 0
        
        async with BinanceAPI() as binance:
            for symbol in symbols:
                binance_symbol = f"{symbol}USDT"
                
                try:
                    liquidations = await binance.get_liquidations(binance_symbol, limit=50)
                    
                    if not liquidations:
                        continue
                    
                    # Анализируем ликвидации за последние 5 минут
                    from datetime import datetime
                    recent_liquidations = []
                    now = datetime.now()
                    
                    for liq in liquidations:
                        liq_time = datetime.fromtimestamp(liq['time'] / 1000)
                        if (now - liq_time).total_seconds() <= 300:  # 5 минут
                            recent_liquidations.append(liq)
                    
                    if recent_liquidations:
                        # Суммируем объемы
                        long_volume = sum(
                            float(l['origQty']) * float(l['price']) 
                            for l in recent_liquidations 
                            if l['side'] == 'SELL'  # SELL = long liquidation
                        )
                        short_volume = sum(
                            float(l['origQty']) * float(l['price']) 
                            for l in recent_liquidations 
                            if l['side'] == 'BUY'  # BUY = short liquidation
                        )
                        
                        total_vol = long_volume + short_volume
                        
                        if total_vol > 10000:  # Показываем только если > $10k
                            liq_text += (
                                f"<b>{symbol}USDT</b>\n"
                                f"🔴 Лонги: ${long_volume:,.0f}\n"
                                f"🟢 Шорты: ${short_volume:,.0f}\n"
                                f"💰 Всего: ${total_vol:,.0f}\n"
                                f"📊 Ордеров: {len(recent_liquidations)}\n\n"
                            )
                            total_liquidations += 1
                    
                    # Задержка между запросами
                    await asyncio.sleep(0.2)
                    
                except Exception as e:
                    logger.error(f"Error checking liquidations for {symbol}: {e}")
                    continue
        
        if total_liquidations == 0:
            liq_text += "✅ Нет крупных ликвидаций за последние 5 минут\n\n"
            liq_text += "<i>Проверяются только крупные позиции (>$10k)</i>"
        
        await message.answer(liq_text, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error in cmd_liquidations: {e}")
        await message.answer(
            "❌ Ошибка при загрузке данных о ликвидациях\n\n"
            "Попробуйте позже или используйте /status для проверки системы"
        )


@router.message(Command('oi'))
async def cmd_open_interest(message: Message, db: Database):
    """Просмотр текущего Open Interest для популярных монет"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await message.answer("❌ Используйте /start")
        return
    
    await message.answer("⏳ Загружаю данные Open Interest...")
    
    try:
        from api import BinanceAPI
        
        # Список популярных монет
        symbols = ['BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'DOGE', 'ADA', 'AVAX', 'DOT', 'LINK']
        
        oi_text = "<b>📊 Open Interest (Binance Futures)</b>\n\n"
        
        async with BinanceAPI() as binance:
            for symbol in symbols:
                binance_symbol = f"{symbol}USDT"
                
                try:
                    oi = await binance.get_open_interest(binance_symbol)
                    
                    if oi:
                        # Получаем историческое значение для сравнения
                        previous = await db.get_latest_oi(binance_symbol, 'binance')
                        
                        if previous and previous.open_interest > 0:
                            change_percent = ((oi - previous.open_interest) / previous.open_interest) * 100
                            change_emoji = "📈" if change_percent > 0 else "📉"
                            oi_text += (
                                f"<b>{symbol}</b>: {oi:,.0f} {change_emoji} {change_percent:+.2f}%\n"
                            )
                        else:
                            oi_text += f"<b>{symbol}</b>: {oi:,.0f}\n"
                    
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Error getting OI for {symbol}: {e}")
                    continue
        
        oi_text += "\n<i>Данные обновляются каждые 5 минут</i>"
        await message.answer(oi_text, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error in cmd_open_interest: {e}")
        await message.answer("❌ Ошибка при загрузке данных OI")

@router.message(Command('debug'))
async def cmd_debug(message: Message, db: Database):
    """Отладочная информация"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await message.answer("❌ Используйте /start")
        return
    
    # Проверяем последние записи OI
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT COUNT(*), MAX(timestamp)
        FROM open_interest_history
        WHERE timestamp > datetime('now', '-10 minutes')
    ''')
    
    oi_count, last_oi = cursor.fetchone()
    
    cursor.execute('''
        SELECT COUNT(*)
        FROM alerts
        WHERE user_id = ? AND created_at > datetime('now', '-10 minutes')
    ''', (user_id,))
    
    alert_count = cursor.fetchone()[0]
    conn.close()
    
    from config import config
    
    debug_text = (
        "<b>🔧 Отладочная Информация</b>\n\n"
        f"<b>Глобальный интервал:</b> {config.UPDATE_INTERVAL} сек\n"
        f"<b>Ваш интервал:</b> {user.settings.get('update_interval', 300)} сек\n"
        f"<b>Мониторинг:</b> {'✅ Вкл' if user.is_monitoring else '❌ Выкл'}\n\n"
        f"<b>За последние 10 минут:</b>\n"
        f"• OI записей: {oi_count}\n"
        f"• Последняя запись: {last_oi or 'Нет данных'}\n"
        f"• Ваших алертов: {alert_count}\n"
    )
    
    await message.answer(debug_text, parse_mode='HTML')

