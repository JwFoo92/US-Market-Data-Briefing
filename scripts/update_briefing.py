import os
import json
import re
from datetime import datetime
import yfinance as yf
import requests

# ====================== 配置 ======================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY 未设置")

# ====================== 1. 获取市场数据 ======================
def fetch_market_snapshot():
    tickers = {
        'SPY': 'SPY', 'QQQ': 'QQQ', 'DIA': '^DJI', 'IWM': '^RUT',
        'TNX': '^TNX', 'IRX': '^IRX', 'DXY': 'DX-Y.NYB',
        'OIL': 'CL=F', 'VIX': '^VIX',
        'XLF': 'XLF', 'XLRE': 'XLRE', 'XLI': 'XLI', 'XLU': 'XLU',
        'XLP': 'XLP', 'XLV': 'XLV', 'XLB': 'XLB', 'XLE': 'XLE',
        'XLY': 'XLY', 'XLC': 'XLC', 'XLK': 'XLK'
    }
    
    snapshot = {}
    print("Fetching live market data...")
    
    for key, symbol in tickers.items():
        try:
            t = yf.Ticker(symbol)
            hist = t.history(period="5d")
            if len(hist) >= 2:
                close = float(hist['Close'].iloc[-1])
                prev = float(hist['Close'].iloc[-2])
                pct = ((close - prev) / prev) * 100
                snapshot[key] = {
                    'price': round(close, 2),
                    'pct': round(pct, 2)
                }
        except Exception as e:
            print(f"Error {symbol}: {e}")
    return snapshot

# ====================== 2. 调用 Gemini REST API 生成完整早报 ======================
def generate_full_briefing(snapshot):
    print("Calling Gemini REST API to generate full briefing...")
    
    data_lines = [f"{k}: {v['price']} ({'+' if v['pct']>=0 else ''}{v['pct']}%)" for k, v in snapshot.items()]
    data_text = "\n".join(data_lines)
    today = datetime.now().strftime("%Y-%m-%d")
    
    prompt = f"""
你是一位资深美股研究分析师。请根据以下最新市场数据，用专业中文撰写一份完整的「美股每日早报」。

【最新市场数据】
{data_text}

请严格输出以下 JSON 格式（绝对不要包含 markdown 代码块如 ```json ，直接返回纯 JSON 字符串）：

{{
  "headline": "一句话总结今日市场核心特征（25字以内）",
  "sentiment_score": 52,
  "sentiment_label": "温和 Neutral / 多空博弈",
  "drivers": [
    {{"title": "驱动因素标题", "content": "详细解释40-70字"}},
    {{"title": "驱动因素标题", "content": "详细解释"}},
    {{"title": "驱动因素标题", "content": "详细解释"}}
  ],
  "sector_comments": {{
    "XLF": "一句话专业解读",
    "XLRE": "一句话专业解读",
    "XLI": "一句话专业解读",
    "XLU": "一句话专业解读",
    "XLP": "一句话专业解读",
    "XLV": "一句话专业解读",
    "XLB": "一句话专业解读",
    "XLE": "一句话专业解读",
    "XLY": "一句话专业解读",
    "XLC": "一句话专业解读",
    "XLK": "一句话专业解读"
  }},
  "stories": [
    {{
      "category": "FED",
      "tag": "Fed 利率决议 / 鹰派按兵不动",
      "date": "{today}",
      "title": "新闻标题（25字内）",
      "what": "事件发生描述（40-60字）",
      "why": "为什么重要 / 核心逻辑（40-60字）",
      "impact": "潜在市场影响（30-50字）",
      "source": "来源名称"
    }}
  ],
  "focus_points": [
    "盘前关注重点1（40字左右）",
    "盘前关注重点2（40字左右）",
    "盘前关注重点3（40字左右）"
  ],
  "max_risk_title": "市场最大潜在风险标题",
  "max_risk_content": "风险详细描述（60-90字）"
}}

要求：
1. stories 生成 8～10 条，覆盖不同主题（FED、AI、POLICY、EARNINGS）
2. focus_points 要具体、可操作
3. 内容专业、客观
"""

    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    headers = {"Content-Type": "application/json"}

    # 依次尝试可用模型的 REST API Endpoint
    models_to_try = [
        "gemini-2.5-flash",
        "gemini-1.5-flash"
    ]

    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        try:
            print(f"尝试请求 Endpoint: {model_name}...")
            res = requests.post(url, json=payload, headers=headers, timeout=40)
            if res.status_code == 200:
                res_data = res.json()
                text = res_data['candidates'][0]['content']['parts'][0]['text'].strip()
                # 过滤可能的 markdown 标记
                text = re.sub(r"^```(?:json)?\s*", "", text)
                text = re.sub(r"\s*```$", "", text)
                briefing = json.loads(text)
                print(f"成功通过 {model_name} 生成 AI 研报！")
                return briefing
            else:
                print(f"模型 {model_name} 返回错误状态码 {res.status_code}: {res.text}")
        except Exception as e:
            print(f"调用 {model_name} 发生异常: {e}")

    print("所有 Gemini 接口调用均失败。")
    return None

# ====================== 3. 更新 index.html ======================
def update_html(snapshot, briefing):
    if not os.path.exists("index.html"):
        print("index.html not found")
        return
    
    with open("index.html", "r", encoding="utf-8") as f:
        content = f.read()
    
    today_str = datetime.now().strftime("%Y年%m月%d日")
    content = re.sub(r'id="sector-date-badge">[^<]*<', f'id="sector-date-badge">{today_str}<', content)
    
    if not briefing:
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(content)
        return
    
    # 情绪评分 & 标签
    content = re.sub(r'id="sentiment-score-val">[^<]*<', f'id="sentiment-score-val">{briefing.get("sentiment_score", 50)}<', content)
    content = re.sub(r'id="sentiment-status-label">[^<]*<', f'id="sentiment-status-label">{briefing.get("sentiment_label", "中性")}<', content)
    
    # 大盘副标题
    if "headline" in briefing:
        content = re.sub(r'data-i18n="sec1_subtitle">[^<]*<', f'data-i18n="sec1_subtitle">{briefing["headline"]}<', content)
    
    # ===== 核心驱动逻辑 =====
    if "drivers" in briefing and len(briefing["drivers"]) >= 3:
        drivers_html = ""
        for i, d in enumerate(briefing["drivers"][:3], 1):
            drivers_html += f'''
                        <div class="bg-[#0b0f19] p-3 rounded-lg border border-[#232d42]">
                            <span class="text-white font-semibold block mb-1">{i}. {d.get("title", "")}</span>
                            <p class="text-slate-400">{d.get("content", "")}</p>
                        </div>'''
        content = re.sub(
            r'(大盘核心驱动逻辑[\s\S]*?<div class="grid md:grid-cols-3 gap-4">)[\s\S]*?(</div>\s*</div>\s*</div>)',
            r'\1' + drivers_html + r'\2',
            content, count=1
        )
    
    # ===== 新闻卡片 =====
    if "stories" in briefing:
        news_html = ""
        for s in briefing["stories"]:
            cat = s.get("category", "FED")
            news_html += f'''
                <div class="bg-[#151c2c] rounded-xl border border-[#232d42] p-4 space-y-3 hover:border-sky-500/40 transition" data-category="{cat}">
                    <div class="flex items-center justify-between text-xs">
                        <span class="px-2 py-0.5 rounded bg-sky-500/15 text-sky-300 font-mono">{s.get("tag", "")}</span>
                        <span class="text-slate-500 font-mono">{s.get("date", "")}</span>
                    </div>
                    <h3 class="text-sm font-bold text-white leading-snug">{s.get("title", "")}</h3>
                    <div class="text-xs space-y-2 text-slate-400">
                        <p><span class="text-slate-300 font-semibold">【事件发生】</span>：{s.get("what", "")}</p>
                        <p><span class="text-slate-300 font-semibold">【为什么重要 / 核心逻辑】</span>：{s.get("why", "")}</p>
                        <p><span class="text-slate-300 font-semibold">【潜在市场影响】</span>：{s.get("impact", "")}</p>
                    </div>
                    <div class="flex justify-between items-center pt-1 text-[11px]">
                        <span class="text-slate-500">来源：{s.get("source", "")}</span>
                    </div>
                </div>'''
        content = re.sub(
            r'(<div class="grid md:grid-cols-2 gap-4" id="news-container">)[\s\S]*?(</div>\s*</section>)',
            r'\1' + news_html + r'\2',
            content, count=1
        )
    
    # ===== 盘前三大关注重点 =====
    if "focus_points" in briefing and len(briefing["focus_points"]) >= 3:
        focus_html = ""
        for point in briefing["focus_points"][:3]:
            focus_html += f'<p class="text-xs text-slate-300 leading-relaxed font-sans">• {point}</p>'
        
        content = re.sub(
            r'(盘前三大关注重点[\s\S]*?<div class="space-y-2 text-xs text-slate-300">)[\s\S]*?(</div>)',
            r'\1' + focus_html + r'\2',
            content, count=1
        )
    
    # ===== 市场最大潜在风险 =====
    if "max_risk_title" in briefing and "max_risk_content" in briefing:
        risk_html = f'''
                    <div class="text-xs text-slate-300 leading-relaxed bg-rose-500/10 p-3 rounded-lg border border-rose-500/20">
                        <span class="font-bold text-rose-300 block mb-1">{briefing["max_risk_title"]}</span>
                        <p>{briefing["max_risk_content"]}</p>
                    </div>'''
        
        content = re.sub(
            r'(市场最大潜在风险[\s\S]*?<div class="text-xs text-slate-300[\s\S]*?</div>)',
            '市场最大潜在风险</span>\n                        </h3>\n' + risk_html,
            content, count=1
        )
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(content)
    
    print("index.html 已成功更新完整早报内容！")

# ====================== 主程序 ======================
if __name__ == "__main__":
    snapshot = fetch_market_snapshot()
    print("Snapshot fetched:", json.dumps(snapshot, indent=2, ensure_ascii=False))
    
    briefing = generate_full_briefing(snapshot)
    
    if briefing:
        print("Briefing generated keys:", list(briefing.keys()))
    
    update_html(snapshot, briefing)
