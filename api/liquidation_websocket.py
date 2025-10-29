import asyncio
import json
import logging
from typing import Callable
import websockets
import ssl

logger = logging.getLogger(__name__)


class LiquidationWebSocket:
    """WebSocket для мониторинга ликвидаций в реальном времени"""
    
    def __init__(self, callback: Callable):
        self.callback = callback
        self.ws_url = "wss://fstream.binance.com/ws"
        self.running = False
        self.max_symbols = 200
        self.max_message_size = 10 * 1024 * 1024
    
    async def connect_binance_liquidations(self, symbols: list):
        """
        Подключение к Binance WebSocket для ликвидаций
        
        Args:
            symbols: Список символов для мониторинга (например, ['btcusdt', 'ethusdt'])
        """
        # Валидация и санитизация символов
        if not symbols:
            raise ValueError("Список символов не может быть пустым")
        
        if len(symbols) > self.max_symbols:
            logger.warning(f"Too many symbols, limiting to {self.max_symbols}")
            symbols = symbols[:self.max_symbols]
        
        validated_symbols = []
        for symbol in symbols:
            if isinstance(symbol, str):
                sanitized = ''.join(c for c in symbol if c.isalnum())
                if sanitized and len(sanitized) <= 20:
                    validated_symbols.append(sanitized.lower())
        
        if not validated_symbols:
            raise ValueError("Нет валидных символов")
        
        # Формируем streams для всех символов
        streams = [f"{symbol}@forceOrder" for symbol in validated_symbols]
        subscribe_message = {
            "method": "SUBSCRIBE",
            "params": streams,
            "id": 1
        }
        
        self.running = True
        
        # SSL контекст
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = True
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        
        while self.running:
            try:
                async with websockets.connect(
                    self.ws_url,
                    ssl=ssl_context,
                    max_size=self.max_message_size,
                    ping_interval=20,
                    ping_timeout=10
                ) as websocket:
                    # Подписываемся на streams
                    await websocket.send(json.dumps(subscribe_message))
                    logger.info(f"Subscribed to {len(symbols)} liquidation streams")
                    
                    # Слушаем события
                    while self.running:
                        message = await websocket.recv()
                        data = json.loads(message)
                        
                        # Обрабатываем ликвидацию
                        if 'o' in data:
                            liquidation = self._parse_binance_liquidation(data['o'])
                            await self.callback(liquidation)
                        
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket connection closed, reconnecting...")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await asyncio.sleep(5)
    
    def _parse_binance_liquidation(self, order_data: dict) -> dict:
        """Парсинг данных ликвидации"""
        try:
            # Проверка наличия обязательных полей
            required_fields = ['s', 'S', 'p', 'q', 'T']
            if not all(field in order_data for field in required_fields):
                logger.warning(f"Missing required fields in liquidation data: {order_data.keys()}")
                return {}
            
            # Валидация полей
            symbol = str(order_data['s']).upper()
            symbol = ''.join(c for c in symbol if c.isalnum())
            
            if not symbol:
                raise ValueError("Invalid symbol")
            
            side_raw = str(order_data['S'])
            side = 'long' if side_raw == 'SELL' else 'short'
            
            price = float(order_data['p'])
            quantity = float(order_data['q'])
            
            # Валидация разумности значений
            if price <= 0 or price > 1e10:
                raise ValueError(f"Price out of range: {price}")
            if quantity <= 0 or quantity > 1e10:
                raise ValueError(f"Quantity out of range: {quantity}")
            
            volume = price * quantity
            timestamp = int(order_data['T'])
            
            return {
                'symbol': symbol,
                'side': side,
                'price': price,
                'quantity': quantity,
                'volume': volume,
                'timestamp': timestamp
            }
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Error parsing liquidation data: {e}")
            return {}
    
    def stop(self):
        """Остановка WebSocket"""
        self.running = False
