import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from database import Database
from api import CoinMarketCapAPI
from config import config

logger = logging.getLogger(__name__)


class CacheService:
    """Сервис кэширования данных CoinMarketCap"""
    
    def __init__(self, db: Database):
        self.db = db
        self.ttl = config.CACHE_TTL
    
    async def get_coins_data(self, force_refresh: bool = False) -> List[Dict]:
        """
        Получение данных о монетах с кэшированием
        
        Args:
            force_refresh: Принудительное обновление кэша
        
        Returns:
            Список монет с данными
        """
        # Проверяем свежесть кэша
        if not force_refresh and await self.db.is_cache_fresh(self.ttl):
            cache = await self.db.get_cmc_cache()
            if cache:
                logger.info(f"Using cached CMC data (age: {(datetime.now() - cache.last_updated).seconds}s)")
                return cache.data.get('coins', [])
        
        # Кэш устарел или отсутствует, запрашиваем свежие данные
        logger.info("Fetching fresh data from CoinMarketCap")
        coins = await self._fetch_fresh_data()
        
        if coins:
            # Сохраняем в кэш
            await self.db.update_cmc_cache({'coins': coins})
            logger.info(f"Cached {len(coins)} coins from CMC")
        
        return coins
    
    async def _fetch_fresh_data(self) -> List[Dict]:
        """Получение свежих данных из CMC API"""
        try:
            async with CoinMarketCapAPI() as cmc:
                coins = await cmc.get_listings(limit=200)
                return coins
        except Exception as e:
            logger.error(f"Error fetching CMC data: {e}")
            
            # Fallback на кэшированные данные, даже если устарели
            cache = await self.db.get_cmc_cache()
            if cache:
                logger.warning("Using stale cache due to API error")
                return cache.data.get('coins', [])
            
            return []
    
    async def get_coin_by_symbol(self, symbol: str) -> Optional[Dict]:
        """Получение данных о конкретной монете из кэша"""
        coins = await self.get_coins_data()
        
        for coin in coins:
            if coin.get('symbol') == symbol.upper():
                return coin
        
        return None
    
    async def filter_coins(self, filters: Dict) -> List[Dict]:
        """
        Фильтрация монет по заданным критериям
        
        Args:
            filters: Словарь с параметрами фильтрации
                - min_market_cap: Минимальная капитализация
                - min_volume_24h: Минимальный объем за 24ч
                - exclude_top_n: Исключить топ N монет
                - custom_exclusions: Список символов для исключения
        
        Returns:
            Отфильтрованный список монет
        """
        coins = await self.get_coins_data()
        
        if not coins:
            return []
        
        # Применяем фильтры
        filtered = coins.copy()
        
        # Исключаем топ N монет
        exclude_top = filters.get('exclude_top_n', 0)
        if exclude_top > 0:
            filtered = [c for c in filtered if c.get('cmc_rank', 0) > exclude_top]
            logger.debug(f"Excluded top {exclude_top} coins")
        
        # Фильтр по капитализации
        min_cap = filters.get('min_market_cap', 0)
        if min_cap > 0:
            filtered = [
                c for c in filtered 
                if c.get('quote', {}).get('USD', {}).get('market_cap', 0) >= min_cap
            ]
            logger.debug(f"Filtered by market cap >= ${min_cap:,.0f}")
        
        # Фильтр по объему
        min_volume = filters.get('min_volume_24h', 0)
        if min_volume > 0:
            filtered = [
                c for c in filtered 
                if c.get('quote', {}).get('USD', {}).get('volume_24h', 0) >= min_volume
            ]
            logger.debug(f"Filtered by volume >= ${min_volume:,.0f}")
        
        # Пользовательские исключения
        exclusions = filters.get('custom_exclusions', [])
        if exclusions:
            filtered = [c for c in filtered if c.get('symbol') not in exclusions]
            logger.debug(f"Excluded {len(exclusions)} custom symbols")
        
        logger.info(f"Filtered coins: {len(coins)} -> {len(filtered)}")
        return filtered
    
    async def get_cache_status(self) -> Dict:
        """Получение статуса кэша"""
        cache = await self.db.get_cmc_cache()
        
        if not cache:
            return {
                'exists': False,
                'age_seconds': None,
                'is_fresh': False,
                'coins_count': 0
            }
        
        age = (datetime.now() - cache.last_updated).total_seconds()
        
        return {
            'exists': True,
            'last_updated': cache.last_updated.isoformat(),
            'age_seconds': int(age),
            'is_fresh': age < self.ttl,
            'coins_count': len(cache.data.get('coins', []))
        }
