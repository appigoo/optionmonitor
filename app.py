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

def is_weekend():
    return get_us_time().weekday() >= 5

def get_session_label():
    """返回當前時段標籤"""
    now = get_us_time()
    if is_market_hours():
        return "LIVE", "🟢 美股交易時段"
    elif now.weekday() >= 5:
        return "WEEKEND", "🟡 週末 — 顯示上週五收市數據"
    elif now.hour < 9 or (now.hour == 9 and now.minute < 30):
        return "PRE", "🟡 盤前 — 顯示昨日收市數據"
    else:
        return "AFTER", "🟡 收市後 — 顯示今日完整期權數據"

def fetch_afterhours_analysis(ticker, top_n=10):
    """
    收市後/非交易時段模式：
    掃描最近交易日的完整期權數據，
    按成交量絕對值排名，找出全日最大手的合約，
    作為隔日方向參考。
    """
    results = []
    try:
        tk = yf.Ticker(ticker)
        expirations = tk.options
        if not expirations:
            return results

        # 14天內到期日
        now = datetime.now()
        cutoff = now + timedelta(days=14)
        near_exps = [
            e for e in expirations
            if datetime.strptime(e, "%Y-%m-%d") <= cutoff
        ]
        if not near_exps:
            near_exps = expirations[:1]

        # 獲取股價
        try:
            current_price = tk.fast_info.last_price or tk.fast_info.previous_close
        except Exception:
            current_price = None

        all_contracts = []

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

                            # 行使價過濾 ±10%
                            if current_price and current_price > 0:
                                if not (current_price * 0.90 <= strike <= current_price * 1.10):
                                    continue

                            if vol < 100 or last_price < 0.05:
                                continue

                            # vol/oi 比值：越高代表新開倉比例越大
                            vol_oi_ratio = (vol / oi) if oi > 0 else 0
                            oi_change_pct = vol_oi_ratio * 100
                            signal_label, sentiment = determine_signal(opt_type, vol_oi_ratio, oi_change_pct)

                            all_contracts.append({
                                "ticker": ticker,
                                "expiry": exp,
                                "opt_type": opt_type,
                                "strike": strike,
                                "volume": vol,
                                "baseline": oi,
                                "vol_ratio": vol_oi_ratio,
                                "oi": oi,
                                "last_price": last_price,
                                "iv": iv,
                                "signal_label": signal_label,
                                "sentiment": sentiment,
                                "time": get_us_time().strftime("%H:%M:%S"),
                                "timestamp": time.time(),
                                "mode": "afterhours"  # 標記為收市後分析
                            })
                        except Exception:
                            continue
            except Exception:
                continue

        # 按成交量排序，取Top N
        all_contracts.sort(key=lambda x: x["volume"], reverse=True)
        results = all_contracts[:top_n]

    except Exception:
        pass

    return results

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
    mode = alert.get("mode", "live")
    mode_label = "📊 收市後分析 — 隔日參考" if mode == "afterhours" else "⚡ 實時異動"
    vol_label = "全日成交量" if mode == "afterhours" else "成交量"
    ratio_label = "Vol/OI" if mode == "afterhours" else f"基準×{alert['vol_ratio']:.1f}倍"

    msg = f"""
{signal_emoji} <b>期權異動警報</b> | {mode_label}

📌 <b>{alert['ticker']}</b> | {alert['opt_type'].upper()} ${alert['strike']} | 到期：{alert['expiry']}
📊 信號：{alert['signal_label']}

{vol_label}：<b>{format_volume(alert['volume'])}</b>（{ratio_label}）
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
# AUTO ANALYSIS FUNCTIONS
# ─────────────────────────────────────────

def auto_analyze(alerts):
    """
    根據警報數據自動生成中文分析摘要
    """
    if not alerts:
        return None

    valid = [a for a in alerts if "error" not in a]
    if not valid:
        return None

    is_afterhours = valid[0].get("mode") == "afterhours"

    # 統計
    bull_alerts = [a for a in valid if a["sentiment"] == "bull"]
    bear_alerts = [a for a in valid if a["sentiment"] == "bear"]
    neutral_alerts = [a for a in valid if a["sentiment"] == "neutral"]

    # 按股票分組
    ticker_groups = {}
    for a in valid:
        t = a["ticker"]
        if t not in ticker_groups:
            ticker_groups[t] = {"bull": [], "bear": [], "neutral": []}
        ticker_groups[t][a["sentiment"]].append(a)

    lines = []

    # ── 整體傾向 ──
    total = len(valid)
    bull_pct = len(bull_alerts) / total * 100
    bear_pct = len(bear_alerts) / total * 100

    if bull_pct >= 70:
        overall = "🟢 整體明顯偏多"
        overall_detail = f"看多信號佔 {bull_pct:.0f}%，市場情緒積極。"
    elif bear_pct >= 70:
        overall = "🔴 整體明顯偏空"
        overall_detail = f"看空信號佔 {bear_pct:.0f}%，市場情緒謹慎。"
    elif bull_pct > bear_pct:
        overall = "🟡 整體略偏多"
        overall_detail = f"看多 {len(bull_alerts)} 個 vs 看空 {len(bear_alerts)} 個，多方略佔優。"
    elif bear_pct > bull_pct:
        overall = "🟡 整體略偏空"
        overall_detail = f"看空 {len(bear_alerts)} 個 vs 看多 {len(bull_alerts)} 個，空方略佔優。"
    else:
        overall = "⚪ 多空均衡"
        overall_detail = "看多看空信號數量相近，市場方向不明確。"

    lines.append(("overall", overall, overall_detail))

    # ── 逐股分析 ──
    stock_analysis = []
    for ticker, groups in ticker_groups.items():
        bull_n = len(groups["bull"])
        bear_n = len(groups["bear"])
        all_ticker = groups["bull"] + groups["bear"] + groups["neutral"]

        # 最大成交量合約
        top = max(all_ticker, key=lambda x: x["volume"]) if all_ticker else None

        if bull_n > bear_n:
            direction = "偏多"
            dir_color = "bull"
        elif bear_n > bull_n:
            direction = "偏空"
            dir_color = "bear"
        else:
            direction = "中性"
            dir_color = "neutral"

        # Vol/OI 或倍數解讀
        if top:
            voi = top.get("vol_ratio", 0)
            iv = top.get("iv", 0)
            strike = top.get("strike", 0)
            opt_type = top.get("opt_type", "call").upper()
            expiry = top.get("expiry", "")
            vol = top.get("volume", 0)

            if is_afterhours:
                strength = "極強" if voi > 10 else ("強" if voi > 5 else ("中等" if voi > 2 else "一般"))
                key_info = f"最活躍合約：{opt_type} ${strike}（到期 {expiry}），全日成交 {format_volume(vol)} 張，Vol/OI={voi:.2f}（新開倉{strength}）"
            else:
                strength = "極強" if voi > 7 else ("強" if voi > 4 else ("中等" if voi > 2 else "一般"))
                key_info = f"最強異動：{opt_type} ${strike}（到期 {expiry}），成交量突增 {voi:.1f} 倍（{strength}信號）"

            # IV解讀
            if iv > 80:
                iv_comment = f"IV {iv:.0f}% 極高，市場預期短期大幅波動。"
            elif iv > 50:
                iv_comment = f"IV {iv:.0f}% 偏高，市場有一定不確定性。"
            elif iv > 30:
                iv_comment = f"IV {iv:.0f}% 正常水平。"
            else:
                iv_comment = f"IV {iv:.0f}% 偏低，市場情緒平穩。"

            stock_analysis.append({
                "ticker": ticker,
                "direction": direction,
                "dir_color": dir_color,
                "bull_n": bull_n,
                "bear_n": bear_n,
                "key_info": key_info,
                "iv_comment": iv_comment,
                "top_vol": vol
            })

    stock_analysis.sort(key=lambda x: x["top_vol"], reverse=True)

    # ── 隔日展望（收市後模式）──
    if is_afterhours:
        if bull_pct >= 60:
            outlook = "收市前大量資金集中在Call端，隔日開盤若配合大盤走強，有機會延續升勢。留意阻力位附近是否出現反向信號。"
        elif bear_pct >= 60:
            outlook = "收市前大量資金集中在Put端，隔日開盤需注意下行風險，建議觀察開盤前15分鐘走勢確認方向。"
        else:
            outlook = "多空信號混雜，隔日方向不明確。建議等待開盤後量價確認再入場，避免倉促建倉。"
    else:
        if bull_pct >= 60:
            outlook = "短線多方信號強烈，但需注意期權異動可能包含對沖成分，配合技術面確認再行動。"
        elif bear_pct >= 60:
            outlook = "短線空方信號明顯，留意下行風險，可考慮收緊止損或減倉。"
        else:
            outlook = "信號混雜，建議觀望為主，等待更清晰的方向性異動出現。"

    return {
        "overall": overall,
        "overall_detail": overall_detail,
        "stock_analysis": stock_analysis,
        "outlook": outlook,
        "bull_n": len(bull_alerts),
        "bear_n": len(bear_alerts),
        "total": total,
        "is_afterhours": is_afterhours
    }


def generate_ai_prompt(alerts, analysis):
    """
    生成可複製到任何AI的分析Prompt
    """
    if not alerts or not analysis:
        return ""

    valid = [a for a in alerts if "error" not in a]
    is_afterhours = valid[0].get("mode") == "afterhours" if valid else False
    mode_label = "收市後期權數據分析" if is_afterhours else "實時期權異動分析"
    scan_time = valid[0].get("time", "") if valid else ""

    # 整理數據
    data_lines = []
    for a in valid[:15]:  # 最多15條
        opt = a.get("opt_type","").upper()
        ticker = a.get("ticker","")
        strike = a.get("strike","")
        expiry = a.get("expiry","")
        vol = format_volume(a.get("volume",0))
        voi = a.get("vol_ratio",0)
        oi = format_volume(a.get("oi",0))
        iv = a.get("iv",0)
        last = a.get("last_price",0)
        signal = a.get("signal_label","")

        if is_afterhours:
            data_lines.append(f"- {ticker} {opt} ${strike} 到期{expiry}：全日成交{vol}張，Vol/OI={voi:.2f}，OI={oi}，最後${last:.2f}，IV={iv:.0f}%，信號={signal}")
        else:
            data_lines.append(f"- {ticker} {opt} ${strike} 到期{expiry}：成交量突增{voi:.1f}倍，OI={oi}，最後${last:.2f}，IV={iv:.0f}%，信號={signal}")

    data_str = "\n".join(data_lines)
    tickers = list(set(a.get("ticker","") for a in valid))
    tickers_str = "、".join(tickers)
    scan_date = get_us_time().strftime("%Y-%m-%d")

    if is_afterhours:
        context = f"以下是{scan_date} 美股收市後的期權數據（{mode_label}），掃描時間 {scan_time} ET。這些是按全日成交量排名的最活躍合約，反映機構當日的佈局方向。"
        question = f"""請根據以上期權數據，幫我分析：

1. **整體市場情緒**：從Call/Put的成交分佈，判斷機構對{tickers_str}的整體看法是偏多還是偏空？

2. **重點合約解讀**：哪些合約的Vol/OI比值最值得關注？高Vol/OI代表大量新開倉，請重點分析這些合約的含義。

3. **行使價分佈意義**：機構集中在哪個價位區間建倉？這對判斷支撐/阻力有何參考意義？

4. **IV分析**：當前IV水平對比正常範圍是高還是低？這反映市場對短期波動的預期如何？

5. **隔日交易建議**：基於以上期權異動，下一個交易日的方向傾向是什麼？有哪些需要特別留意的風險？

請用簡潔的繁體中文回答，每個部分給出明確的判斷，避免含糊表述。"""
    else:
        context = f"以下是{scan_date} 美股交易時段的期權異動數據（{mode_label}），掃描時間 {scan_time} ET。這些合約的成交量出現異常突增，可能反映機構的短線方向性押注。"
        question = f"""請根據以上期權異動數據，幫我分析：

1. **異動性質判斷**：這些成交量突增屬於新開倉建倉，還是平倉離場？請結合OI數據判斷。

2. **方向性信號**：Call/Put的異動分佈顯示市場短線傾向多方還是空方？信號強度如何？

3. **機構意圖推測**：基於行使價選擇和到期日，這些異動更像是方向性押注、對沖現貨，還是其他策略？

4. **IV異常分析**：哪些合約的IV特別值得關注？是否暗示市場預期某個催化劑事件？

5. **短線交易建議**：基於以上異動，對{tickers_str}的短線操作有什麼具體建議？包括方向、潛在入場區間和風險提示。

請用簡潔的繁體中文回答，給出明確判斷，不要過度保守。"""

    prompt = f"""你是一位專業的美股期權分析師，擅長解讀期權異動背後的機構意圖。

【數據背景】
{context}

【期權異動數據】
{data_str}

【分析請求】
{question}"""

    return prompt


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

    afterhours_top_n = st.slider(
        "收市後顯示Top N合約",
        min_value=5,
        max_value=30,
        value=10,
        step=5,
        help="非交易時段按全日成交量排名，顯示前N個最活躍合約"
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
    session_code, session_label = get_session_label()

    if session_code == "LIVE":
        # ══ 實時模式 ══
        st.markdown(f'<p style="font-size:0.78rem; color:#00ff88; font-family:monospace;">● {session_label}</p>', unsafe_allow_html=True)

        with st.spinner(f"🔍 實時掃描中... {', '.join(tickers_list)}"):
            new_alerts = []
            for ticker in tickers_list:
                found = fetch_option_anomalies(ticker, threshold, tg_token, tg_chat_id)
                new_alerts.extend(found)

            st.session_state.scan_count += 1
            st.session_state.last_scan = get_us_time().strftime("%H:%M:%S ET")

            if new_alerts:
                st.session_state.alerts = new_alerts + st.session_state.alerts
                st.session_state.alerts = st.session_state.alerts[:100]

        time.sleep(scan_interval)
        st.rerun()

    else:
        # ══ 收市後/盤前/週末模式 ══
        st.markdown(f'<p style="font-size:0.78rem; color:#ffcc00; font-family:monospace;">● {session_label}</p>', unsafe_allow_html=True)

        st.info("📊 **收市後分析模式** — 掃描最近交易日完整期權數據，按全日成交量排名，供判斷下一個交易日趨勢參考。")

        # 只掃一次（收市後數據不會再變，無需輪詢）
        if st.session_state.scan_count == 0 or st.button("🔄 重新掃描", key="rescan_ah"):
            with st.spinner(f"📊 分析最近交易日數據... {', '.join(tickers_list)}"):
                ah_alerts = []
                for ticker in tickers_list:
                    found = fetch_afterhours_analysis(ticker, top_n=afterhours_top_n)
                    # 推送Top 3到Telegram（避免洗版）
                    for i, alert in enumerate(found[:3]):
                        ah_key = f"ah_{alert['ticker']}_{alert['expiry']}_{alert['opt_type']}_{alert['strike']}"
                        if ah_key not in st.session_state.sent_hashes:
                            st.session_state.sent_hashes.add(ah_key)
                            if tg_token and tg_chat_id:
                                msg = build_telegram_message(alert)
                                send_telegram(tg_token, tg_chat_id, msg)
                    ah_alerts.extend(found)

                st.session_state.scan_count += 1
                st.session_state.last_scan = get_us_time().strftime("%H:%M:%S ET")

                if ah_alerts:
                    # 收市後模式：直接替換（非累加）
                    st.session_state.alerts = ah_alerts

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
        is_afterhours = alert.get("mode") == "afterhours"

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

        # 收市後模式：顯示Vol/OI比值；實時模式：顯示基準倍數
        if is_afterhours:
            ratio_html = f'Vol/OI <b style="color:#ffcc00">{alert.get("vol_ratio",0):.2f}</b>'
            mode_badge = '<span style="font-size:0.65rem; color:#ffcc00; font-family:monospace; margin-left:6px;">📊 隔日參考</span>'
        else:
            ratio_html = f'基準×<b style="color:#ffcc00">{alert.get("vol_ratio",0):.1f}</b>倍'
            mode_badge = '<span style="font-size:0.65rem; color:#00ff88; font-family:monospace; margin-left:6px;">⚡ 實時</span>'

        st.markdown(f"""
        <div class="alert-card {card_class}">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span class="alert-ticker">{alert.get('ticker','')}</span>
                    <span style="color:{opt_color}; font-family:monospace; font-size:0.8rem; margin-left:8px;">{opt_label}</span>
                    <span class="alert-contract"> ${alert.get('strike','')} | {alert.get('expiry','')}</span>
                    {mode_badge}
                </div>
                <span class="{tag_class}">{signal_label}</span>
            </div>
            <div class="alert-meta" style="margin-top:0.5rem;">
                成交量 <b style="color:#e0e0f0">{format_volume(alert.get('volume',0))}</b>
                &nbsp;|&nbsp; {ratio_html}
                &nbsp;|&nbsp; OI {format_volume(alert.get('oi',0))}
                &nbsp;|&nbsp; 最後 <b style="color:#e0e0f0">${alert.get('last_price',0):.2f}</b>
                &nbsp;|&nbsp; IV {alert.get('iv',0):.1f}%
            </div>
            <div class="alert-meta" style="color:#444466;">
                🕐 {alert.get('time','')}
            </div>
        </div>
        """, unsafe_allow_html=True)

# ─── AUTO ANALYSIS SECTION ───
if st.session_state.alerts:
    valid_alerts = [a for a in st.session_state.alerts if "error" not in a]
    if valid_alerts:
        st.markdown("---")
        st.markdown('<div class="section-title">🧠 自動分析</div>', unsafe_allow_html=True)

        analysis = auto_analyze(valid_alerts)
        if analysis:
            # 整體傾向
            overall_color = "#00ff88" if "多" in analysis["overall"] and "空" not in analysis["overall"] else ("#ff3355" if "空" in analysis["overall"] else "#ffcc00")
            st.markdown(f"""
            <div style="background:#11111a; border:1px solid #1e1e2e; border-radius:8px; padding:1.2rem 1.5rem; margin-bottom:1rem;">
                <div style="font-family:monospace; font-size:0.7rem; color:#666688; letter-spacing:2px; margin-bottom:0.5rem;">整體市場情緒</div>
                <div style="font-size:1.1rem; font-weight:700; color:{overall_color}; margin-bottom:0.3rem;">{analysis['overall']}</div>
                <div style="font-size:0.85rem; color:#aaaacc;">{analysis['overall_detail']}</div>
                <div style="display:flex; gap:1.5rem; margin-top:0.8rem;">
                    <span style="font-family:monospace; font-size:0.75rem; color:#00ff88;">🟢 看多 {analysis['bull_n']} 個</span>
                    <span style="font-family:monospace; font-size:0.75rem; color:#ff3355;">🔴 看空 {analysis['bear_n']} 個</span>
                    <span style="font-family:monospace; font-size:0.75rem; color:#666688;">共 {analysis['total']} 個信號</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # 逐股分析
            for sa in analysis["stock_analysis"]:
                dir_color = "#00ff88" if sa["dir_color"] == "bull" else ("#ff3355" if sa["dir_color"] == "bear" else "#ffcc00")
                border_color = "#00ff88" if sa["dir_color"] == "bull" else ("#ff3355" if sa["dir_color"] == "bear" else "#ffcc00")
                st.markdown(f"""
                <div style="background:#11111a; border:1px solid #1e1e2e; border-left:3px solid {border_color}; border-radius:4px; padding:1rem 1.2rem; margin-bottom:0.6rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                        <span style="font-family:monospace; font-weight:700; color:#c9a84c; font-size:0.9rem;">{sa['ticker']}</span>
                        <span style="font-size:0.75rem; color:{dir_color}; font-weight:700;">{sa['direction']}</span>
                    </div>
                    <div style="font-size:0.82rem; color:#ccccee; margin-bottom:0.3rem;">📌 {sa['key_info']}</div>
                    <div style="font-size:0.78rem; color:#888899;">📈 {sa['iv_comment']}</div>
                </div>
                """, unsafe_allow_html=True)

            # 展望
            mode_title = "📅 隔日展望" if analysis["is_afterhours"] else "⚡ 短線展望"
            st.markdown(f"""
            <div style="background:#0d0d18; border:1px solid #2a2a40; border-radius:8px; padding:1.2rem 1.5rem; margin-top:0.5rem;">
                <div style="font-family:monospace; font-size:0.7rem; color:#666688; letter-spacing:2px; margin-bottom:0.5rem;">{mode_title}</div>
                <div style="font-size:0.88rem; color:#ddddee; line-height:1.8;">{analysis['outlook']}</div>
            </div>
            """, unsafe_allow_html=True)

        # ─── AI PROMPT SECTION ───
        st.markdown("---")
        st.markdown('<div class="section-title">🤖 AI深度分析 Prompt</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="font-size:0.78rem; color:#666688; margin-bottom:0.8rem;">
        複製以下Prompt，貼到 ChatGPT / Claude / Gemini，獲取更深入的AI分析。
        </div>
        """, unsafe_allow_html=True)

        ai_prompt = generate_ai_prompt(valid_alerts, analysis)
        if ai_prompt:
            st.text_area(
                label="AI分析Prompt（點擊全選→複製）",
                value=ai_prompt,
                height=280,
                key="ai_prompt_box",
                label_visibility="collapsed"
            )
            # 快捷連結
            pc1, pc2, pc3 = st.columns(3)
            with pc1:
                st.link_button("🤖 開啟 ChatGPT", "https://chat.openai.com", use_container_width=True)
            with pc2:
                st.link_button("🧠 開啟 Claude", "https://claude.ai", use_container_width=True)
            with pc3:
                st.link_button("✨ 開啟 Gemini", "https://gemini.google.com", use_container_width=True)

            st.markdown("""
            <div style="font-size:0.7rem; color:#444466; margin-top:0.5rem; font-family:monospace;">
            💡 提示：複製Prompt → 開啟AI → 貼上 → 發送。每次掃描後Prompt自動更新最新數據。
            </div>
            """, unsafe_allow_html=True)

# ─── FOOTER ───
st.markdown("---")
st.markdown("""
<div style="font-size:0.7rem; color:#333355; font-family:monospace; text-align:center;">
期權異動監控系統 v1.1 &nbsp;|&nbsp; 數據來源：Yahoo Finance（15-20分鐘延遲）&nbsp;|&nbsp; 僅供參考，非投資建議
</div>
""", unsafe_allow_html=True)
