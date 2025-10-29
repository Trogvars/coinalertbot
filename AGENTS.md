# Agent Guidelines for Crypto Alert Bot

## Build/Lint/Test Commands
- **Run bot**: `python main.py` or `./start_bot.sh`
- **Run single test**: `python test_project.py` (no pytest config found - tests are standalone scripts)
- **Test specific modules**: `python test_coinglass.py`, `python test_liquidations.py`
- **Install deps**: `pip install -r requirements.txt`

## Code Style
- **Language**: Python 3.11+, async/await throughout
- **Imports**: Standard libs first, third-party second, local imports last (from config/database/services/utils)
- **Formatting**: 4 spaces (no tabs), snake_case for functions/variables, PascalCase for classes
- **Types**: Use type hints (Optional, Dict, List from typing), dataclasses for models
- **Docstrings**: Russian comments/docstrings (project convention), describe Args/Returns for public methods
- **Error handling**: Try/except with logging via `logger.error()`, return None/empty on API failures
- **Logging**: Get logger via `logging.getLogger(__name__)`, log levels: INFO for operations, ERROR for failures
- **Async patterns**: Use `async with` for sessions, `asyncio.sleep()` for delays, context managers for resources
- **Database**: All DB operations are async via aiosqlite, use Database class methods
- **Config**: Access via `config.SETTING_NAME` from config module, validate in Config.validate()
- **Services**: Dependency injection pattern - pass bot, db, services to constructors
- **Naming**: Russian in user-facing strings, English for code/variables/functions

## Architecture
- Telegram bot using aiogram 3.13+, WebSocket + REST API monitoring, SQLite with aiosqlite
- Services: AlertService (sends alerts), MonitoringService (detects OI changes), CacheService (CMC data)
- API clients: BinanceAPI, BybitAPI (async context managers with sessions)
