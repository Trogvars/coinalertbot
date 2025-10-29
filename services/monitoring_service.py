import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime

from database import Database, OpenInterestHistory, Alert
from api import BinanceAPI, BybitAPI, CoinglassAPI, BinanceWebSocket
from .cache_service import CacheService

logger = logging.getLogger(__name__)


class MonitoringService:
    """Сервис мониторинга криптовалют"""

    def __init__(self, db: Database, cache_service: CacheService):
        self.db = db
        self.cache_service = cache_service
        self.is_running = False
        self.websocket: Optional[BinanceWebSocket] = None
        self.websocket_active = False

    async def check_open_interest_changes(self, coins: List[Dict], settings: Dict) -> List[Dict]:
        """
        Проверка изменений Open Interest с поддержкой множественных таймфреймов
        
        Args:
            coins: Список монет для проверки
            settings: Настройки пользователя
        
        Returns:
            Список алертов об изменениях OI
        """
        alerts = []

        # Настройки таймфреймов
        timeframes = [
            ('15min', 15, settings.get('oi_threshold_15min', 2.0)),
            ('30min', 30, settings.get('oi_threshold_30min', 3.0)),
            ('1hour', 60, settings.get('oi_threshold_1hour', 5.0)),
        ]

        async with BinanceAPI() as binance:
            available_symbols = await binance.get_available_symbols()
            logger.info(f"Checking OI for {len(coins)} coins across multiple timeframes")

            checked_count = 0
            skipped_count = 0

            for coin in coins:
                symbol = coin.get('symbol')
                if not symbol:
                    continue

                binance_symbol = f"{symbol}USDT"

                if binance_symbol not in available_symbols:
                    skipped_count += 1
                    continue

                try:
                    current_oi = await binance.get_open_interest(binance_symbol)

                    if current_oi is None:
                        continue

                    checked_count += 1

                    await self.db.save_oi_history(OpenInterestHistory(
                        symbol=binance_symbol,
                        open_interest=current_oi,
                        timestamp=datetime.now(),
                        exchange='binance'
                    ))

                    for timeframe_name, minutes, threshold in timeframes:
                        previous = await self.db.get_latest_oi(
                            binance_symbol,
                            'binance',
                            minutes_ago=minutes
                        )

                        if previous and previous.open_interest > 0:
                            change_percent = ((current_oi - previous.open_interest) / previous.open_interest) * 100

                            if abs(change_percent) >= threshold:
                                alerts.append({
                                    'symbol': symbol,
                                    'exchange': 'binance',
                                    'type': 'open_interest',
                                    'timeframe': timeframe_name,
                                    'change_percent': round(change_percent, 2),
                                    'current_value': current_oi,
                                    'previous_value': previous.open_interest,
                                    'direction': 'increase' if change_percent > 0 else 'decrease',
                                    'threshold': threshold
                                })
                                logger.info(f"OI Alert [{timeframe_name}]: {symbol} {change_percent:+.2f}%")

                    await asyncio.sleep(0.2)

                except Exception as e:
                    logger.error(f"Error checking OI for {symbol}: {e}")
                    continue

            logger.info(f"OI Check complete: {checked_count} checked, {skipped_count} skipped, {len(alerts)} alerts")

        return alerts

    async def check_liquidations(self, coins: List[Dict], min_volume: float = 100000) -> List[Dict]:
        """Проверка крупных ликвидаций через Binance API (УСТАРЕЛО)"""
        logger.debug("Binance liquidation API is deprecated, skipping")
        return []

    async def detect_liquidations_from_oi(self, coins: List[Dict], oi_drop_threshold: float = 10.0) -> List[Dict]:
        """Обнаружение вероятных ликвидаций через анализ резкого падения Open Interest"""
        alerts = []

        async with BinanceAPI() as binance:
            available_symbols = await binance.get_available_symbols()
            checked_count = 0

            for coin in coins:
                symbol = coin.get('symbol')
                if not symbol:
                    continue

                binance_symbol = f"{symbol}USDT"

                if binance_symbol not in available_symbols:
                    continue

                try:
                    current_oi = await binance.get_open_interest(binance_symbol)

                    if current_oi is None:
                        continue

                    checked_count += 1
                    previous = await self.db.get_latest_oi(binance_symbol, 'binance')

                    if previous and previous.open_interest > 0:
                        change_percent = ((current_oi - previous.open_interest) / previous.open_interest) * 100

                        if change_percent <= -oi_drop_threshold:
                            estimated_side = 'long'
                            oi_decrease = previous.open_interest - current_oi
                            estimated_volume = abs(oi_decrease) * 50000

                            alerts.append({
                                'symbol': symbol,
                                'exchange': 'binance',
                                'type': 'estimated_liquidation',
                                'side': estimated_side,
                                'oi_change_percent': round(change_percent, 2),
                                'estimated_volume': estimated_volume,
                                'confidence': 'high' if abs(change_percent) > 15 else 'medium',
                                'method': 'oi_analysis'
                            })

                            logger.info(f"⚡ Estimated liquidation: {symbol} OI dropped {change_percent:.2f}%")

                    await asyncio.sleep(0.2)

                except Exception as e:
                    logger.error(f"Error analyzing OI for liquidations on {symbol}: {e}")
                    continue

            logger.info(f"Liquidation detection: {checked_count} checked, {len(alerts)} alerts")

        return alerts

    async def start_websocket_mode(self, symbols: List[str]):
        """Запуск WebSocket мониторинга"""
        if self.websocket_active:
            logger.warning("WebSocket already active")
            return

        logger.info(f"🚀 Starting WebSocket mode for {len(symbols)} symbols")
        self.websocket = BinanceWebSocket(self._on_websocket_oi_update)
        await self.websocket.start(symbols)
        self.websocket_active = True
        logger.info("✅ WebSocket mode started")

    async def stop_websocket_mode(self):
        """Остановка WebSocket мониторинга"""
        if not self.websocket_active or not self.websocket:
            return

        logger.info("🛑 Stopping WebSocket mode...")
        await self.websocket.stop()
        self.websocket = None
        self.websocket_active = False
        logger.info("✅ WebSocket mode stopped")

    async def update_websocket_symbols(self, symbols: List[str]):
        """Обновление списка символов для WebSocket"""
        if self.websocket and self.websocket_active:
            await self.websocket.update_symbols(symbols)

    async def _on_websocket_oi_update(self, update: Dict):
        """Callback для обработки обновлений OI от WebSocket"""
        symbol = update['symbol']
        change_percent = update['change_percent']

        try:
            await self.db.save_oi_history(OpenInterestHistory(
                symbol=symbol,
                open_interest=update['current_oi'],
                timestamp=update['timestamp'],
                exchange='binance'
            ))
        except Exception as e:
            logger.error(f"Error saving WebSocket OI to DB: {e}")

        users = await self.db.get_monitoring_users()

        for user in users:
            if user.settings.get('monitoring_mode') != 'websocket':
                continue

            oi_threshold = user.settings.get('oi_threshold', 1.0)
            liq_threshold = user.settings.get('liquidation_oi_threshold', 5.0)
            alerts = []

            if user.settings.get('enable_oi_alerts', True) and abs(change_percent) >= oi_threshold:
                alerts.append({
                    'symbol': symbol.replace('USDT', ''),
                    'exchange': 'binance',
                    'type': 'open_interest',
                    'change_percent': round(change_percent, 2),
                    'current_value': update['current_oi'],
                    'previous_value': update['previous_oi'],
                    'direction': 'increase' if change_percent > 0 else 'decrease',
                    'source': 'websocket'
                })
                logger.info(f"⚡ WebSocket OI Alert: {symbol} {change_percent:+.2f}%")

            if user.settings.get('enable_liquidation_detection', True) and change_percent <= -liq_threshold:
                estimated_volume = abs(update['current_oi'] - update['previous_oi']) * 50000

                alerts.append({
                    'symbol': symbol.replace('USDT', ''),
                    'exchange': 'binance',
                    'type': 'estimated_liquidation',
                    'side': 'long',
                    'oi_change_percent': round(change_percent, 2),
                    'estimated_volume': estimated_volume,
                    'confidence': 'high' if abs(change_percent) > 10 else 'medium',
                    'method': 'websocket_oi',
                    'source': 'websocket'
                })
                logger.info(f"⚡ WebSocket Liquidation: {symbol} OI dropped {change_percent:.2f}%")

            if alerts:
                for alert_data in alerts:
                    alert = Alert(
                        user_id=user.user_id,
                        alert_type=alert_data['type'],
                        symbol=alert_data['symbol'],
                        message=self._format_alert_message(alert_data),
                        value=alert_data.get('change_percent', alert_data.get('estimated_volume', 0)),
                        created_at=datetime.now()
                    )
                    await self.db.create_alert(alert)

                if hasattr(self, '_alert_service'):
                    asyncio.create_task(
                        self._alert_service.send_alerts_batch(user.chat_id, alerts)
                    )

    async def monitor_user(self, user_id: int, settings: Dict) -> List[Dict]:
        """Мониторинг для конкретного пользователя"""
        all_alerts = []

        try:
            filtered_coins = await self.cache_service.filter_coins(settings)

            if not filtered_coins:
                logger.warning(f"No coins match filters for user {user_id}")
                return []

            max_coins = settings.get('max_coins_to_check', 30)
            logger.info(f"Monitoring {len(filtered_coins)} coins for user {user_id} (checking top {max_coins})")

            if settings.get('enable_oi_alerts', True):
                oi_alerts = await self.check_open_interest_changes(
                    filtered_coins[:max_coins],
                    settings
                )
                all_alerts.extend(oi_alerts)

            if settings.get('enable_liquidation_detection', True):
                oi_drop_threshold = settings.get('liquidation_oi_threshold', 8.0)
                liq_alerts = await self.detect_liquidations_from_oi(
                    filtered_coins[:max_coins],
                    oi_drop_threshold=oi_drop_threshold
                )
                all_alerts.extend(liq_alerts)

            for alert_data in all_alerts:
                alert = Alert(
                    user_id=user_id,
                    alert_type=alert_data['type'],
                    symbol=alert_data['symbol'],
                    message=self._format_alert_message(alert_data),
                    value=alert_data.get('change_percent', alert_data.get('estimated_volume', 0)),
                    created_at=datetime.now()
                )
                await self.db.create_alert(alert)

            logger.info(f"Generated {len(all_alerts)} alerts for user {user_id}")

        except Exception as e:
            logger.error(f"Error monitoring user {user_id}: {e}")

        return all_alerts

    def _format_alert_message(self, alert_data: Dict) -> str:
        """Форматирование сообщения алерта"""
        if alert_data['type'] == 'open_interest':
            direction = "📈" if alert_data['direction'] == 'increase' else "📉"
            timeframe = alert_data.get('timeframe', 'unknown')

            timeframe_names = {
                '15min': '15 минут',
                '30min': '30 минут',
                '1hour': '1 час'
            }
            timeframe_text = timeframe_names.get(timeframe, timeframe)

            return (
                f"{direction} <b>{alert_data['symbol']}</b> OI {alert_data['direction']}\n"
                f"⏱ Период: {timeframe_text}\n"
                f"Change: {alert_data['change_percent']:+.2f}%\n"
                f"Current: {alert_data['current_value']:,.0f}\n"
                f"Previous: {alert_data['previous_value']:,.0f}"
            )

        elif alert_data['type'] == 'estimated_liquidation':
            emoji = "⚡"
            confidence = alert_data.get('confidence', 'medium')
            confidence_emoji = "🔴" if confidence == 'high' else "🟡"

            return (
                f"{emoji} <b>{alert_data['symbol']}</b> Likely {alert_data['side'].upper()} Liquidations\n"
                f"{confidence_emoji} Confidence: {confidence.title()}\n"
                f"📉 OI dropped: {alert_data['oi_change_percent']:.2f}%\n"
                f"💰 Est. volume: ${alert_data['estimated_volume']:,.0f}\n"
                f"🔍 Method: OI Analysis"
            )

        elif alert_data['type'] == 'liquidation':
            emoji = "🔴" if alert_data['side'] == 'long' else "🟢"
            return (
                f"{emoji} {alert_data['symbol']} {alert_data['side'].upper()} Liquidation\n"
                f"Volume: ${alert_data.get('volume', 0):,.2f}"
            )

        return str(alert_data)
