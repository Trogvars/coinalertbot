import websockets
import json
import asyncio
import logging
from typing import Callable, Dict, List, Optional
from datetime import datetime
import ssl

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
        self.max_symbols = 200  # Binance WebSocket limit
        self.max_message_size = 10 * 1024 * 1024  # 10MB max message size
    
    async def start(self, symbols: List[str]):
        """
        Запуск WebSocket подключения
        
        Args:
            symbols: Список символов для мониторинга (например, ['BTCUSDT', 'ETHUSDT'])
        """
        # Валидация символов
        if not symbols:
            raise ValueError("Список символов не может быть пустым")
        
        if len(symbols) > self.max_symbols:
            logger.warning(f"Too many symbols ({len(symbols)}), limiting to {self.max_symbols}")
            symbols = symbols[:self.max_symbols]
        
        # Санитизация и валидация символов
        validated_symbols = []
        for symbol in symbols:
            if not isinstance(symbol, str):
                logger.warning(f"Invalid symbol type: {type(symbol)}")
                continue
            # Разрешаем только буквы и цифры
            sanitized = ''.join(c for c in symbol.upper() if c.isalnum())
            if sanitized and len(sanitized) <= 20:  # Разумная длина символа
                validated_symbols.append(sanitized.lower())
        
        if not validated_symbols:
            raise ValueError("Нет валидных символов для подписки")
        
        self.subscribed_symbols = validated_symbols
        self.running = True
        
        logger.info(f"📡 Starting WebSocket for {len(validated_symbols)} symbols...")
        
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
        
        # SSL контекст для безопасного подключения
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = True
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        
        async with websockets.connect(
            ws_url, 
            ping_interval=20, 
            ping_timeout=10,
            ssl=ssl_context,
            max_size=self.max_message_size,
            close_timeout=10
        ) as websocket:
            self.websocket = websocket
            self.reconnect_delay = 5  # Сбрасываем задержку при успешном подключении
            
            logger.info(f"✅ WebSocket connected! Listening for OI updates...")
            
            # Прослушиваем сообщения
            async for message in websocket:
                if not self.running:
                    break
                
                # Проверка размера сообщения
                if len(message) > self.max_message_size:
                    logger.warning(f"Message too large ({len(message)} bytes), skipping")
                    continue
                
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
        # Валидация типа данных
        if not isinstance(data, dict):
            logger.warning(f"Invalid data type: {type(data)}")
            return
        
        if data.get('e') != 'openInterest':
            return
        
        # Валидация и санитизация полей
        try:
            symbol = str(data.get('s', '')).upper()
            # Санитизация символа - только буквы и цифры
            symbol = ''.join(c for c in symbol if c.isalnum())
            
            if not symbol or len(symbol) > 20:
                logger.warning(f"Invalid symbol: {data.get('s')}")
                return
            
            # Валидация OI
            oi_value = data.get('o', 0)
            if not isinstance(oi_value, (int, float, str)):
                logger.warning(f"Invalid OI value type: {type(oi_value)}")
                return
            
            current_oi = float(oi_value)
            if current_oi < 0 or current_oi > 1e15:  # Разумный лимит
                logger.warning(f"OI value out of range: {current_oi}")
                return
            
            # Валидация timestamp
            timestamp_ms = data.get('E', 0)
            if not isinstance(timestamp_ms, (int, float)) or timestamp_ms < 0:
                logger.warning(f"Invalid timestamp: {timestamp_ms}")
                return
            
            timestamp = datetime.fromtimestamp(timestamp_ms / 1000)
            
        except (ValueError, TypeError, OverflowError) as e:
            logger.error(f"Error parsing message data: {e}")
            return
        
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
