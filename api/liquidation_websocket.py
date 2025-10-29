import asyncio
import json
import logging
from typing import Callable
import websockets

logger = logging.getLogger(__name__)


class LiquidationWebSocket:
    """WebSocket для мониторинга ликвидаций в реальном времени"""
    
    def __init__(self, callback: Callable):
        self.callback = callback
        self.ws_url = "wss://fstream.binance.com/ws"
        self.running = False
    
    async def connect_binance_liquidations(self, symbols: list):
        """
        Подключение к Binance WebSocket для ликвидаций
        
        Args:
            symbols: Список символов для мониторинга (например, ['btcusdt', 'ethusdt'])
        """
        # Формируем streams для всех символов
        streams = [f"{symbol.lower()}@forceOrder" for symbol in symbols]
        subscribe_message = {
            "method": "SUBSCRIBE",
            "params": streams,
            "id": 1
        }
        
        self.running = True
        
        while self.running:
            try:
                async with websockets.connect(self.ws_url) as websocket:
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
        return {
            'symbol': order_data['s'],
            'side': 'long' if order_data['S'] == 'SELL' else 'short',
            'price': float(order_data['p']),
            'quantity': float(order_data['q']),
            'volume': float(order_data['p']) * float(order_data['q']),
            'timestamp': order_data['T']
        }
    
    def stop(self):
        """Остановка WebSocket"""
        self.running = False
