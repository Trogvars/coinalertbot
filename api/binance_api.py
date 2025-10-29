import hmac
import hashlib
import time
import aiohttp
import asyncio
import logging
from typing import Dict, List, Optional
from urllib.parse import urlencode

from config import config

logger = logging.getLogger(__name__)


class BinanceAPI:
    """API клиент для Binance Futures"""
    
    def __init__(self):
        self.api_key = config.BINANCE_API_KEY
        self.secret_key = config.BINANCE_SECRET_KEY
        self.base_url = config.BINANCE_BASE_URL
        self.session: Optional[aiohttp.ClientSession] = None
        self._available_symbols_cache: Optional[set] = None  # ← ДОБАВИТЬ
    
    async def __aenter__(self):
        headers = {
            'X-MBX-APIKEY': self.api_key
        }
        self.session = aiohttp.ClientSession(headers=headers)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _generate_signature(self, params: dict) -> str:
        """Генерация подписи для приватных эндпоинтов"""
        query_string = urlencode(params)
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    async def get_open_interest(self, symbol: str) -> Optional[float]:
        """Получение Open Interest для символа"""
        url = f"{self.base_url}/fapi/v1/openInterest"
        params = {'symbol': symbol}
        
        try:
            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    return float(data.get('openInterest', 0))
                else:
                    logger.warning(f"Failed to get OI for {symbol}: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error getting OI for {symbol}: {e}")
            return None
    
    async def get_all_open_interest(self) -> List[Dict]:
        """Получение Open Interest для всех символов"""
        # Получаем список всех торговых пар
        exchange_info = await self.get_exchange_info()
        if not exchange_info:
            return []
        
        results = []
        for symbol_info in exchange_info:
            symbol = symbol_info['symbol']
            if symbol.endswith('USDT'):  # Только USDT пары
                oi = await self.get_open_interest(symbol)
                if oi:
                    results.append({
                        'symbol': symbol,
                        'open_interest': oi
                    })
                    # Небольшая задержка для соблюдения rate limit
                    await asyncio.sleep(0.05)
        
        return results
    
    async def get_exchange_info(self) -> List[Dict]:
        """Получение информации о торговых парах"""
        url = f"{self.base_url}/fapi/v1/exchangeInfo"
        
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('symbols', [])
                return []
        except Exception as e:
            logger.error(f"Error getting exchange info: {e}")
            return []
    
    async def get_liquidations(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Получение данных о ликвидациях"""
        url = f"{self.base_url}/fapi/v1/allForceOrders"
        params = {
            'symbol': symbol,
            'limit': limit
        }
        
        try:
            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    return await response.json()
                return []
        except Exception as e:
            logger.error(f"Error getting liquidations for {symbol}: {e}")
            return []
    
    async def get_24h_ticker(self, symbol: str) -> Optional[Dict]:
        """Получение 24h статистики"""
        url = f"{self.base_url}/fapi/v1/ticker/24hr"
        params = {'symbol': symbol}
        
        try:
            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    return await response.json()
                return None
        except Exception as e:
            logger.error(f"Error getting 24h ticker for {symbol}: {e}")
            return None
    
    async def get_klines(self, symbol: str, interval: str = '1h', limit: int = 100) -> List[List]:
        """Получение свечей (klines)"""
        url = f"{self.base_url}/fapi/v1/klines"
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        try:
            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    return await response.json()
                return []
        except Exception as e:
            logger.error(f"Error getting klines for {symbol}: {e}")
            return []


    async def get_available_symbols(self, force_refresh: bool = False) -> set:
        """
        Получение списка доступных USDT символов на Binance Futures
        С кэшированием для избежания повторных запросов
        """
        # Проверяем кэш
        if self._available_symbols_cache and not force_refresh:
            return self._available_symbols_cache
        
        try:
            exchange_info = await self.get_exchange_info()
            
            # Фильтруем только активные USDT пары
            available = set()
            for symbol_info in exchange_info:
                symbol = symbol_info['symbol']
                status = symbol_info.get('status', '')
                
                # Только активные USDT пары
                if symbol.endswith('USDT') and status == 'TRADING':
                    available.add(symbol)
            
            # Кэшируем результат
            self._available_symbols_cache = available
            logger.info(f"Cached {len(available)} available Binance symbols")
            
            return available
            
        except Exception as e:
            logger.error(f"Error getting available symbols: {e}")
            return set()
    
    async def is_symbol_available(self, symbol: str) -> bool:
        """
        Проверка доступности символа на Binance Futures
        
        Args:
            symbol: Символ для проверки (например, 'BTCUSDT')
        
        Returns:
            True если символ доступен, False иначе
        """
        available_symbols = await self.get_available_symbols()
        return symbol in available_symbols
