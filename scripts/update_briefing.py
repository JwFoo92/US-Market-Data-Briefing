import os
import json
import re
from datetime import datetime
import yfinance as yf

# 1. Fetch real-time market data across Indices, Treasury, Crude, and Sector ETFs
def fetch_market_snapshot():
    tickers = {
        'SPY': 'SPY',
        'QQQ': 'QQQ',
        'DIA': '^DJI',
        'IWM': '^RUT',
        'TNX': '^TNX', # 10Y Treasury
        'IRX': '^IRX', # 13-Week/Short Treasury
        'DXY': 'DX-Y.NYB',
        'OIL': 'CL=F', # WTI Crude
        'VIX': '^VIX',
        
        # 11 Select Sector SPDR ETFs
        'XLF': 'XLF', 'XLRE': 'XLRE', 'XLI': 'XLI',
        'XLU': 'XLU', 'XLP': 'XLP', 'XLV': 'XLV',
        'XLB': 'XLB', 'XLE': 'XLE', 'XLY': 'XLY',
        'XLC': 'XLC', 'XLK': 'XLK'
    }
    
    snapshot = {}
    print("Fetching live market data from Yahoo Finance...")
    
    for key, symbol in tickers.items():
        try:
            t = yf.Ticker(symbol)
            hist = t.history(period="5d")
            if len(hist) >= 2:
                close = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2]
                pct = ((close - prev) / prev) * 100
                diff = close - prev
                snapshot[key] = {
                    'price': round(close, 2),
                    'pct': round(pct, 2),
                    'diff': round(diff, 2)
                }
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            
    return snapshot

# 2. Update index.html with the fresh snapshot numbers
def sync_to_index_html(data):
    if not os.path.exists("index.html"):
        print("index.html not found.")
        return

    with open("index.html", "r", encoding="utf-8") as f:
        content = f.read()

    # Update date badge to current date
    today_str = datetime.now().strftime("%Y年%m月%d日")
    content = re.sub(r'id="sector-date-badge">[^<]+<', f'id="sector-date-badge">{today_str}<', content)

    # Example: Sync VIX reading if available
    if 'VIX' in data:
        vix_val = str(data['VIX']['price'])
        vix_pct = f"{'+' if data['VIX']['pct'] > 0 else ''}{data['VIX']['pct']}%"
        content = re.sub(r'id="vix-val">[^<]+<', f'id="vix-val">{vix_val}<', content)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(content)

    print("Successfully synchronized market data snapshot into index.html!")

if __name__ == "__main__":
    snapshot = fetch_market_snapshot()
    sync_to_index_html(snapshot)
