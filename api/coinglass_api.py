import aiohttp
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class CoinglassAPI:
    """
    API клиент для Coinglass - агрегатор данных о ликвидациях
    """
    
    def __init__(self):
        self.base_url = "https://open-api.coinglass.com/public/v2"
        self.session: Optional[aiohttp.ClientSession] = None
        self._is_available = True  # Флаг доступности API
    
    async def __aenter__(self):
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.session = aiohttp.ClientSession(headers=headers)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def is_available(self) -> bool:
        """Проверка доступности API"""
        return self._is_available
    
    async def get_liquidation_history(self, symbol: str = "BTC", time_type: str = "h1") -> Optional[Dict]:
        """
        Получение истории ликвидаций
        
        Args:
            symbol: Символ (BTC, ETH, и т.д.)
            time_type: Временной интервал (m5, m15, m30, h1, h4, h12, h24)
        
        Returns:
            Данные о ликвидациях с разбивкой по лонгам/шортам
        """
        if not self._is_available:
            logger.debug("Coinglass API marked as unavailable, skipping request")
            return None
        
        url = f"{self.base_url}/liquidation"
        params = {
            'symbol': symbol,
            'time_type': time_type
        }
        
        try:
            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('success'):
                        logger.debug(f"Fetched liquidation data for {symbol} ({time_type})")
                        return data.get('data')
                    else:
                        logger.warning(f"Coinglass API returned success=false for {symbol}")
                        return None
                elif response.status == 500:
                    # Отмечаем API как недоступный после первой ошибки 500
                    self._is_available = False
                    logger.warning("Coinglass API returned 500. Marking as unavailable for this session.")
                    return None
                elif response.status == 429:
                    logger.warning("Coinglass API rate limit exceeded")
                    return None
                else:
                    logger.error(f"Coinglass API error: {response.status}")
                    return None
        except asyncio.TimeoutError:
            logger.warning("Coinglass API timeout")
            return None
        except Exception as e:
            logger.error(f"Coinglass API exception: {e}")
            return None
    
    def parse_liquidation_data(self, liq_data: Dict) -> Dict:
        """
        Парсинг данных о ликвидациях в удобный формат
        """
        if not liq_data:
            return {}
        
        try:
            # Coinglass возвращает данные в миллионах USD
            long_liquidations = float(liq_data.get('longLiquidation', 0)) * 1_000_000
            short_liquidations = float(liq_data.get('shortLiquidation', 0)) * 1_000_000
            total = long_liquidations + short_liquidations
            
            return {
                'long_volume': long_liquidations,
                'short_volume': short_liquidations,
                'total_volume': total,
                'long_percentage': (long_liquidations / total * 100) if total > 0 else 0,
                'short_percentage': (short_liquidations / total * 100) if total > 0 else 0,
                'dominance': 'long' if long_liquidations > short_liquidations else 'short',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error parsing liquidation data: {e}")
            return {}
