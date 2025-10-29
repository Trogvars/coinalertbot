"""
Утилиты для безопасной работы с HTML в Telegram сообщениях
"""
import re
from typing import Any


def escape_html(text: str) -> str:
    """
    Экранирует HTML специальные символы для безопасной отправки в Telegram
    
    Args:
        text: Текст для экранирования
    
    Returns:
        Экранированный текст
    
    Examples:
        >>> escape_html("Price < $100")
        'Price &lt; $100'
        >>> escape_html("Volume > 1M")
        'Volume &gt; 1M'
    """
    if not isinstance(text, str):
        text = str(text)
    
    replacements = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    return text


def safe_format(template: str, **kwargs: Any) -> str:
    """
    Безопасное форматирование строк с автоматическим экранированием
    
    Args:
        template: Шаблон с placeholder'ами
        **kwargs: Значения для подстановки
    
    Returns:
        Отформатированная и экранированная строка
    
    Examples:
        >>> safe_format("Price: {price}", price="< $100")
        'Price: &lt; $100'
    """
    # Экранируем все значения
    escaped_kwargs = {
        key: escape_html(str(value)) if not isinstance(value, (int, float)) else value
        for key, value in kwargs.items()
    }
    
    return template.format(**escaped_kwargs)


def preserve_telegram_tags(text: str) -> str:
    """
    Экранирует HTML, но сохраняет разрешенные Telegram теги
    
    Разрешенные теги: <b>, <i>, <code>, <pre>, <a>, <u>, <s>, <tg-spoiler>
    
    Args:
        text: Текст для обработки
    
    Returns:
        Текст с экранированными символами, кроме разрешенных тегов
    """
    # Сначала сохраняем разрешенные теги
    allowed_tags = [
        'b', 'i', 'code', 'pre', 'a', 'u', 's', 'tg-spoiler',
        'strong', 'em'
    ]
    
    # Создаем временные маркеры для разрешенных тегов
    placeholders = {}
    counter = 0
    
    for tag in allowed_tags:
        # Находим открывающие теги
        pattern_open = f'<{tag}[^>]*>'
        for match in re.finditer(pattern_open, text):
            placeholder = f'___PLACEHOLDER_{counter}___'
            placeholders[placeholder] = match.group()
            text = text.replace(match.group(), placeholder, 1)
            counter += 1
        
        # Находим закрывающие теги
        pattern_close = f'</{tag}>'
        for match in re.finditer(pattern_close, text):
            placeholder = f'___PLACEHOLDER_{counter}___'
            placeholders[placeholder] = match.group()
            text = text.replace(match.group(), placeholder, 1)
            counter += 1
    
    # Экранируем весь текст
    text = escape_html(text)
    
    # Возвращаем разрешенные теги
    for placeholder, original in placeholders.items():
        text = text.replace(placeholder, original)
    
    return text


def check_html_safety(text: str) -> tuple[bool, list[str]]:
    """
    Проверяет текст на безопасность для отправки в Telegram
    
    Args:
        text: Текст для проверки
    
    Returns:
        Кортеж (безопасен, список_проблем)
    
    Examples:
        >>> check_html_safety("Price < $100")
        (False, ['Unescaped < at position 6'])
    """
    issues = []
    
    # Проверяем на неэкранированные < и >
    for i, char in enumerate(text):
        if char == '<':
            # Проверяем, является ли это разрешенным тегом
            remaining = text[i:]
            if not re.match(r'</?(?:b|i|code|pre|a|u|s|strong|em|tg-spoiler)[>\s]', remaining):
                issues.append(f"Unescaped < at position {i}")
        elif char == '>':
            # Проверяем контекст
            if i > 0 and text[i-1] not in ['&', ';']:
                # Это может быть часть тега, проверяем
                if not re.search(r'<[^>]+>$', text[:i+1].split()[-1] if text[:i+1].split() else ''):
                    issues.append(f"Potentially unescaped > at position {i}")
    
    return (len(issues) == 0, issues)
