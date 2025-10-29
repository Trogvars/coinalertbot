# Bug Fix: Telegram HTML Parsing Error

## Error Description
```
TelegramBadRequest: Telegram server says - Bad Request: can't parse entities: 
Unsupported start tag "" at byte offset 334
```

## Root Cause
Unescaped HTML special characters (`<` and `>`) in Telegram messages sent with `parse_mode='HTML'`.

Telegram's HTML parser interprets `<` as the start of an HTML tag. When it's not a valid tag, the parsing fails.

## Files Fixed

### 1. bot/handlers/start.py (Line 213)
**Before:**
```python
"• Задержка < 3 секунды ⚡\n"
```

**After:**
```python
"• Задержка &lt; 3 секунды ⚡\n"
```

### 2. bot/handlers/monitoring.py (Line 184)
**Before:**
```python
liq_text += "<i>Проверяются только крупные позиции (>$10k)</i>"
```

**After:**
```python
liq_text += "<i>Проверяются только крупные позиции (&gt;$10k)</i>"
```

### 3. bot/handlers/settings.py (Line 146)
**Before:**
```python
"Например: 15 (для алертов при изменении >15%)\n\n"
```

**After:**
```python
"Например: 15 (для алертов при изменении &gt;15%)\n\n"
```

### 4. bot/handlers/settings.py (Line 305)
**Before:**
```python
await message.answer("❌ Введите число >= 60")
```

**After:**
```python
await message.answer("❌ Введите число &gt;= 60")
```

## HTML Entity Reference

When using `parse_mode='HTML'` in Telegram, always escape these characters:

| Character | HTML Entity | Usage |
|-----------|-------------|-------|
| `<`       | `&lt;`      | Less than |
| `>`       | `&gt;`      | Greater than |
| `&`       | `&amp;`     | Ampersand |
| `"`       | `&quot;`    | Quote |

## Allowed Telegram HTML Tags

Only these tags are allowed and should NOT be escaped:
- `<b>text</b>` - Bold
- `<i>text</i>` - Italic
- `<code>text</code>` - Monospace
- `<pre>text</pre>` - Preformatted
- `<a href="url">text</a>` - Link
- `<u>text</u>` - Underline
- `<s>text</s>` - Strikethrough
- `<tg-spoiler>text</tg-spoiler>` - Spoiler

## Prevention - New Utility Module

Created `utils/html.py` with helper functions:

### escape_html()
```python
from utils.html import escape_html

text = escape_html("Price < $100 and > $50")
# Result: "Price &lt; $100 and &gt; $50"
```

### safe_format()
```python
from utils.html import safe_format

message = safe_format(
    "Price: {price}, Volume: {volume}",
    price="< $100",
    volume="> 1M"
)
# Result: "Price: &lt; $100, Volume: &gt; 1M"
```

### check_html_safety()
```python
from utils.html import check_html_safety

safe, issues = check_html_safety("Price < $100")
if not safe:
    print(f"Issues found: {issues}")
```

## Testing

To test if HTML is valid for Telegram:
1. Use `check_html_safety()` before sending
2. Send test messages to yourself first
3. Watch for TelegramBadRequest exceptions in logs

## Best Practices

1. **Always escape user input** before including in HTML messages
2. **Use the utility functions** from `utils/html.py`
3. **Test messages** with special characters
4. **Watch logs** for parsing errors
5. **Consider using Markdown** instead of HTML if you don't need complex formatting

## Impact

✅ **Fixed**: All Telegram HTML parsing errors
✅ **Prevented**: Future similar errors with utility module
✅ **Improved**: Code safety and maintainability

## Related Files

- `bot/handlers/start.py` - Mode selection menu
- `bot/handlers/monitoring.py` - Liquidations display
- `bot/handlers/settings.py` - Settings prompts
- `utils/html.py` - New utility module
