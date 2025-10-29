import websockets
import json
import asyncio
import logging
from typing import Callable, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BinanceWebSocket:
    """WebSocket клиент для мониторинга Open Interest в реальном времени"""
    
    def __init__(self, on_oi_update: Callable):
        """
        Args:
            on_oi_update: Callback функция для обработки обновлений OI
        """
        self.ws_url = "wss://fstream.binance.com/ws"
        self.on_oi_update = on_oi_update
        self.running = False
        self.subscribed_symbols = []
        self.oi_cache = {}  # {symbol: {'oi': value, 'timestamp': datetime}}
        self.websocket = None
        self.reconnect_delay = 5
        self.max_reconnect_delay = 60
    
    async def start(self, symbols: List[str]):
        """
        Запуск WebSocket подключения
        
        Args:
            symbols: Список символов для мониторинга (например, ['BTCUSDT', 'ETHUSDT'])
        """
        self.subscribed_symbols = [s.lower() for s in symbols]
        self.running = True
        
        logger.info(f"📡 Starting WebSocket for {len(symbols)} symbols...")
        
        # Запускаем в фоне
        asyncio.create_task(self._maintain_connection())
    
    async def _maintain_connection(self):
        """Поддержка постоянного подключения с автоматическим reconnect"""
        while self.running:
            try:
                await self._connect_and_listen()
            except Exception as e:
                logger.error(f"WebSocket connection failed: {e}")
                if self.running:
                    logger.info(f"Reconnecting in {self.reconnect_delay}s...")
                    await asyncio.sleep(self.reconnect_delay)
                    # Увеличиваем задержку (exponential backoff)
                    self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
    
    async def _connect_and_listen(self):
        """Подключение и прослушивание обновлений"""
        # Формируем streams
        streams = "/".join([f"{symbol}@openInterest" for symbol in self.subscribed_symbols])
        ws_url = f"{self.ws_url}/{streams}"
        
        logger.info(f"🔌 Connecting to {ws_url[:80]}...")
        
        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=10) as websocket:
            self.websocket = websocket
            self.reconnect_delay = 5  # Сбрасываем задержку при успешном подключении
            
            logger.info(f"✅ WebSocket connected! Listening for OI updates...")
            
            # Прослушиваем сообщения
            async for message in websocket:
                if not self.running:
                    break
                
                try:
                    data = json.loads(message)
                    await self._process_message(data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received: {message[:100]}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
    
    async def _process_message(self, data: Dict):
        """
        Обработка входящего сообщения
        
        Формат Binance WebSocket для Open Interest:
        {
            "e": "openInterest",
            "E": 1234567890000,
            "s": "BTCUSDT",
            "o": "78123.456"
        }
        """
        if data.get('e') != 'openInterest':
            return
        
        symbol = data.get('s', '').upper()
        current_oi = float(data.get('o', 0))
        timestamp = datetime.fromtimestamp(data.get('E', 0) / 1000)
        
        if not symbol or current_oi <= 0:
            return
        
        # Проверяем изменение
        if symbol in self.oi_cache:
            previous_data = self.oi_cache[symbol]
            previous_oi = previous_data['oi']
            
            if previous_oi > 0:
                change_percent = ((current_oi - previous_oi) / previous_oi) * 100
                
                # Вызываем callback если изменение значимое
                if abs(change_percent) >= 0.1:  # Минимальный порог для обработки
                    update_data = {
                        'symbol': symbol,
                        'current_oi': current_oi,
                        'previous_oi': previous_oi,
                        'change_percent': change_percent,
                        'timestamp': timestamp,
                        'source': 'websocket'
                    }
                    
                    # Вызываем callback асинхронно
                    asyncio.create_task(self.on_oi_update(update_data))
        
        # Обновляем кэш
        self.oi_cache[symbol] = {
            'oi': current_oi,
            'timestamp': timestamp
        }
    
    async def update_symbols(self, symbols: List[str]):
        """
        Обновление списка отслеживаемых символов
        
        Args:
            symbols: Новый список символов
        """
        logger.info(f"📝 Updating WebSocket symbols to {len(symbols)} coins...")
        
        self.subscribed_symbols = [s.lower() for s in symbols]
        
        # Переподключаемся с новым списком
        if self.running:
            await self.stop()
            await asyncio.sleep(1)
            await self.start(symbols)
    
    async def stop(self):
        """Остановка WebSocket"""
        logger.info("🛑 Stopping WebSocket...")
        self.running = False
        
        if self.websocket:
            await self.websocket.close()
        
        logger.info("✅ WebSocket stopped")
    
    def get_cached_oi(self, symbol: str) -> Optional[float]:
        """Получение закэшированного значения OI"""
        data = self.oi_cache.get(symbol.upper())
        return data['oi'] if data else None
    
    def is_connected(self) -> bool:
        """Проверка статуса подключения"""
        return self.running and self.websocket is not None
