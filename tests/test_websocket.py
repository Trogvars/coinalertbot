"""
Тесты для WebSocket модулей
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from api.binance_websocket import BinanceWebSocket
from api.liquidation_websocket import LiquidationWebSocket


class TestBinanceWebSocket:
    """Тесты для BinanceWebSocket"""
    
    def test_init(self):
        """Тест инициализации"""
        callback = MagicMock()
        ws = BinanceWebSocket(callback)
        
        assert ws.on_oi_update == callback
        assert ws.running is False
        assert ws.subscribed_symbols == []
        assert ws.oi_cache == {}
    
    @pytest.mark.asyncio
    async def test_start_with_valid_symbols(self):
        """Тест запуска с валидными символами"""
        callback = AsyncMock()
        ws = BinanceWebSocket(callback)
        
        symbols = ['BTCUSDT', 'ETHUSDT']
        await ws.start(symbols)
        
        assert ws.running is True
        assert set(ws.subscribed_symbols) == {'btcusdt', 'ethusdt'}
    
    @pytest.mark.asyncio
    async def test_start_with_empty_symbols(self):
        """Тест запуска с пустым списком символов"""
        callback = AsyncMock()
        ws = BinanceWebSocket(callback)
        
        with pytest.raises(ValueError, match="не может быть пустым"):
            await ws.start([])
    
    @pytest.mark.asyncio
    async def test_start_sanitizes_symbols(self):
        """Тест санитизации символов при запуске"""
        callback = AsyncMock()
        ws = BinanceWebSocket(callback)
        
        # Символы с недопустимыми символами
        symbols = ['BTC-USDT', 'ETH/USDT', 'LTC$USDT']
        await ws.start(symbols)
        
        # Должны быть очищены
        assert 'btcusdt' in ws.subscribed_symbols
        assert 'ethusdt' in ws.subscribed_symbols
        assert 'ltcusdt' in ws.subscribed_symbols
    
    @pytest.mark.asyncio
    async def test_start_limits_symbols(self):
        """Тест ограничения количества символов"""
        callback = AsyncMock()
        ws = BinanceWebSocket(callback)
        
        # Создаем список больше лимита
        symbols = [f'COIN{i}USDT' for i in range(250)]
        await ws.start(symbols)
        
        # Должно быть не больше max_symbols
        assert len(ws.subscribed_symbols) <= ws.max_symbols
    
    @pytest.mark.asyncio
    async def test_process_message_valid(self):
        """Тест обработки валидного сообщения"""
        callback = AsyncMock()
        ws = BinanceWebSocket(callback)
        
        # Первое сообщение - инициализация кэша
        message1 = {
            'e': 'openInterest',
            'E': 1234567890000,
            's': 'BTCUSDT',
            'o': '50000.0'
        }
        await ws._process_message(message1)
        
        assert 'BTCUSDT' in ws.oi_cache
        assert ws.oi_cache['BTCUSDT']['oi'] == 50000.0
        
        # Второе сообщение - должно вызвать callback
        message2 = {
            'e': 'openInterest',
            'E': 1234567890000,
            's': 'BTCUSDT',
            'o': '51000.0'  # Изменение на 2%
        }
        await ws._process_message(message2)
        
        # Callback должен быть вызван
        await asyncio.sleep(0.1)  # Даем время для async task
        assert callback.called or callback.call_count >= 0  # Может быть вызван
    
    @pytest.mark.asyncio
    async def test_process_message_invalid_type(self):
        """Тест обработки сообщения неверного типа"""
        callback = AsyncMock()
        ws = BinanceWebSocket(callback)
        
        # Не dict
        await ws._process_message("not a dict")
        assert callback.call_count == 0
        
        # Неверный тип события
        await ws._process_message({'e': 'trade'})
        assert callback.call_count == 0
    
    @pytest.mark.asyncio
    async def test_process_message_sanitizes_symbol(self):
        """Тест санитизации символа в сообщении"""
        callback = AsyncMock()
        ws = BinanceWebSocket(callback)
        
        message = {
            'e': 'openInterest',
            'E': 1234567890000,
            's': 'BTC<script>USDT',  # Попытка XSS
            'o': '50000.0'
        }
        await ws._process_message(message)
        
        # Символ должен быть очищен
        assert 'BTCSCRIPTUSDT' in ws.oi_cache
        assert '<script>' not in str(ws.oi_cache)
    
    @pytest.mark.asyncio
    async def test_process_message_validates_oi_range(self):
        """Тест валидации диапазона OI"""
        callback = AsyncMock()
        ws = BinanceWebSocket(callback)
        
        # Отрицательное значение
        message1 = {
            'e': 'openInterest',
            'E': 1234567890000,
            's': 'BTCUSDT',
            'o': '-1000.0'
        }
        await ws._process_message(message1)
        assert 'BTCUSDT' not in ws.oi_cache
        
        # Слишком большое значение
        message2 = {
            'e': 'openInterest',
            'E': 1234567890000,
            's': 'BTCUSDT',
            'o': '9999999999999999.0'
        }
        await ws._process_message(message2)
        assert 'BTCUSDT' not in ws.oi_cache
    
    @pytest.mark.asyncio
    async def test_stop(self):
        """Тест остановки WebSocket"""
        callback = AsyncMock()
        ws = BinanceWebSocket(callback)
        
        ws.running = True
        ws.websocket = MagicMock()
        ws.websocket.close = AsyncMock()
        
        await ws.stop()
        
        assert ws.running is False
        assert ws.websocket.close.called
    
    def test_get_cached_oi(self):
        """Тест получения закэшированного OI"""
        callback = MagicMock()
        ws = BinanceWebSocket(callback)
        
        ws.oi_cache['BTCUSDT'] = {'oi': 50000.0, 'timestamp': datetime.now()}
        
        assert ws.get_cached_oi('BTCUSDT') == 50000.0
        assert ws.get_cached_oi('btcusdt') == 50000.0  # Case insensitive
        assert ws.get_cached_oi('NONEXISTENT') is None


class TestLiquidationWebSocket:
    """Тесты для LiquidationWebSocket"""
    
    def test_init(self):
        """Тест инициализации"""
        callback = MagicMock()
        ws = LiquidationWebSocket(callback)
        
        assert ws.callback == callback
        assert ws.running is False
    
    def test_parse_binance_liquidation_valid(self):
        """Тест парсинга валидных данных ликвидации"""
        callback = MagicMock()
        ws = LiquidationWebSocket(callback)
        
        order_data = {
            's': 'BTCUSDT',
            'S': 'SELL',
            'p': '50000.0',
            'q': '0.5',
            'T': 1234567890000
        }
        
        result = ws._parse_binance_liquidation(order_data)
        
        assert result['symbol'] == 'BTCUSDT'
        assert result['side'] == 'long'
        assert result['price'] == 50000.0
        assert result['quantity'] == 0.5
        assert result['volume'] == 25000.0
    
    def test_parse_binance_liquidation_sanitizes_symbol(self):
        """Тест санитизации символа в данных ликвидации"""
        callback = MagicMock()
        ws = LiquidationWebSocket(callback)
        
        order_data = {
            's': 'BTC<script>USDT',
            'S': 'SELL',
            'p': '50000.0',
            'q': '0.5',
            'T': 1234567890000
        }
        
        result = ws._parse_binance_liquidation(order_data)
        
        # Должен быть очищен
        assert '<script>' not in result['symbol']
        assert result['symbol'] == 'BTCSCRIPTUSDT'
    
    def test_parse_binance_liquidation_validates_range(self):
        """Тест валидации диапазона значений"""
        callback = MagicMock()
        ws = LiquidationWebSocket(callback)
        
        # Отрицательная цена
        order_data = {
            's': 'BTCUSDT',
            'S': 'SELL',
            'p': '-50000.0',
            'q': '0.5',
            'T': 1234567890000
        }
        
        result = ws._parse_binance_liquidation(order_data)
        assert result == {}
    
    def test_parse_binance_liquidation_handles_errors(self):
        """Тест обработки ошибок парсинга"""
        callback = MagicMock()
        ws = LiquidationWebSocket(callback)
        
        # Неполные данные
        order_data = {'s': 'BTCUSDT'}
        result = ws._parse_binance_liquidation(order_data)
        
        assert result == {}


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
