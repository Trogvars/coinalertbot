import asyncio
import aiohttp
from datetime import datetime

async def test():
    print("=" * 80)
    print("ДЕТАЛЬНАЯ ПРОВЕРКА BINANCE API")
    print("=" * 80)
    
    base_url = "https://fapi.binance.com"
    
    async with aiohttp.ClientSession() as session:
        # Тест 1: Проверяем forceOrders (ликвидации)
        print("\n1️⃣ Тест forceOrders (ликвидации):")
        print("-" * 80)
        
        url = f"{base_url}/fapi/v1/allForceOrders"
        params = {'symbol': 'BTCUSDT', 'limit': 10}
        
        try:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                print(f"   URL: {response.url}")
                print(f"   Status: {response.status}")
                
                text = await response.text()
                print(f"   Response length: {len(text)} bytes")
                print(f"   Response preview: {text[:500]}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"   Data type: {type(data)}")
                    print(f"   Data length: {len(data) if isinstance(data, list) else 'N/A'}")
                else:
                    print(f"   ❌ Error status code")
        except Exception as e:
            print(f"   ❌ Exception: {e}")
        
        # Тест 2: Проверяем Open Interest (должен работать)
        print("\n2️⃣ Тест Open Interest:")
        print("-" * 80)
        
        url = f"{base_url}/fapi/v1/openInterest"
        params = {'symbol': 'BTCUSDT'}
        
        try:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                print(f"   Status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"   ✅ Open Interest: {data}")
                else:
                    print(f"   ❌ Error")
        except Exception as e:
            print(f"   ❌ Exception: {e}")
        
        # Тест 3: Проверяем aggTrades (агрегированные сделки)
        print("\n3️⃣ Тест aggTrades (альтернатива):")
        print("-" * 80)
        
        url = f"{base_url}/fapi/v1/aggTrades"
        params = {'symbol': 'BTCUSDT', 'limit': 5}
        
        try:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                print(f"   Status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"   ✅ Получено сделок: {len(data)}")
                    if data:
                        trade = data[0]
                        trade_time = datetime.fromtimestamp(trade['T'] / 1000)
                        print(f"   Последняя сделка: {trade_time}")
                        print(f"   Цена: ${float(trade['p']):,.2f}")
                        print(f"   Объем: {float(trade['q']):.4f}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

asyncio.run(test())
