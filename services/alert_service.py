import asyncio
import logging
from typing import List, Dict
from datetime import datetime

from aiogram import Bot
from database import Database
from .monitoring_service import MonitoringService

logger = logging.getLogger(__name__)


class AlertService:
    """Сервис отправки алертов пользователям"""

    def __init__(self, bot: Bot, db: Database, monitoring_service: MonitoringService):
        self.bot = bot
        self.db = db
        self.monitoring_service = monitoring_service
        self.is_running = False

    async def send_alert(self, chat_id: int, alert_message: str):
        """Отправка одного алерта"""
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=alert_message,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            logger.info(f"Alert sent to chat {chat_id}")
        except Exception as e:
            logger.error(f"Error sending alert to {chat_id}: {e}")

    async def send_alerts_batch(self, chat_id: int, alerts: List[Dict]):
        """Отправка пакета алертов с группировкой по таймфреймам"""
        if not alerts:
            return

        try:
            # Группируем алерты по типу
            oi_alerts = [a for a in alerts if a.get('type') == 'open_interest']
            liq_alerts = [a for a in alerts if a.get('type') == 'estimated_liquidation']

            # Отправляем OI алерты, группируя по таймфреймам
            if oi_alerts:
                # Группируем по таймфрейму
                timeframes = {}
                for alert in oi_alerts:
                    tf = alert.get('timeframe', 'unknown')
                    if tf not in timeframes:
                        timeframes[tf] = []
                    timeframes[tf].append(alert)

                # Отправляем по таймфреймам
                timeframe_names = {
                    '15min': '15 минут',
                    '30min': '30 минут',
                    '1hour': '1 час'
                }

                for tf, tf_alerts in timeframes.items():
                    tf_name = timeframe_names.get(tf, tf)
                    message = f"<b>📊 Open Interest Changes ({tf_name})</b>\n\n"

                    for alert in tf_alerts[:10]:
                        direction = "📈" if alert['direction'] == 'increase' else "📉"
                        message += f"{direction} <b>{alert['symbol']}</b>: {alert['change_percent']:+.2f}%\n"

                    if len(tf_alerts) > 10:
                        message += f"\n<i>... и еще {len(tf_alerts) - 10}</i>"

                    await self.send_alert(chat_id, message)
                    await asyncio.sleep(1)

            # Отправляем Liquidation алерты
            if liq_alerts:
                message = "<b>⚡ Estimated Liquidations</b>\n\n"

                for alert in liq_alerts[:10]:
                    confidence = alert.get('confidence', 'medium')
                    confidence_emoji = "🔴" if confidence == 'high' else "🟡"

                    message += (
                        f"{confidence_emoji} <b>{alert['symbol']}</b> {alert['side'].upper()}\n"
                        f"   OI: {alert['oi_change_percent']:.2f}% | "
                        f"${alert['estimated_volume']/1000000:.1f}M\n"
                    )

                if len(liq_alerts) > 10:
                    message += f"\n<i>... и еще {len(liq_alerts) - 10}</i>"

                await self.send_alert(chat_id, message)

            logger.info(f"Sent {len(alerts)} alerts to chat {chat_id}")

        except Exception as e:
            logger.error(f"Error sending alerts batch to {chat_id}: {e}")

    async def monitoring_loop(self, interval: int = 300):
        """Основной цикл мониторинга"""
        self.is_running = True
        logger.info(f"Started monitoring loop with interval {interval}s")

        # Связываем monitoring_service с alert_service для WebSocket callback
        self.monitoring_service._alert_service = self

        while self.is_running:
            try:
                users = await self.db.get_monitoring_users()

                if users:
                    logger.info(f"Processing {len(users)} active users")

                    # Проверяем нужен ли WebSocket
                    websocket_users = [u for u in users if u.settings.get('monitoring_mode') == 'websocket']
                    api_users = [u for u in users if u.settings.get('monitoring_mode') != 'websocket']

                    # Запускаем WebSocket если есть пользователи
                    if websocket_users and not self.monitoring_service.websocket_active:
                        # Собираем все уникальные символы
                        all_symbols = set()
                        for user in websocket_users:
                            filtered_coins = await self.monitoring_service.cache_service.filter_coins(user.settings)

                            max_coins = user.settings.get('max_coins_to_check', 30)
                            symbols = [f"{coin['symbol']}USDT" for coin in filtered_coins[:max_coins]]
                            all_symbols.update(symbols)

                        if all_symbols:
                            logger.info(f"🚀 Starting WebSocket for {len(all_symbols)} symbols")
                            await self.monitoring_service.start_websocket_mode(list(all_symbols))

                    # Обрабатываем API пользователей
                    for user in api_users:
                        try:
                            alerts = await self.monitoring_service.monitor_user(
                                user.user_id,
                                user.settings
                            )

                            if alerts:
                                logger.info(f"📤 Sending {len(alerts)} alerts to user {user.user_id}")
                                await self.send_alerts_batch(user.chat_id, alerts)

                            await asyncio.sleep(1)

                        except Exception as e:
                            logger.error(f"Error processing user {user.user_id}: {e}")
                            continue

                    logger.info(f"Monitoring cycle completed. Next check in {interval}s")
                else:
                    logger.debug("No active monitoring users")

                    # Останавливаем WebSocket если нет пользователей
                    if self.monitoring_service.websocket_active:
                        await self.monitoring_service.stop_websocket_mode()

                await asyncio.sleep(interval)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)

    def stop(self):
        """Остановка мониторинга"""
        self.is_running = False
        logger.info("Alert service stopped")
