import asyncio
from api import BinanceAPI

async def check():
    print("=" * 80)
    print("ТЕКУЩИЕ ЗНАЧЕНИЯ OI (TOP 10 МОНЕТ)")
    print("=" * 80)
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 
               'DOGEUSDT', 'ADAUSDT', 'AVAXUSDT', 'DOTUSDT', 'LINKUSDT']
    
    async with BinanceAPI() as binance:
        print(f"\n{'Symbol':<12} {'Open Interest':<20}")
        print("-" * 80)
        
        for symbol in symbols:
            try:
                oi = await binance.get_open_interest(symbol)
                if oi:
                    print(f"{symbol:<12} {oi:>18,.0f}")
                await asyncio.sleep(0.3)
            except Exception as e:
                print(f"{symbol:<12} ERROR: {e}")
    
    print("\n✅ Эти значения сохраняются в БД каждые 5 минут")
    print("📊 Алерты появятся когда изменение превысит порог")

asyncio.run(check())
