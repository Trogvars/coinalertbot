import sqlite3
from datetime import datetime

conn = sqlite3.connect('bot.db')
cursor = conn.cursor()

print("=" * 80)
print("РЕАЛЬНЫЕ ИЗМЕНЕНИЯ OPEN INTEREST ЗА ПОСЛЕДНИЕ 10 МИНУТ")
print("=" * 80)

# Ищем монеты с наибольшими изменениями
cursor.execute('''
    WITH ranked_oi AS (
        SELECT 
            symbol,
            open_interest,
            timestamp,
            LAG(open_interest) OVER (PARTITION BY symbol ORDER BY timestamp) as prev_oi,
            ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY timestamp DESC) as rn
        FROM open_interest_history
        WHERE timestamp > datetime('now', '-10 minutes')
    )
    SELECT 
        symbol,
        open_interest as current_oi,
        prev_oi,
        ROUND((open_interest - prev_oi) / prev_oi * 100, 2) as change_percent,
        timestamp
    FROM ranked_oi
    WHERE rn = 1 AND prev_oi IS NOT NULL
    ORDER BY ABS((open_interest - prev_oi) / prev_oi * 100) DESC
    LIMIT 80
''')

results = cursor.fetchall()

if results:
    print(f"\n{'Symbol':<12} {'Current OI':<15} {'Previous OI':<15} {'Change %':<10}")
    print("-" * 80)
    
    for symbol, current, previous, change, timestamp in results:
        emoji = "📈" if change > 0 else "📉"
        print(f"{symbol:<12} {current:<15,.0f} {previous:<15,.0f} {emoji} {change:>+7.2f}%")
    
    print(f"\n✅ Найдено изменений: {len(results)}")
    print(f"📊 Максимальное изменение: {abs(results[0][3]):.2f}%")
else:
    print("\n⚠️ Недостаточно данных для сравнения")
    print("Подождите еще 5-10 минут для накопления истории")

# Проверяем настройки пользователя
cursor.execute('SELECT settings FROM users WHERE user_id = 95166589')
row = cursor.fetchone()

if row:
    import json
    settings = json.loads(row[0])
    
    print("\n" + "=" * 80)
    print("ВАШИ ТЕКУЩИЕ НАСТРОЙКИ")
    print("=" * 80)
    print(f"OI Threshold: {settings.get('oi_threshold', 'N/A')}%")
    print(f"Liquidation OI Threshold: {settings.get('liquidation_oi_threshold', 'N/A')}%")
    print(f"Max coins to check: {settings.get('max_coins_to_check', 'N/A')}")
    print(f"Update interval: {settings.get('update_interval', 'N/A')} sec")

conn.close()
