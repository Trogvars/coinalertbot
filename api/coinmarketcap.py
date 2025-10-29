import aiohttp
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime

from config import config

logger = logging.getLogger(__name__)


class CoinMarketCapAPI:
    """API клиент для CoinMarketCap"""
    
    def __init__(self):
        self.api_key = config.COINMARKETCAP_API_KEY
        self.base_url = config.COINMARKETCAP_BASE_URL
        self.headers = {
            'Accepts': 'application/json',
            'X-CMC_PRO_API_KEY': self.api_key,
        }
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_listings(self, limit: int = 200) -> List[Dict]:
        """Получение списка криптовалют"""
        url = f"{self.base_url}/cryptocurrency/listings/latest"
        params = {
            'limit': limit,
            'sort': 'market_cap',
            'convert': 'USD'
        }
        
        try:
            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Fetched {len(data['data'])} coins from CMC")
                    return data['data']
                else:
                    error_text = await response.text()
                    logger.error(f"CMC API error: {response.status} - {error_text}")
                    return []
        except asyncio.TimeoutError:
            logger.error("CMC API timeout")
            return []
        except Exception as e:
            logger.error(f"CMC API exception: {e}")
            return []
    
    async def get_coin_info(self, symbol: str) -> Optional[Dict]:
        """Получение информации о конкретной монете"""
        url = f"{self.base_url}/cryptocurrency/quotes/latest"
        params = {
            'symbol': symbol,
            'convert': 'USD'
        }
        
        try:
            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    data = await response.json()
                    return data['data'].get(symbol)
                else:
                    logger.error(f"Failed to get info for {symbol}")
                    return None
        except Exception as e:
            logger.error(f"Error getting coin info: {e}")
            return None
    
    async def get_market_data(self, symbols: List[str]) -> Dict[str, Dict]:
        """Получение рыночных данных для списка символов"""
        url = f"{self.base_url}/cryptocurrency/quotes/latest"
        params = {
            'symbol': ','.join(symbols[:100]),  # Максимум 100 символов за раз
            'convert': 'USD'
        }
        
        try:
            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    data = await response.json()
                    return data['data']
                return {}
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return {}
