import aiosqlite
import logging
from typing import Optional, List, Dict
from datetime import datetime
import json

from .models import User, Alert, OpenInterestHistory, CMCCache, DEFAULT_USER_SETTINGS
from config.settings import config

logger = logging.getLogger(__name__)


class Database:
    """Асинхронная работа с базой данных SQLite"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.DB_PATH
        self.connection: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Подключение к БД с оптимизацией"""
        self.connection = await aiosqlite.connect(self.db_path)

        # Оптимизация SQLite
        await self.connection.execute('PRAGMA journal_mode=WAL')
        await self.connection.execute('PRAGMA synchronous=NORMAL')
        await self.connection.execute('PRAGMA cache_size=10000')
        await self.connection.execute('PRAGMA temp_store=MEMORY')

        logger.info(f"Connected to database: {self.db_path}")

    async def close(self):
        """Закрытие соединения"""
        if self.connection:
            await self.connection.close()
            logger.info("Database connection closed")

    async def init_db(self):
        """Инициализация таблиц"""
        await self.connect()

        # Таблица пользователей
        await self.connection.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                chat_id INTEGER NOT NULL,
                settings TEXT NOT NULL,
                created_at TEXT NOT NULL,
                is_monitoring INTEGER DEFAULT 0
            )
        ''')

        # Таблица алертов
        await self.connection.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                alert_type TEXT NOT NULL,
                symbol TEXT NOT NULL,
                message TEXT NOT NULL,
                value REAL NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')

        # Индекс для быстрого поиска алертов по пользователю
        await self.connection.execute('''
            CREATE INDEX IF NOT EXISTS idx_alerts_user_id
            ON alerts(user_id, created_at DESC)
        ''')

        # История Open Interest
        await self.connection.execute('''
            CREATE TABLE IF NOT EXISTS open_interest_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                open_interest REAL NOT NULL,
                timestamp TEXT NOT NULL,
                exchange TEXT DEFAULT 'binance'
            )
        ''')

        # Индекс для быстрого поиска по символу
        await self.connection.execute('''
            CREATE INDEX IF NOT EXISTS idx_oi_symbol_timestamp
            ON open_interest_history(symbol, timestamp DESC)
        ''')

        # Кэш CoinMarketCap
        await self.connection.execute('''
            CREATE TABLE IF NOT EXISTS cmc_cache (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                data_json TEXT NOT NULL,
                last_updated TEXT NOT NULL
            )
        ''')

        await self.connection.commit()
        logger.info("Database initialized successfully")

    # ===== USER OPERATIONS =====

    async def create_user(self, user_id: int, chat_id: int) -> User:
        """Создание нового пользователя"""
        user = User(
            user_id=user_id,
            chat_id=chat_id,
            settings=DEFAULT_USER_SETTINGS.copy(),
            created_at=datetime.now()
        )

        await self.connection.execute('''
            INSERT OR REPLACE INTO users (user_id, chat_id, settings, created_at, is_monitoring)
            VALUES (?, ?, ?, ?, ?)
        ''', (user.user_id, user.chat_id, json.dumps(user.settings),
              user.created_at.isoformat(), int(user.is_monitoring)))

        await self.connection.commit()
        logger.info(f"Created user: {user_id}")
        return user

    async def get_user(self, user_id: int) -> Optional[User]:
        """Получение пользователя"""
        async with self.connection.execute(
            'SELECT * FROM users WHERE user_id = ?', (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return User.from_dict({
                    'user_id': row[0],
                    'chat_id': row[1],
                    'settings': row[2],
                    'created_at': row[3],
                    'is_monitoring': row[4]
                })
        return None

    async def update_user_settings(self, user_id: int, settings: dict):
        """Обновление настроек пользователя"""
        await self.connection.execute('''
            UPDATE users SET settings = ? WHERE user_id = ?
        ''', (json.dumps(settings), user_id))
        await self.connection.commit()
        logger.info(f"Updated settings for user: {user_id}")

    async def set_monitoring_status(self, user_id: int, status: bool):
        """Установка статуса мониторинга"""
        await self.connection.execute('''
            UPDATE users SET is_monitoring = ? WHERE user_id = ?
        ''', (int(status), user_id))
        await self.connection.commit()

    async def get_monitoring_users(self) -> List[User]:
        """Получение всех пользователей с активным мониторингом"""
        users = []
        async with self.connection.execute(
            'SELECT * FROM users WHERE is_monitoring = 1'
        ) as cursor:
            async for row in cursor:
                users.append(User.from_dict({
                    'user_id': row[0],
                    'chat_id': row[1],
                    'settings': row[2],
                    'created_at': row[3],
                    'is_monitoring': row[4]
                }))
        return users

    # ===== ALERT OPERATIONS =====

    async def create_alert(self, alert: Alert):
        """Создание алерта"""
        await self.connection.execute('''
            INSERT INTO alerts (user_id, alert_type, symbol, message, value, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (alert.user_id, alert.alert_type, alert.symbol,
              alert.message, alert.value, alert.created_at.isoformat()))
        await self.connection.commit()

    async def get_user_alerts(self, user_id: int, limit: int = 50) -> List[Alert]:
        """Получение алертов пользователя"""
        alerts = []
        async with self.connection.execute('''
            SELECT * FROM alerts WHERE user_id = ?
            ORDER BY created_at DESC LIMIT ?
        ''', (user_id, limit)) as cursor:
            async for row in cursor:
                alerts.append(Alert(
                    id=row[0],
                    user_id=row[1],
                    alert_type=row[2],
                    symbol=row[3],
                    message=row[4],
                    value=row[5],
                    created_at=datetime.fromisoformat(row[6])
                ))
        return alerts

    # ===== OPEN INTEREST OPERATIONS =====

    async def save_oi_history(self, oi: OpenInterestHistory):
        """Сохранение истории OI"""
        await self.connection.execute('''
            INSERT INTO open_interest_history (symbol, open_interest, timestamp, exchange)
            VALUES (?, ?, ?, ?)
        ''', (oi.symbol, oi.open_interest, oi.timestamp.isoformat(), oi.exchange))
        await self.connection.commit()

    async def get_latest_oi(self, symbol: str, exchange: str, minutes_ago: int = 0):
        """
        Получить OI за определенный период назад
        
        Args:
            symbol: Символ монеты
            exchange: Биржа
            minutes_ago: За сколько минут назад (0 = последний, 15, 30, 60)
        
        Returns:
            OpenInterestHistory или None
        """
        async with aiosqlite.connect(self.db_path) as db:
            if minutes_ago == 0:
                # Получаем самое последнее значение
                cursor = await db.execute('''
                    SELECT symbol, open_interest, timestamp, exchange
                    FROM open_interest_history
                    WHERE symbol = ? AND exchange = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                ''', (symbol, exchange))
            else:
                # Получаем значение N минут назад (с допуском ±2 минуты)
                cursor = await db.execute('''
                    SELECT symbol, open_interest, timestamp, exchange
                    FROM open_interest_history
                    WHERE symbol = ? AND exchange = ?
                    AND timestamp BETWEEN
                        datetime('now', '-' || ? || ' minutes', '-2 minutes')
                        AND datetime('now', '-' || ? || ' minutes', '+2 minutes')
                    ORDER BY ABS(
                        strftime('%s', timestamp) - strftime('%s', datetime('now', '-' || ? || ' minutes'))
                    )
                    LIMIT 1
                ''', (symbol, exchange, minutes_ago, minutes_ago, minutes_ago))
            
            row = await cursor.fetchone()
            
            if row:
                return OpenInterestHistory(
                    symbol=row[0],
                    open_interest=row[1],
                    timestamp=datetime.fromisoformat(row[2]),
                    exchange=row[3]
                )
            return None

    # ===== CMC CACHE OPERATIONS =====

    async def get_cmc_cache(self) -> Optional[CMCCache]:
        """Получение кэша CMC"""
        async with self.connection.execute(
            'SELECT * FROM cmc_cache WHERE id = 1'
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return CMCCache.from_dict({
                    'id': row[0],
                    'data_json': row[1],
                    'last_updated': row[2]
                })
        return None

    async def update_cmc_cache(self, data: Dict):
        """Обновление кэша CoinMarketCap"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO cmc_cache (id, data_json, last_updated)
                VALUES (1, ?, ?)
            ''', (json.dumps(data), datetime.now().isoformat()))
            await db.commit()
        
        logger.debug("CMC cache updated")

    async def is_cache_fresh(self, ttl: int = 3600) -> bool:
        """Проверка свежести кэша"""
        cache = await self.get_cmc_cache()
        if not cache:
            return False

        age = (datetime.now() - cache.last_updated).total_seconds()
        return age < ttl
