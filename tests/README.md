# Тесты для Crypto Alert Bot

## Запуск тестов

### Запуск всех тестов
```bash
pytest
```

### Запуск конкретного файла
```bash
pytest tests/test_security.py
```

### Запуск конкретного теста
```bash
pytest tests/test_security.py::TestInputValidator::test_validate_number_valid
```

### Запуск с покрытием кода
```bash
pytest --cov=. --cov-report=html
```

### Запуск тестов по маркерам
```bash
# Только тесты безопасности
pytest -m security

# Только тесты WebSocket
pytest -m websocket

# Исключить медленные тесты
pytest -m "not slow"
```

## Структура тестов

- `test_security.py` - Тесты модуля безопасности и валидации
- `test_database.py` - Тесты базы данных
- `test_websocket.py` - Тесты WebSocket подключений
- `test_api.py` - Тесты API клиентов (если добавлены)

## Покрытие кода

После запуска тестов с `--cov-report=html` откройте `htmlcov/index.html` в браузере для просмотра детального покрытия.

## CI/CD

Тесты автоматически запускаются при:
- Push в main ветку
- Pull requests
- Перед деплоем

## Добавление новых тестов

1. Создайте файл `test_<module>.py` в директории `tests/`
2. Используйте pytest фикстуры для setup/teardown
3. Добавьте маркеры для категоризации: `@pytest.mark.security`
4. Следуйте именованию: `test_<feature>_<scenario>`
