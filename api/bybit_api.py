import hmac
import hashlib
import time
import aiohttp
import asyncio
import logging
from typing import Dict, List, Optional
import json

from config import config

logger = logging.getLogger(__name__)


class BybitAPI:
    """API клиент для Bybit"""
    
    def __init__(self):
        self.api_key = config.BYBIT_API_KEY
        self.secret_key = config.BYBIT_SECRET_KEY
        self.base_url = config.BYBIT_BASE_URL
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _generate_signature(self, params: dict) -> str:
        """Генерация подписи для Bybit API"""
        param_str = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            param_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    async def get_open_interest(self, symbol: str) -> Optional[float]:
        """Получение Open Interest"""
        url = f"{self.base_url}/v5/market/open-interest"
        params = {
            'category': 'linear',
            'symbol': symbol,
            'intervalTime': '5min'
        }
        
        try:
            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('retCode') == 0 and data.get('result', {}).get('list'):
                        return float(data['result']['list'][0]['openInterest'])
                    return None
                else:
                    logger.warning(f"Failed to get OI for {symbol} from Bybit: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error getting OI from Bybit for {symbol}: {e}")
            return None
    
    async def get_tickers(self, category: str = 'linear') -> List[Dict]:
        """Получение тикеров"""
        url = f"{self.base_url}/v5/market/tickers"
        params = {'category': category}
        
        try:
            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('retCode') == 0:
                        return data.get('result', {}).get('list', [])
                return []
        except Exception as e:
            logger.error(f"Error getting tickers from Bybit: {e}")
            return []
    
    async def get_kline(self, symbol: str, interval: str = '60', limit: int = 200) -> List[Dict]:
        """Получение свечей (klines)"""
        url = f"{self.base_url}/v5/market/kline"
        params = {
            'category': 'linear',
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        try:
            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('retCode') == 0:
                        return data.get('result', {}).get('list', [])
                return []
        except Exception as e:
            logger.error(f"Error getting klines from Bybit: {e}")
            return []
    
    async def get_liquidations(self, symbol: str, limit: int = 50) -> List[Dict]:
        """
        Получение данных о ликвидациях
        
        Примечание: Bybit не предоставляет публичный API для исторических ликвидаций.
        Для реального использования нужно подключить WebSocket или использовать 
        сторонние сервисы типа Coinglass.
        """
        logger.warning("Bybit liquidations API not available in public endpoint")
        return []
    
    async def get_instruments_info(self, category: str = 'linear') -> List[Dict]:
        """Получение информации об инструментах"""
        url = f"{self.base_url}/v5/market/instruments-info"
        params = {'category': category}
        
        try:
            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('retCode') == 0:
                        return data.get('result', {}).get('list', [])
                return []
        except Exception as e:
            logger.error(f"Error getting instruments info from Bybit: {e}")
            return
