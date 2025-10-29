import asyncio
import aiohttp
from datetime import datetime

async def test():
    print("=" * 80)
    print("ПРОВЕРКА COINGLASS API")
    print("=" * 80)
    
    base_url = "https://open-api.coinglass.com/public/v2"
    
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        # Тест основных монет
        symbols = ['BTC', 'ETH', 'BNB', 'SOL', 'XRP']
        
        for symbol in symbols:
            print(f"\n📊 {symbol}:")
            print("-" * 80)
            
            url = f"{base_url}/liquidation"
            params = {
                'symbol': symbol,
                'time_type': 'h1'  # Последний час
            }
            
            try:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    print(f"   Status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get('success'):
                            liq_data = data.get('data', {})
                            
                            # Coinglass возвращает в миллионах USD
                            long_liq = float(liq_data.get('longLiquidation', 0)) * 1_000_000
                            short_liq = float(liq_data.get('shortLiquidation', 0)) * 1_000_000
                            total = long_liq + short_liq
                            
                            print(f"   ✅ Данные получены!")
                            print(f"      🔴 Лонги:  ${long_liq:>12,.0f}")
                            print(f"      🟢 Шорты:  ${short_liq:>12,.0f}")
                            print(f"      💰 Всего:  ${total:>12,.0f}")
                        else:
                            print(f"   ⚠️ Success=false: {data}")
                    else:
                        text = await response.text()
                        print(f"   ❌ Error: {text[:200]}")
                        
            except Exception as e:
                print(f"   ❌ Exception: {e}")
            
            await asyncio.sleep(1)

asyncio.run(test())
