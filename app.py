import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time
import json
import threading
from datetime import datetime, timedelta
from collections import defaultdict
import pytz

# ─────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────
st.set_page_config(
    page_title="期權異動監控",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Noto+Sans+TC:wght@400;700&display=swap');

:root {
    --bg: #0a0a0f;
    --panel: #11111a;
    --border: #1e1e2e;
    --accent-green: #00ff88;
    --accent-red: #ff3355;
    --accent-yellow: #ffcc00;
    --accent-blue: #00aaff;
    --text: #e0e0f0;
    --text-dim: #666688;
}

html, body, [data-testid="stApp"] {
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'Noto Sans TC', sans-serif;
}

[data-testid="stSidebar"] {
    background: var(--panel) !important;
    border-right: 1px solid var(--border) !important;
}

.block-container { padding: 1.5rem 2rem !important; }

/* Header */
.main-header {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--accent-yellow);
    letter-spacing: 2px;
    border-bottom: 1px solid var(--border);
    padding-bottom: 0.5rem;
    margin-bottom: 1.5rem;
}

/* Alert Cards */
.alert-card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
    position: relative;
    overflow: hidden;
}
.alert-card::before {
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 4px;
}
.alert-bull::before { background: var(--accent-green); }
.alert-bear::before { background: var(--accent-red); }
.alert-neutral::before { background: var(--accent-yellow); }

.alert-ticker {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1rem;
    font-weight: 700;
    color: var(--accent-yellow);
}
.alert-contract {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    color: var(--text-dim);
}
.alert-bull .alert-signal { color: var(--accent-green); font-weight: 700; }
.alert-bear .alert-signal { color: var(--accent-red); font-weight: 700; }
.alert-neutral .alert-signal { color: var(--accent-yellow); font-weight: 700; }

.alert-meta {
    font-size: 0.78rem;
    color: var(--text-dim);
    font-family: 'JetBrains Mono', monospace;
    margin-top: 0.3rem;
}

/* Stats */
.stat-box {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem;
    text-align: center;
}
.stat-num {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.8rem;
    font-weight: 700;
}
.stat-label {
    font-size: 0.75rem;
    color: var(--text-dim);
    margin-top: 0.2rem;
}

/* Status bar */
.status-bar {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: var(--text-dim);
    border-top: 1px solid var(--border);
    padding-top: 0.5rem;
    margin-top: 1rem;
}
.status-live { color: var(--accent-green); }
.status-off { color: var(--accent-red); }

/* Sticker labels */
.tag-bull {
    background: rgba(0,255,136,0.12);
    color: var(--accent-green);
    border: 1px solid rgba(0,255,136,0.3);
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 0.72rem;
    font-family: 'JetBrains Mono', monospace;
}
.tag-bear {
    background: rgba(255,51,85,0.12);
    color: var(--accent-red);
    border: 1px solid rgba(255,51,85,0.3);
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 0.72rem;
    font-family: 'JetBrains Mono', monospace;
}
.tag-neutral {
    background: rgba(255,204,0,0.12);
    color: var(--accent-yellow);
    border: 1px solid rgba(255,204,0,0.3);
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 0.72rem;
    font-family: 'JetBrains Mono', monospace;
}

/* Section titles */
.section-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: var(--text-dim);
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-bottom: 0.8rem;
    margin-top: 1.2rem;
}

/* Inputs */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
    background: var(--panel) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    font-family: 'JetBrains Mono', monospace !important;
}

[data-testid="stButton"] button {
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 700 !important;
    letter-spacing: 1px !important;
}

/* Divider */
hr { border-color: var(--border) !important; }

/* Scrollable alert container */
.alert-scroll {
    max-height: 600px;
    overflow-y: auto;
    padding-right: 4px;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────
if "alerts" not in st.session_state:
    st.session_state.alerts = []
if "vol_baseline" not in st.session_state:
    st.session_state.vol_baseline = {}
if "monitoring" not in st.session_state:
    st.session_state.monitoring = False
if "sent_hashes" not in st.session_state:
    st.session_state.sent_hashes = set()
if "scan_count" not in st.session_state:
    st.session_state.scan_count = 0
if "last_scan" not in st.session_state:
    st.session_state.last_scan = None

# ─────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────

def get_us_time():
    ny = pytz.timezone("America/New_York")
    return datetime.now(ny)

def is_market_hours():
    now = get_us_time()
    if now.weekday() >= 5:
        return False
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    return market_open <= now <= market_close

def format_volume(v):
    if v >= 1_000_000:
        return f"{v/1_000_000:.1f}M"
    elif v >= 1_000:
        return f"{v/1_000:.1f}K"
    return str(v)

def determine_signal(opt_type, vol_ratio, oi_change_pct):
    """
    判斷多空信號
    Call Volume突增 + OI增加 → 看多
    Put Volume突增 + OI增加 → 看空
    Call Volume突增 + OI不變/減少 → 可能平倉，中性偏空
    Put Volume突增 + OI不變/減少 → 可能平倉，中性偏多
    """
    if opt_type == "call":
        if oi_change_pct > 5:
            return "🟢 看多", "bull"
        elif oi_change_pct < -5:
            return "🟡 Call平倉", "neutral"
        else:
            return "🟢 看多傾向", "bull"
    else:  # put
        if oi_change_pct > 5:
            return "🔴 看空", "bear"
        elif oi_change_pct < -5:
            return "🟡 Put平倉", "neutral"
        else:
            return "🔴 看空傾向", "bear"

def send_telegram(token, chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        return False

def build_telegram_message(alert):
    signal_emoji = "🟢" if alert["sentiment"] == "bull" else ("🔴" if alert["sentiment"] == "bear" else "🟡")
    msg = f"""
{signal_emoji} <b>期權異動警報</b>

📌 <b>{alert['ticker']}</b> | {alert['opt_type'].upper()} ${alert['strike']} | 到期：{alert['expiry']}
📊 信號：{alert['signal_label']}

成交量：<b>{format_volume(alert['volume'])}</b>（基準 {format_volume(alert['baseline'])} × {alert['vol_ratio']:.1f}倍）
未平倉：{format_volume(alert['oi'])}
最後價：${alert['last_price']:.2f}
IV：{alert['iv']:.1f}%

🕐 {alert['time']} (ET)
""".strip()
    return msg

def fetch_option_anomalies(ticker, threshold, tg_token, tg_chat_id):
    """核心掃描函數"""
    alerts_found = []
    try:
        tk = yf.Ticker(ticker)
        expirations = tk.options
        if not expirations:
            return alerts_found

        # ── 選項C：只掃本週+下週（14天內）到期日 ──
        now = datetime.now()
        cutoff = now + timedelta(days=14)
        near_exps = [
            e for e in expirations
            if datetime.strptime(e, "%Y-%m-%d") <= cutoff
        ]
        if not near_exps:
            # 若14天內沒有到期日（如假期），取最近1個
            near_exps = expirations[:1]

        # ── 獲取當前股價（用於行使價過濾）──
        try:
            current_price = tk.fast_info.last_price or tk.fast_info.previous_close
        except Exception:
            current_price = None

        for exp in near_exps:
            try:
                chain = tk.option_chain(exp)
                for opt_type, df in [("call", chain.calls), ("put", chain.puts)]:
                    if df.empty:
                        continue

                    for _, row in df.iterrows():
                        try:
                            vol = int(row.get("volume", 0) or 0)
                            oi = int(row.get("openInterest", 0) or 0)
                            strike = float(row.get("strike", 0))
                            last_price = float(row.get("lastPrice", 0) or 0)
                            iv = float(row.get("impliedVolatility", 0) or 0) * 100

                            # ── 行使價過濾：股價 ±10% 範圍內 ──
                            if current_price and current_price > 0:
                                lower = current_price * 0.90
                                upper = current_price * 1.10
                                if not (lower <= strike <= upper):
                                    continue

                            if vol < 50 or last_price < 0.05:
                                continue

                            # 建立/更新基準
                            key = f"{ticker}_{exp}_{opt_type}_{strike}"
                            baseline = st.session_state.vol_baseline.get(key, None)

                            if baseline is None:
                                # 首次掃描：用OI作基準估算
                                baseline = max(oi * 0.05, 100)
                                st.session_state.vol_baseline[key] = baseline
                                continue  # 首次不觸發

                            vol_ratio = vol / baseline if baseline > 0 else 1

                            if vol_ratio >= threshold:
                                # OI變化估算（Yahoo不提供前日OI，用vol/oi比例推算）
                                oi_change_pct = (vol / oi * 100) if oi > 0 else 0
                                signal_label, sentiment = determine_signal(opt_type, vol_ratio, oi_change_pct)

                                alert = {
                                    "ticker": ticker,
                                    "exp": exp,
                                    "expiry": exp,
                                    "opt_type": opt_type,
                                    "strike": strike,
                                    "volume": vol,
                                    "baseline": int(baseline),
                                    "vol_ratio": vol_ratio,
                                    "oi": oi,
                                    "last_price": last_price,
                                    "iv": iv,
                                    "signal_label": signal_label,
                                    "sentiment": sentiment,
                                    "time": get_us_time().strftime("%H:%M:%S"),
                                    "timestamp": time.time()
                                }

                                # 去重
                                alert_hash = f"{key}_{vol}"
                                if alert_hash not in st.session_state.sent_hashes:
                                    st.session_state.sent_hashes.add(alert_hash)
                                    alerts_found.append(alert)

                                    # 發送Telegram
                                    if tg_token and tg_chat_id:
                                        msg = build_telegram_message(alert)
                                        send_telegram(tg_token, tg_chat_id, msg)

                            # 更新基準（滾動平均）
                            st.session_state.vol_baseline[key] = (baseline * 0.7 + vol * 0.3)

                        except Exception:
                            continue
            except Exception:
                continue

    except Exception as e:
        st.session_state.alerts.insert(0, {
            "ticker": ticker,
            "error": str(e),
            "time": get_us_time().strftime("%H:%M:%S"),
            "sentiment": "neutral"
        })

    return alerts_found

# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="main-header">⚡ 期權異動</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">監控設定</div>', unsafe_allow_html=True)

    tickers_input = st.text_input(
        "股票清單（逗號分隔）",
        value="TSLA,AAPL,NVDA",
        placeholder="TSLA,AAPL,NVDA,MSFT"
    )

    threshold = st.slider(
        "異動門檻（倍數）",
        min_value=2.0,
        max_value=10.0,
        value=3.0,
        step=0.5,
        help="成交量超過基準N倍時觸發"
    )

    scan_interval = st.slider(
        "掃描間隔（秒）",
        min_value=60,
        max_value=300,
        value=120,
        step=30
    )

    st.markdown('<div class="section-title">Telegram 設定</div>', unsafe_allow_html=True)

    tg_token = st.text_input(
        "Bot Token",
        type="password",
        placeholder="123456789:AAxxxxxx"
    )

    tg_chat_id = st.text_input(
        "Chat ID",
        placeholder="-100xxxxxxxxx"
    )

    # Test Telegram
    if st.button("📨 測試Telegram", use_container_width=True):
        if tg_token and tg_chat_id:
            ok = send_telegram(tg_token, tg_chat_id, "✅ 期權異動監控系統連線成功！")
            if ok:
                st.success("發送成功！")
            else:
                st.error("發送失敗，請檢查Token/Chat ID")
        else:
            st.warning("請填入Token和Chat ID")

    st.divider()

    # Start/Stop
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶ 啟動", use_container_width=True, type="primary"):
            st.session_state.monitoring = True
            st.session_state.vol_baseline = {}
            st.session_state.sent_hashes = set()
            st.session_state.scan_count = 0
            st.session_state.alerts = []
    with col2:
        if st.button("⏹ 停止", use_container_width=True):
            st.session_state.monitoring = False

    # Status
    if st.session_state.monitoring:
        st.markdown('<p class="status-bar"><span class="status-live">● LIVE</span> 監控中</p>', unsafe_allow_html=True)
    else:
        st.markdown('<p class="status-bar"><span class="status-off">● OFF</span> 已停止</p>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">說明</div>', unsafe_allow_html=True)
    st.markdown("""
<div style="font-size:0.75rem; color:#666688; line-height:1.6;">
• 掃描範圍：<b style="color:#ffcc00">14天內到期日</b>（本週+下週）<br>
• 行使價：<b style="color:#ffcc00">股價 ±10%</b> 範圍內合約<br>
• 首次掃描建立基準，第二次起觸發警報<br>
• 看多 = Call量突增<br>
• 看空 = Put量突增<br>
• 數據延遲約15-20分鐘
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# MAIN PANEL
# ─────────────────────────────────────────
st.markdown('<div class="main-header">🔥 期權異動監控系統</div>', unsafe_allow_html=True)

# Stats row
tickers_list = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
bull_count = sum(1 for a in st.session_state.alerts if a.get("sentiment") == "bull")
bear_count = sum(1 for a in st.session_state.alerts if a.get("sentiment") == "bear")
total_alerts = len(st.session_state.alerts)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""
    <div class="stat-box">
        <div class="stat-num" style="color:#00aaff">{len(tickers_list)}</div>
        <div class="stat-label">監控股票</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <div class="stat-box">
        <div class="stat-num" style="color:#00ff88">{bull_count}</div>
        <div class="stat-label">🟢 看多信號</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""
    <div class="stat-box">
        <div class="stat-num" style="color:#ff3355">{bear_count}</div>
        <div class="stat-label">🔴 看空信號</div>
    </div>""", unsafe_allow_html=True)
with c4:
    st.markdown(f"""
    <div class="stat-box">
        <div class="stat-num" style="color:#ffcc00">{st.session_state.scan_count}</div>
        <div class="stat-label">掃描次數</div>
    </div>""", unsafe_allow_html=True)

st.markdown("")

# ─── SCANNING LOGIC ───
if st.session_state.monitoring:
    if not is_market_hours():
        st.warning("⚠️ 現在非美股交易時段（ET 09:30-16:00），數據可能不更新。監控仍運行中。")

    with st.spinner(f"🔍 掃描中... {', '.join(tickers_list)}"):
        new_alerts = []
        for ticker in tickers_list:
            found = fetch_option_anomalies(ticker, threshold, tg_token, tg_chat_id)
            new_alerts.extend(found)

        st.session_state.scan_count += 1
        st.session_state.last_scan = get_us_time().strftime("%H:%M:%S ET")

        if new_alerts:
            st.session_state.alerts = new_alerts + st.session_state.alerts
            # 只保留最新100條
            st.session_state.alerts = st.session_state.alerts[:100]

    # Auto-refresh
    time.sleep(scan_interval)
    st.rerun()

# ─── ALERT FEED ───
st.markdown('<div class="section-title">異動警報 Feed</div>', unsafe_allow_html=True)

if st.session_state.last_scan:
    st.markdown(f'<p style="font-size:0.75rem;color:#666688;font-family:monospace;">最後掃描：{st.session_state.last_scan}</p>', unsafe_allow_html=True)

if not st.session_state.alerts:
    if st.session_state.monitoring:
        st.info("🔍 正在建立基準數據，下一輪掃描開始偵測異動...")
    else:
        st.info("👆 點擊左側「▶ 啟動」開始監控")
else:
    # Filter controls
    fc1, fc2 = st.columns([2, 1])
    with fc1:
        filter_sentiment = st.selectbox(
            "篩選信號",
            ["全部", "🟢 看多", "🔴 看空", "🟡 中性"],
            label_visibility="collapsed"
        )
    with fc2:
        if st.button("🗑 清除記錄", use_container_width=True):
            st.session_state.alerts = []
            st.rerun()

    # Display alerts
    for alert in st.session_state.alerts:
        if "error" in alert:
            continue

        sentiment = alert.get("sentiment", "neutral")

        # Apply filter
        if filter_sentiment == "🟢 看多" and sentiment != "bull":
            continue
        if filter_sentiment == "🔴 看空" and sentiment != "bear":
            continue
        if filter_sentiment == "🟡 中性" and sentiment != "neutral":
            continue

        card_class = f"alert-{sentiment}"
        tag_class = f"tag-{sentiment}"
        signal_label = alert.get("signal_label", "")

        opt_label = "CALL" if alert.get("opt_type") == "call" else "PUT"
        opt_color = "#00ff88" if alert.get("opt_type") == "call" else "#ff3355"

        st.markdown(f"""
        <div class="alert-card {card_class}">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span class="alert-ticker">{alert.get('ticker','')}</span>
                    <span style="color:{opt_color}; font-family:monospace; font-size:0.8rem; margin-left:8px;">{opt_label}</span>
                    <span class="alert-contract"> ${alert.get('strike','')} | {alert.get('expiry','')}</span>
                </div>
                <span class="{tag_class}">{signal_label}</span>
            </div>
            <div class="alert-meta" style="margin-top:0.5rem;">
                成交量 <b style="color:#e0e0f0">{format_volume(alert.get('volume',0))}</b>
                &nbsp;|&nbsp; 基準×<b style="color:#ffcc00">{alert.get('vol_ratio',0):.1f}</b>倍
                &nbsp;|&nbsp; OI {format_volume(alert.get('oi',0))}
                &nbsp;|&nbsp; 最後 <b style="color:#e0e0f0">${alert.get('last_price',0):.2f}</b>
                &nbsp;|&nbsp; IV {alert.get('iv',0):.1f}%
            </div>
            <div class="alert-meta" style="color:#444466;">
                🕐 {alert.get('time','')}
            </div>
        </div>
        """, unsafe_allow_html=True)

# ─── FOOTER ───
st.markdown("---")
st.markdown("""
<div style="font-size:0.7rem; color:#333355; font-family:monospace; text-align:center;">
期權異動監控系統 v1.0 &nbsp;|&nbsp; 數據來源：Yahoo Finance（15-20分鐘延遲）&nbsp;|&nbsp; 僅供參考，非投資建議
</div>
""", unsafe_allow_html=True)
