#!/usr/bin/env python3
"""
A股股票专业深度分析器 v2.0 - 基于 Tushare API

六维分析框架：
  1. 基本面  - 盈利/成长/估值/偿债/现金流/运营效率
  2. 技术面  - 趋势/动量(MACD·KDJ·RSI·BOLL)/量能/波动性
  3. 资金面  - 主力大单净流入/融资融券/大宗交易
  4. 筹码面  - 股东户数趋势/前十大持仓/外资动向
  5. 综合评分 - 加权合成
  6. 未来一周走势预测 - 多因子信号聚合+ATR目标区间

输出：JSON 数据文件（供 generate_report.py 渲染 HTML 报告）
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta

# ─── 配置 ─────────────────────────────────────────────────────────────────────
TUSHARE_TOKEN = "TUSHARE_TOKEN_PLACEHOLDER"
API_URL = "http://api.waditu.com"

# 火山引擎 Doubao LLM API 配置
DOUBAO_API_KEY  = "DOUBAO_API_KEY_PLACEHOLDER"
DOUBAO_ENDPOINT = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
DOUBAO_MODEL    = "doubao-seed-2-0-pro-260215"


# ─── API 调用层 ────────────────────────────────────────────────────────────────
def curl_api(api_name, params=None, fields=None):
    """使用 curl 调用 Tushare HTTP API，返回 list[dict]"""
    payload = {
        "api_name": api_name,
        "token": TUSHARE_TOKEN,
        "params": params or {},
    }
    if fields:
        payload["fields"] = fields

    cmd = ["curl", "-s", "-X", "POST",
           "-H", "Content-Type: application/json",
           "-d", json.dumps(payload), API_URL]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        data = json.loads(res.stdout)
        if data.get("code") == 0:
            raw = data.get("data", {})
            flds = raw.get("fields", [])
            items = raw.get("items", [])
            return [dict(zip(flds, it)) for it in items]
        else:
            print(f"    [API警告] {api_name}: {data.get('msg')}")
            return []
    except Exception as e:
        print(f"    [API错误] {api_name}: {e}")
        return []


# ─── Doubao LLM API ──────────────────────────────────────────────────────────
def call_doubao(prompt, system_prompt="你是一位资深A股分析师，擅长撰写专业简洁的股票分析报告。", max_tokens=800):
    """调用火山引擎 Doubao 大模型 API，返回文本或 None"""
    import urllib.request
    payload = json.dumps({
        "model": DOUBAO_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": prompt},
        ],
        "max_tokens": max_tokens,
    })
    req = urllib.request.Request(
        DOUBAO_ENDPOINT,
        data=payload.encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DOUBAO_API_KEY}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"    [Doubao警告] LLM调用失败: {e}")
        return None


def _extract_key_metrics(data, keys_to_keep):
    """从分析结果中提取关键指标，去掉大数组和无关字段以减少 prompt 体积"""
    result = {}
    for k in keys_to_keep:
        if k in data:
            v = data[k]
            if isinstance(v, dict):
                # 保留 dict，但去掉其中的大列表
                result[k] = {kk: vv for kk, vv in v.items()
                             if not isinstance(vv, list) or len(vv) <= 5}
            elif isinstance(v, list) and len(v) > 10:
                result[k] = v[:5]  # 截断过长列表
            else:
                result[k] = v
    return result


_HTML_FORMAT_INSTRUCTIONS = """
输出格式要求（严格遵守）：
1. 使用内联HTML格式，不要使用markdown
2. 每个分析维度用 <b> 加粗标题，例如：<b>盈利能力：</b>
3. 关键数值用 <b> 加粗，例如：ROE达<b>14.35%</b>
4. 正面/偏多的关键词用红色，例如：<span style="color:#dc2626">高增长</span>、<span style="color:#dc2626">低估</span>
5. 负面/偏空的关键词用绿色，例如：<span style="color:#16a34a">偏弱</span>、<span style="color:#16a34a">承压</span>
6. 中性关键词用橙色，例如：<span style="color:#d97706">中性</span>
7. 每个分析维度之间用 <br><br> 分段，形成清晰的层次结构
8. 开头用一句话总结评分和整体判断，加粗显示
9. 结尾单独一段给出总结性定性判断
10. 不要输出```html等代码块标记，直接输出HTML内容
"""


def generate_ai_summaries(fundamental, technical, capital, stock_info):
    """用 Doubao 大模型为三大维度生成专业分析总结，替换机械式拼接文本"""
    stock_name = stock_info.get("名称", "")
    stock_code = stock_info.get("代码", "")
    industry   = stock_info.get("行业", "")
    header = f"股票：{stock_name}（{stock_code}），所属行业：{industry}。\n\n"

    def _to_json(d):
        return json.dumps(d, ensure_ascii=False, default=str)

    # ── 基本面总结
    print("  [AI] 生成基本面总结...")
    fund_slim = _extract_key_metrics(fundamental, [
        "score", "profitability", "growth", "valuation", "solvency",
        "cashflow", "efficiency", "forecast", "analyst", "mainbz", "balance_detail",
    ])
    fund_prompt = (
        header +
        "以下是该股票的基本面核心指标：\n" + _to_json(fund_slim) + "\n\n"
        "请撰写400-600字的基本面分析总结。涵盖盈利能力、成长性、估值水平、偿债安全、现金流质量。"
        "如有业绩预告、券商预测、主营业务数据也需提及。结尾给出定性判断（优秀/良好/一般/偏弱）。\n"
        + _HTML_FORMAT_INSTRUCTIONS
    )
    fund_ai = call_doubao(fund_prompt, max_tokens=1000)
    if fund_ai:
        fundamental["summary"] = fund_ai

    # ── 技术面总结
    print("  [AI] 生成技术面总结...")
    tech_slim = _extract_key_metrics(technical, [
        "score", "trend", "momentum", "volume", "volatility",
        "support_resistance", "divergences", "chip_data", "nineturn",
        "family_signals", "signals",
    ])
    tech_prompt = (
        header +
        "以下是该股票的技术面核心指标：\n" + _to_json(tech_slim) + "\n\n"
        "请撰写400-600字的技术面分析总结。涵盖趋势方向、动量指标（MACD/RSI/KDJ）、量能配合、波动性。"
        "如有背离信号、筹码分布、九转指标等数据也需提及。明确指出最关键的技术信号及其含义。\n"
        + _HTML_FORMAT_INSTRUCTIONS
    )
    tech_ai = call_doubao(tech_prompt, max_tokens=1000)
    if tech_ai:
        technical["summary"] = tech_ai

    # ── 资金面总结
    print("  [AI] 生成资金面总结...")
    cap_slim = _extract_key_metrics(capital, [
        "score", "money_flow", "margin", "holders", "block_trade",
        "holdertrade", "share_float", "pledge", "hk_hold", "survey",
    ])
    cap_prompt = (
        header +
        "以下是该股票的资金与筹码面核心指标：\n" + _to_json(cap_slim) + "\n\n"
        "请撰写400-600字的资金面分析总结。涵盖主力资金流向、融资融券、股东结构、大宗交易。"
        "如有股东增减持、限售解禁、股权质押、北向资金、机构调研数据也需提及。重点分析资金面对短期走势的影响方向。\n"
        + _HTML_FORMAT_INSTRUCTIONS
    )
    cap_ai = call_doubao(cap_prompt, max_tokens=1000)
    if cap_ai:
        capital["summary"] = cap_ai


# ─── 数据采集层 ────────────────────────────────────────────────────────────────
def _date_range(days_back):
    end = datetime.now().strftime("%Y%m%d")
    start = (datetime.now() - timedelta(days=int(days_back * 1.6))).strftime("%Y%m%d")
    return start, end


def fetch_stock_basic(ts_code):
    print("  [数据] 基本信息")
    rows = curl_api("stock_basic", {"ts_code": ts_code, "list_status": "L"})
    return rows[0] if rows else {}


def fetch_daily(ts_code, n=120):
    """日线行情（取最近 n 个交易日）"""
    print("  [数据] 日线行情")
    s, e = _date_range(n)
    rows = curl_api("daily", {"ts_code": ts_code, "start_date": s, "end_date": e})
    rows.sort(key=lambda x: x.get("trade_date", ""))
    return rows[-n:] if len(rows) > n else rows


def fetch_daily_basic(ts_code, n=60):
    """每日基本面指标（PE/PB/换手率等）"""
    print("  [数据] 每日指标")
    s, e = _date_range(n)
    rows = curl_api("daily_basic", {"ts_code": ts_code, "start_date": s, "end_date": e})
    rows.sort(key=lambda x: x.get("trade_date", ""))
    return rows[-n:] if len(rows) > n else rows


def fetch_stk_factor(ts_code, n=60):
    """技术面因子（MACD/KDJ/RSI/BOLL/CCI）"""
    print("  [数据] 技术因子")
    s, e = _date_range(n)
    fields = ("ts_code,trade_date,close,"
              "macd_dif,macd_dea,macd,"
              "kdj_k,kdj_d,kdj_j,"
              "rsi_6,rsi_12,rsi_24,"
              "boll_upper,boll_mid,boll_lower,cci")
    rows = curl_api("stk_factor",
                    {"ts_code": ts_code, "start_date": s, "end_date": e},
                    fields=fields)
    rows.sort(key=lambda x: x.get("trade_date", ""))
    return rows[-n:] if len(rows) > n else rows


def fetch_fina_indicator(ts_code):
    """财务指标（近2年）"""
    print("  [数据] 财务指标")
    rows = curl_api("fina_indicator", {"ts_code": ts_code, "start_date": "20230101"})
    rows.sort(key=lambda x: x.get("ann_date", ""), reverse=True)
    return rows


def fetch_income(ts_code):
    """利润表（年报，用于营收增速）"""
    print("  [数据] 利润表")
    rows = curl_api("income", {"ts_code": ts_code, "start_date": "20210101",
                               "report_type": "1"})
    rows.sort(key=lambda x: x.get("end_date", ""), reverse=True)
    return rows


def fetch_moneyflow(ts_code, n=30):
    """个股资金流向"""
    print("  [数据] 资金流向")
    s, e = _date_range(n)
    rows = curl_api("moneyflow", {"ts_code": ts_code, "start_date": s, "end_date": e})
    rows.sort(key=lambda x: x.get("trade_date", ""))
    return rows[-n:] if len(rows) > n else rows


def fetch_margin(ts_code, n=30):
    """融资融券"""
    print("  [数据] 融资融券")
    s, e = _date_range(n)
    rows = curl_api("margin_detail",
                    {"ts_code": ts_code, "start_date": s, "end_date": e})
    rows.sort(key=lambda x: x.get("trade_date", ""))
    return rows[-n:] if len(rows) > n else rows


def fetch_top10_holders(ts_code):
    """前十大流通股东"""
    print("  [数据] 前十大股东")
    return curl_api("top10_floatholders", {"ts_code": ts_code})


def fetch_holder_number(ts_code):
    """股东户数变动（近6期）"""
    print("  [数据] 股东户数")
    rows = curl_api("stk_holdernumber", {"ts_code": ts_code})
    rows.sort(key=lambda x: x.get("ann_date", ""), reverse=True)
    return rows[:6]


def fetch_block_trade(ts_code, n=30):
    """大宗交易"""
    print("  [数据] 大宗交易")
    s, e = _date_range(n)
    return curl_api("block_trade",
                    {"ts_code": ts_code, "start_date": s, "end_date": e})


def fetch_weekly(ts_code, n=30):
    """周线行情（取最近 n 周）"""
    print("  [数据] 周线行情")
    s, e = _date_range(n * 7)
    rows = curl_api("weekly", {"ts_code": ts_code, "start_date": s, "end_date": e})
    rows.sort(key=lambda x: x.get("trade_date", ""))
    return rows[-n:] if len(rows) > n else rows


def fetch_concepts(ts_code):
    """概念板块"""
    print("  [数据] 概念板块")
    rows = curl_api("concept_detail", {"ts_code": ts_code})
    return [r.get("concept_name", "") for r in rows if r.get("concept_name")]


def fetch_report_rc(ts_code, n=90):
    """券商盈利预测（近期研报）"""
    print("  [数据] 券商盈利预测")
    s, e = _date_range(n)
    rows = curl_api("report_rc", {"ts_code": ts_code, "start_date": s, "end_date": e},
                     fields="ts_code,report_date,org_name,eps,pe,rating,max_price,min_price,np")
    rows.sort(key=lambda x: x.get("report_date", ""))
    return rows


def fetch_holdertrade(ts_code, n=180):
    """股东增减持（近半年）"""
    print("  [数据] 股东增减持")
    s, e = _date_range(n)
    return curl_api("stk_holdertrade", {"ts_code": ts_code, "start_date": s, "end_date": e})


def fetch_forecast(ts_code):
    """业绩预告"""
    print("  [数据] 业绩预告")
    return curl_api("forecast", {"ts_code": ts_code})


def fetch_balancesheet(ts_code):
    """资产负债表"""
    print("  [数据] 资产负债表")
    rows = curl_api("balancesheet", {"ts_code": ts_code, "report_type": "1"},
                     fields="ts_code,end_date,total_cur_assets,total_cur_liab,"
                            "total_assets,total_liab,total_hldr_eqy_inc_min_int,"
                            "goodwill,accounts_receiv,inventories,lt_borr,st_borr,"
                            "notes_receiv,oth_receiv")
    rows.sort(key=lambda x: x.get("end_date", ""))
    return rows


def fetch_cyq_perf(ts_code, n=10):
    """每日筹码及胜率"""
    print("  [数据] 筹码胜率")
    s, e = _date_range(n)
    return curl_api("cyq_perf", {"ts_code": ts_code, "start_date": s, "end_date": e})


def fetch_share_float(ts_code, n=90):
    """限售股解禁（未来90天）"""
    print("  [数据] 限售解禁")
    today = datetime.now()
    s = today.strftime("%Y%m%d")
    e = (today + timedelta(days=n)).strftime("%Y%m%d")
    return curl_api("share_float", {"ts_code": ts_code, "start_date": s, "end_date": e})


def fetch_mainbz(ts_code):
    """主营业务构成（按产品）"""
    print("  [数据] 主营业务构成")
    return curl_api("fina_mainbz", {"ts_code": ts_code, "type": "P"})


def fetch_pledge_stat(ts_code):
    """股权质押统计"""
    print("  [数据] 股权质押")
    rows = curl_api("pledge_stat", {"ts_code": ts_code})
    rows.sort(key=lambda x: x.get("end_date", ""))
    return rows


def fetch_hk_hold(ts_code, n=30):
    """沪深股通持股（北向资金）"""
    print("  [数据] 北向资金持股")
    s, e = _date_range(n)
    exchange = "SH" if ts_code.endswith(".SH") else "SZ"
    return curl_api("hk_hold", {"ts_code": ts_code, "start_date": s, "end_date": e,
                                 "exchange": exchange})


def fetch_stk_surv(ts_code, n=180):
    """机构调研（近半年）"""
    print("  [数据] 机构调研")
    s, e = _date_range(n)
    return curl_api("stk_surv", {"ts_code": ts_code, "start_date": s, "end_date": e},
                     fields="ts_code,surv_date,rece_org,rece_mode")


def fetch_nineturn(ts_code, n=30):
    """神奇九转指标"""
    print("  [数据] 神奇九转")
    s, e = _date_range(n)
    return curl_api("stk_nineturn", {"ts_code": ts_code, "freq": "daily",
                                      "start_date": s, "end_date": e},
                     fields="ts_code,trade_date,up_count,down_count,nine_up_turn,nine_down_turn")


# ─── 工具函数 ──────────────────────────────────────────────────────────────────
def sf(v, default=None):
    """安全浮点转换"""
    try:
        return float(v) if v is not None else default
    except (TypeError, ValueError):
        return default


def ma(series, n):
    """简单移动平均"""
    if len(series) < n:
        return None
    return sum(series[-n:]) / n


def linear_slope(series):
    """线性回归斜率（归一化到 per-step 涨跌量）"""
    n = len(series)
    if n < 3:
        return 0.0
    x_mean = (n - 1) / 2
    y_mean = sum(series) / n
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(series))
    den = sum((i - x_mean) ** 2 for i in range(n))
    return num / den if den else 0.0


def calc_atr(daily_data, n=14):
    """Average True Range"""
    if len(daily_data) < n + 1:
        return None
    trs = []
    for i in range(1, len(daily_data)):
        h = sf(daily_data[i].get("high"), 0)
        l = sf(daily_data[i].get("low"), 0)
        pc = sf(daily_data[i - 1].get("close"), 0)
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(trs[-n:]) / n if trs else None


def find_pivot_levels(daily_data, n=20):
    """通过摆动高低点寻找近期支撑/阻力位"""
    recent = daily_data[-n:] if len(daily_data) >= n else daily_data
    highs = [sf(d.get("high"), 0) for d in recent]
    lows = [sf(d.get("low"), 0) for d in recent]

    # 全周期高低
    resistance_abs = max(highs) if highs else 0
    support_abs = min(lows) if lows else 0

    # 摆动高低点（N邻近窗口=2）
    pivot_h, pivot_l = [], []
    for i in range(2, len(recent) - 2):
        if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
           highs[i] > highs[i+1] and highs[i] > highs[i+2]:
            pivot_h.append(highs[i])
        if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
           lows[i] < lows[i+1] and lows[i] < lows[i+2]:
            pivot_l.append(lows[i])

    return {
        "resistance": round(resistance_abs, 2),
        "support": round(support_abs, 2),
        "pivot_resistance": round(sorted(pivot_h)[-1], 2) if pivot_h else round(resistance_abs * 0.97, 2),
        "pivot_support": round(sorted(pivot_l)[0], 2) if pivot_l else round(support_abs * 1.03, 2),
    }


def detect_divergences(closes, highs, lows, factor_data, n=30):
    """检测价格与指标(RSI/MACD)的背离信号"""
    signals = []
    if not factor_data or len(factor_data) < n or len(closes) < n:
        return signals

    rc = closes[-n:]
    rh = highs[-n:]
    rl = lows[-n:]

    # 找摆动高点和低点（窗口=3）
    swing_highs, swing_lows = [], []
    for i in range(3, len(rc) - 3):
        if rh[i] >= max(rh[i-3:i]) and rh[i] >= max(rh[i+1:i+4]):
            swing_highs.append(i)
        if rl[i] <= min(rl[i-3:i]) and rl[i] <= min(rl[i+1:i+4]):
            swing_lows.append(i)

    # 提取对应日期的RSI和MACD DIF
    rf = factor_data[-n:]
    rsi_vals = [sf(f.get("rsi_6")) for f in rf]
    dif_vals = [sf(f.get("macd_dif")) for f in rf]

    # 顶背离：价格创新高但指标未创新高 → 看空
    if len(swing_highs) >= 2:
        i1, i2 = swing_highs[-2], swing_highs[-1]
        if rh[i2] > rh[i1]:  # 价格新高
            # RSI 顶背离
            if rsi_vals[i1] and rsi_vals[i2] and rsi_vals[i2] < rsi_vals[i1]:
                signals.append(("strong_bear", f"RSI顶背离：价格创新高但RSI走低({rsi_vals[i2]:.0f}<{rsi_vals[i1]:.0f})，警惕回调"))
            # MACD 顶背离
            if dif_vals[i1] and dif_vals[i2] and dif_vals[i2] < dif_vals[i1]:
                signals.append(("strong_bear", f"MACD顶背离：价格创新高但DIF走低，多头动能衰减"))

    # 底背离：价格创新低但指标未创新低 → 看多
    if len(swing_lows) >= 2:
        i1, i2 = swing_lows[-2], swing_lows[-1]
        if rl[i2] < rl[i1]:  # 价格新低
            # RSI 底背离
            if rsi_vals[i1] and rsi_vals[i2] and rsi_vals[i2] > rsi_vals[i1]:
                signals.append(("strong_bull", f"RSI底背离：价格创新低但RSI走高({rsi_vals[i2]:.0f}>{rsi_vals[i1]:.0f})，反弹信号"))
            # MACD 底背离
            if dif_vals[i1] and dif_vals[i2] and dif_vals[i2] > dif_vals[i1]:
                signals.append(("strong_bull", f"MACD底背离：价格创新低但DIF走高，空头动能衰减"))

    return signals


# ─── 技术面分析 ────────────────────────────────────────────────────────────────
def analyze_technical(daily_data, factor_data, cyq_perf_data=None, nineturn_data=None):
    """
    全面技术面分析，返回：
      - trend   均线趋势（MA多空排列、金叉死叉）
      - momentum MACD/RSI/KDJ/BOLL/CCI
      - volume  量能（量比、量价配合、OBV）
      - volatility ATR、支撑阻力
      - signals  [(type, description), ...]
      - score   0-100
    """
    result = {
        "score": 50, "trend": {}, "momentum": {},
        "volume": {}, "volatility": {}, "signals": [], "comment": ""
    }
    if not daily_data or len(daily_data) < 10:
        result["comment"] = "日线数据不足，跳过技术分析"
        return result

    closes = [sf(d.get("close"), 0) for d in daily_data]
    highs  = [sf(d.get("high"),  0) for d in daily_data]
    lows   = [sf(d.get("low"),   0) for d in daily_data]
    vols   = [sf(d.get("vol"),   0) for d in daily_data]
    price  = closes[-1]
    signals = []

    # ────────────────── 1. 趋势 ──────────────────
    ma5  = ma(closes, 5)
    ma10 = ma(closes, 10)
    ma20 = ma(closes, 20)
    ma60 = ma(closes, 60)

    trend = {
        "current_price": price,
        "MA5":  round(ma5,  2) if ma5  else None,
        "MA10": round(ma10, 2) if ma10 else None,
        "MA20": round(ma20, 2) if ma20 else None,
        "MA60": round(ma60, 2) if ma60 else None,
    }

    # 均线排列
    if ma5 and ma10 and ma20 and ma60:
        if ma5 > ma10 > ma20 > ma60:
            trend["均线排列"] = "多头排列（强势）"
            signals.append(("strong_bull", "均线完美多头排列，趋势强劲上行"))
        elif ma5 < ma10 < ma20 < ma60:
            trend["均线排列"] = "空头排列（弱势）"
            signals.append(("strong_bear", "均线空头排列，趋势持续下行"))
        elif ma5 > ma20:
            trend["均线排列"] = "短期偏多"
            signals.append(("bull", "短期均线高于中期，短线偏多"))
        else:
            trend["均线排列"] = "短期偏空"
            signals.append(("bear", "短期均线低于中期，短线偏空"))

    # 价格与MA20位置
    if ma20:
        diff_pct = (price - ma20) / ma20 * 100
        trend["距MA20(%)"] = round(diff_pct, 2)
        if diff_pct > 8:
            signals.append(("weak_bear", f"股价严重偏离MA20上方({diff_pct:+.1f}%)，短期回调压力大"))
        elif diff_pct > 2:
            signals.append(("bull", f"股价站上MA20 {diff_pct:+.1f}%，趋势偏多"))
        elif diff_pct < -8:
            signals.append(("weak_bull", f"股价严重偏离MA20下方({diff_pct:+.1f}%)，存在超跌反弹机会"))
        elif diff_pct < -2:
            signals.append(("bear", f"股价跌破MA20 {diff_pct:+.1f}%，趋势偏空"))

    # 5日/20日金叉/死叉（需前日数据）
    if ma5 and ma20 and len(closes) >= 21:
        prev_ma5  = ma(closes[:-1], 5)
        prev_ma20 = ma(closes[:-1], 20)
        if prev_ma5 and prev_ma20:
            if prev_ma5 <= prev_ma20 and ma5 > ma20:
                signals.append(("strong_bull", "MA5上穿MA20，形成黄金交叉 —— 中线看多信号"))
            elif prev_ma5 >= prev_ma20 and ma5 < ma20:
                signals.append(("strong_bear", "MA5下穿MA20，形成死亡交叉 —— 中线看空信号"))

    # 20日线性趋势斜率
    slope = linear_slope(closes[-20:] if len(closes) >= 20 else closes)
    trend["近20日线性趋势"] = "上升" if slope > 0 else "下降"
    result["trend"] = trend

    # ────────────────── 2. 动量 ──────────────────
    momentum = {}
    if factor_data and len(factor_data) >= 2:
        f0 = factor_data[-1]   # 最新
        f1 = factor_data[-2]   # 前一日

        def _f(key): return sf(f0.get(key))
        def _fp(key): return sf(f1.get(key))

        # MACD
        dif, dea, hist = _f("macd_dif"), _f("macd_dea"), _f("macd")
        if dif is not None and dea is not None:
            momentum.update({"MACD_DIF": round(dif, 4),
                             "MACD_DEA": round(dea, 4),
                             "MACD_柱": round(hist, 4) if hist else None})
            # 金叉/死叉
            p_dif, p_dea = _fp("macd_dif"), _fp("macd_dea")
            if p_dif is not None and p_dea is not None:
                if p_dif <= p_dea and dif > dea:
                    signals.append(("strong_bull", "MACD DIF上穿DEA，金叉买入信号"))
                elif p_dif >= p_dea and dif < dea:
                    signals.append(("strong_bear", "MACD DIF下穿DEA，死叉卖出信号"))
            # 零轴位置
            if dif > 0 and dea > 0:
                signals.append(("bull", "MACD双线位于零轴上方，多头市场"))
            elif dif < 0 and dea < 0:
                signals.append(("bear", "MACD双线位于零轴下方，空头市场"))
            # 柱状线趋势
            if hist and f1.get("macd"):
                p_hist = sf(f1.get("macd"))
                momentum["MACD_柱趋势"] = "扩张" if abs(hist) > abs(p_hist or 0) else "收敛"

        # RSI
        rsi6, rsi12 = _f("rsi_6"), _f("rsi_12")
        if rsi6 is not None:
            momentum.update({"RSI_6": round(rsi6, 2),
                             "RSI_12": round(rsi12, 2) if rsi12 else None})
            if rsi6 > 80:
                signals.append(("bear", f"RSI_6={rsi6:.1f}，强超买——回调风险高"))
            elif rsi6 > 70:
                signals.append(("weak_bear", f"RSI_6={rsi6:.1f}，接近超买，谨慎追高"))
            elif rsi6 < 20:
                signals.append(("strong_bull", f"RSI_6={rsi6:.1f}，深度超卖——超跌反弹机会大"))
            elif rsi6 < 30:
                signals.append(("bull", f"RSI_6={rsi6:.1f}，进入超卖区间"))

        # KDJ
        k, d, j = _f("kdj_k"), _f("kdj_d"), _f("kdj_j")
        pk, pd = _fp("kdj_k"), _fp("kdj_d")
        if k is not None and d is not None:
            momentum.update({"KDJ_K": round(k, 2), "KDJ_D": round(d, 2),
                             "KDJ_J": round(j, 2) if j else None})
            # 金叉死叉（低位/高位更有效）
            if pk is not None and pd is not None:
                if pk <= pd and k > d and k < 50:
                    signals.append(("bull", f"KDJ低位({k:.0f})金叉，短线买入信号"))
                elif pk >= pd and k < d and k > 70:
                    signals.append(("bear", f"KDJ高位({k:.0f})死叉，短线卖出信号"))
            if j and j > 100:
                signals.append(("weak_bear", f"KDJ_J={j:.1f}，极度超买"))
            elif j and j < 0:
                signals.append(("weak_bull", f"KDJ_J={j:.1f}，极度超卖"))

        # BOLL
        bu, bm, bl = _f("boll_upper"), _f("boll_mid"), _f("boll_lower")
        if bu and bm and bl:
            width_pct = (bu - bl) / bm * 100
            momentum.update({"BOLL_上": round(bu, 2), "BOLL_中": round(bm, 2),
                             "BOLL_下": round(bl, 2), "BOLL_带宽(%)": round(width_pct, 2)})
            if price >= bu:
                signals.append(("bear", f"股价触及/突破布林上轨({bu:.2f})，面临压制"))
            elif price <= bl:
                signals.append(("bull", f"股价触及/突破布林下轨({bl:.2f})，具备强支撑"))
            elif price > bm:
                momentum["BOLL_位置"] = "中上轨（偏强）"
            else:
                momentum["BOLL_位置"] = "中下轨（偏弱）"
            # 带宽收窄预警（可能有大行情）
            if width_pct < 5:
                momentum["BOLL_预警"] = "带宽极度收窄，注意方向性突破"

        # CCI
        cci = _f("cci")
        if cci is not None:
            momentum["CCI"] = round(cci, 2)
            if cci > 200:
                signals.append(("bear", f"CCI={cci:.0f}，极度超买"))
            elif cci > 100:
                signals.append(("weak_bear", f"CCI={cci:.0f}，超买区间"))
            elif cci < -200:
                signals.append(("bull", f"CCI={cci:.0f}，极度超卖"))
            elif cci < -100:
                signals.append(("weak_bull", f"CCI={cci:.0f}，超卖区间"))

    result["momentum"] = momentum

    # ────────────────── 3. 量能 ──────────────────
    avg_vol = ma(vols, 20) or (sum(vols) / len(vols) if vols else 1)
    latest_vol = vols[-1] if vols else 0
    vol_ratio = latest_vol / avg_vol if avg_vol else 1

    # 5日量能变化
    r5_vol = sum(vols[-5:]) / 5 if len(vols) >= 5 else avg_vol
    p5_vol = sum(vols[-10:-5]) / 5 if len(vols) >= 10 else avg_vol
    vol_expand = r5_vol / p5_vol if p5_vol else 1

    # 近5日价格变化
    price_5d = (closes[-1] - closes[-6]) / closes[-6] * 100 if len(closes) >= 6 and closes[-6] else 0

    volume = {
        "量比": round(vol_ratio, 2),
        "近5日量能变化(%)": round((vol_expand - 1) * 100, 1),
        "近5日价格变化(%)": round(price_5d, 2),
    }

    if price_5d > 3 and vol_expand > 1.2:
        signals.append(("strong_bull", f"价涨量增（量能扩大{(vol_expand-1)*100:.0f}%），上涨动能充分"))
    elif price_5d > 0 and vol_expand < 0.8:
        signals.append(("weak_bear", "价涨量缩，上涨动能不足，需警惕假突破"))
    elif price_5d < -3 and vol_expand > 1.2:
        signals.append(("bear", "价跌量增，空头力量较强，跌势可能延续"))
    elif price_5d < 0 and vol_expand < 0.8:
        signals.append(("weak_bull", "价跌量缩，抛压减弱，下跌动能衰减"))

    # OBV 趋势（简化）
    if len(closes) >= 10:
        obv, obv_series = 0.0, []
        for i in range(1, len(closes)):
            obv += vols[i] if closes[i] > closes[i-1] else (-vols[i] if closes[i] < closes[i-1] else 0)
            obv_series.append(obv)
        if len(obv_series) >= 10:
            obv_slope = linear_slope(obv_series[-10:])
            volume["OBV趋势"] = "上升" if obv_slope > 0 else "下降"
            if obv_slope > 0 and price_5d > 0:
                signals.append(("bull", "OBV能量潮上升，量价共振确认多头"))
            elif obv_slope < 0 and price_5d < 0:
                signals.append(("bear", "OBV能量潮下降，量价共振确认空头"))

    result["volume"] = volume

    # ────────────────── 4. 波动性 ──────────────────
    atr = calc_atr(daily_data, 14)
    atr_pct = atr / price * 100 if atr and price else None
    sr = find_pivot_levels(daily_data, 20)

    result["volatility"] = {
        "ATR_14":     round(atr, 3) if atr else None,
        "ATR_%(日波幅预期)": round(atr_pct, 2) if atr_pct else None,
        "支撑位(20日低点)":  sr["support"],
        "阻力位(20日高点)":  sr["resistance"],
        "近期关键支撑":      sr["pivot_support"],
        "近期关键阻力":      sr["pivot_resistance"],
    }
    if atr_pct:
        if atr_pct > 4:
            signals.append(("weak_bear", f"ATR={atr_pct:.1f}%，波动率较高，风险偏大"))
        elif atr_pct < 1.5:
            signals.append(("weak_bull", f"ATR={atr_pct:.1f}%，低波动，趋势稳定"))

    # ────────────────── 5. 背离检测 ──────────────────
    div_signals = detect_divergences(closes, highs, lows, factor_data, 30)
    signals.extend(div_signals)
    if div_signals:
        result["divergence"] = [{"type": s[0], "desc": s[1]} for s in div_signals]

    # ────────────────── 6. 筹码胜率 ──────────────────
    if cyq_perf_data:
        sorted_cyq = sorted(cyq_perf_data, key=lambda x: x.get("trade_date", ""))
        if sorted_cyq:
            latest_cyq = sorted_cyq[-1]
            wr = sf(latest_cyq.get("winner_rate"))
            wavg = sf(latest_cyq.get("weight_avg"))
            cost50 = sf(latest_cyq.get("cost_50pct"))
            result["chip_data"] = {
                "获利盘比例(%)": round(wr, 2) if wr else None,
                "加权平均成本": round(wavg, 2) if wavg else None,
                "50分位成本": round(cost50, 2) if cost50 else None,
                "5分位成本": round(sf(latest_cyq.get("cost_5pct")), 2) if sf(latest_cyq.get("cost_5pct")) else None,
                "95分位成本": round(sf(latest_cyq.get("cost_95pct")), 2) if sf(latest_cyq.get("cost_95pct")) else None,
            }
            if wr is not None:
                if wr > 90:
                    signals.append(("weak_bear", f"获利盘{wr:.0f}%，市场浮盈过大，注意获利回吐"))
                elif wr < 10:
                    signals.append(("bull", f"获利盘仅{wr:.0f}%，大面积套牢，抛压衰竭"))
            if wavg and price:
                cost_ratio = (price - wavg) / wavg * 100
                result["chip_data"]["偏离加权成本(%)"] = round(cost_ratio, 1)

    # ────────────────── 7. 神奇九转 ──────────────────
    if nineturn_data:
        sorted_nt = sorted(nineturn_data, key=lambda x: x.get("trade_date", ""))
        if sorted_nt:
            latest_nt = sorted_nt[-1]
            nine_up = latest_nt.get("nine_up_turn")
            nine_down = latest_nt.get("nine_down_turn")
            up_count = sf(latest_nt.get("up_count"), 0)
            down_count = sf(latest_nt.get("down_count"), 0)
            result["nineturn"] = {
                "上九转计数": int(up_count),
                "下九转计数": int(down_count),
                "九转触发": nine_up or nine_down or "无",
            }
            if nine_up and "+9" in str(nine_up):
                signals.append(("strong_bear", "神奇九转上九转触发，连涨9日见顶信号"))
            elif nine_down and "-9" in str(nine_down):
                signals.append(("strong_bull", "神奇九转下九转触发，连跌9日见底信号"))
            elif up_count >= 7:
                signals.append(("weak_bear", f"上九转计数{int(up_count)}，接近顶部反转"))
            elif down_count >= 7:
                signals.append(("weak_bull", f"下九转计数{int(down_count)}，接近底部反转"))

    # ────────────────── 信号族聚合（去重） ──────────────────
    result["signals"] = signals

    # 将信号分组为独立信号族，族内取代表信号避免相关信号重复投票
    SIGNAL_FAMILIES = {
        "TREND":    ["均线", "MA", "金叉", "死叉", "趋势"],
        "MOMENTUM": ["MACD", "RSI", "KDJ", "BOLL", "CCI", "布林", "背离", "九转"],
        "VOLUME":   ["量", "OBV", "量价", "量能"],
        "VOLATILITY": ["ATR", "波动"],
        "CHIP":     ["获利盘", "筹码", "套牢"],
    }
    w = {"strong_bull": 2.0, "bull": 1.5, "weak_bull": 0.8,
         "weak_bear": -0.8, "bear": -1.5, "strong_bear": -2.0}

    def _classify(msg):
        for fam, keywords in SIGNAL_FAMILIES.items():
            if any(kw in msg for kw in keywords):
                return fam
        return "OTHER"

    families = {}
    for sig_type, sig_msg in signals:
        fam = _classify(sig_msg)
        families.setdefault(fam, []).append((sig_type, sig_msg))

    # 族内聚合：取最强信号，但按族内一致性调整权重
    family_signals = []
    for fam, sigs in families.items():
        bull_w = sum(w[s[0]] for s in sigs if w.get(s[0], 0) > 0)
        bear_w = sum(abs(w[s[0]]) for s in sigs if w.get(s[0], 0) < 0)
        # 取族内绝对值最大的信号作为代表
        best = max(sigs, key=lambda s: abs(w.get(s[0], 0)))
        # 一致性系数：族内同方向占比越高，信号越可靠
        total_sigs = len(sigs)
        if bull_w > bear_w:
            agreement = sum(1 for s in sigs if w.get(s[0], 0) > 0) / total_sigs
        elif bear_w > bull_w:
            agreement = sum(1 for s in sigs if w.get(s[0], 0) < 0) / total_sigs
        else:
            agreement = 0.5
        family_signals.append((best[0], best[1], fam, round(agreement, 2)))

    result["family_signals"] = family_signals

    # 使用聚合后的族信号计算技术评分（避免相关信号膨胀）
    net = sum(w.get(fs[0], 0) * fs[3] for fs in family_signals)
    max_w = len(family_signals) * 2.0 if family_signals else 1
    score = 50 + (net / max_w) * 45
    result["score"] = max(0, min(100, round(score, 1)))

    bull_n = sum(1 for s in signals if "bull" in s[0])
    bear_n = sum(1 for s in signals if "bear" in s[0])
    if bull_n > bear_n + 1:
        result["comment"] = f"技术面偏多 ▲，看多信号{bull_n}个 vs 看空{bear_n}个"
    elif bear_n > bull_n + 1:
        result["comment"] = f"技术面偏空 ▼，看空信号{bear_n}个 vs 看多{bull_n}个"
    else:
        result["comment"] = f"技术面中性，多空信号均衡（多{bull_n} 空{bear_n}）"

    # ── 生成技术面综合摘要（HTML格式）──
    def _score_color(s):
        return "#dc2626" if s >= 60 else "#d97706" if s >= 40 else "#16a34a"
    def _fv(v):
        try: return float(str(v).replace("+","").replace("%",""))
        except: return 0

    sc = result["score"]
    parts = [f'<b style="font-size:14px">技术面综合评分 <span style="color:{_score_color(sc)}">{sc}分</span></b>']

    # 趋势
    tr = result.get("trend", {})
    ma_arr = tr.get("均线排列", "")
    if ma_arr:
        slope = tr.get("20日线性趋势斜率")
        price_vs_ma = tr.get("股价vs MA20", "")
        t_clr = "#dc2626" if "多头" in ma_arr else "#16a34a" if "空头" in ma_arr else "#d97706"
        t_parts = [f'<span style="color:{t_clr}"><b>{ma_arr}</b></span>']
        if price_vs_ma: t_parts.append(f"股价{price_vs_ma}")
        if slope is not None: t_parts.append(f"20日趋势斜率<b>{slope}</b>")
        parts.append(f'<b>趋势：</b>{"，".join(t_parts)}')

    # 动量
    mo = result.get("momentum", {})
    macd_dif = mo.get("MACD_DIF")
    macd_st = mo.get("MACD状态", "")
    if macd_dif is not None or macd_st:
        rsi_v = mo.get("RSI_6")
        kdj_k = mo.get("KDJ_K")
        boll_pos = mo.get("BOLL位置", "")
        # 判断MACD状态
        if not macd_st:
            macd_st = "零轴上方" if macd_dif and macd_dif > 0 else "零轴下方"
        m_clr = "#dc2626" if "金叉" in macd_st or "零轴上方" in macd_st else "#16a34a" if "死叉" in macd_st or "零轴下方" in macd_st else "#d97706"
        parts.append(f'<b>动量：</b>MACD <span style="color:{m_clr}"><b>{macd_st}</b></span>'
                     f'{"(DIF=" + str(round(macd_dif,2)) + ")" if macd_dif else ""}，'
                     f'RSI(6)=<b>{rsi_v}</b>，KDJ_K=<b>{kdj_k}</b>'
                     + (f"，布林带{boll_pos}" if boll_pos else ""))

    # 量能
    vo = result.get("volume", {})
    vr = vo.get("量比(最新/20均)") or vo.get("量比")
    if vr:
        vp = vo.get("量价配合", "")
        obv = vo.get("OBV趋势", "")
        vp_clr = "#dc2626" if vp and "价涨量增" in vp else "#16a34a" if vp and "价跌" in vp else "#d97706"
        vp_str = f'，<span style="color:{vp_clr}">{vp}</span>' if vp else ""
        parts.append(f'<b>量能：</b>量比<b>{vr}</b>{vp_str}，OBV{obv}')

    # 波动
    vl = result.get("volatility", {})
    atr_pct = vl.get("ATR_%(日波幅预期)")
    if atr_pct:
        supp = vl.get("近期关键支撑")
        resis = vl.get("近期关键阻力")
        risk_clr = "#dc2626" if atr_pct > 4 else "#d97706" if atr_pct > 2 else "#16a34a"
        parts.append(f'<b>波动：</b>日均波幅<span style="color:{risk_clr}"><b>{atr_pct}%</b></span>，'
                     f'支撑<b style="color:#16a34a">{supp}</b>，阻力<b style="color:#dc2626">{resis}</b>')

    # 筹码
    cd = result.get("chip_data", {})
    cdd = cd.get("data", {}) if "data" in cd else cd
    wr = cdd.get("获利比例(%)") or cdd.get("获利盘比例(%)")
    if wr is not None:
        wr_clr = "#dc2626" if _fv(wr) > 50 else "#d97706" if _fv(wr) > 20 else "#16a34a"
        parts.append(f'<b>筹码：</b>获利比例<span style="color:{wr_clr}"><b>{wr}%</b></span>，'
                     f'加权成本<b>{cdd.get("加权平均成本","")}</b>。{cd.get("comment","")}')

    # 九转
    nt = result.get("nineturn", {})
    ntd = nt.get("data", {}) if "data" in nt else nt
    if ntd:
        up_c = ntd.get("上涨计数") or ntd.get("上九转计数", 0)
        dn_c = ntd.get("下跌计数") or ntd.get("下九转计数", 0)
        nt_trigger = ntd.get("九转触发", "")
        nt_comment = nt.get("comment", "")
        if up_c or dn_c or nt_trigger:
            trigger_str = ""
            if nt_trigger and nt_trigger != "无":
                t_clr = "#dc2626" if "上" in nt_trigger else "#16a34a"
                trigger_str = f'，触发 <span style="color:{t_clr}"><b>{nt_trigger}</b></span>'
            parts.append(f'<b>九转：</b>上涨计数<b>{up_c}</b>，下跌计数<b>{dn_c}</b>{trigger_str}。{nt_comment}')

    # 信号汇总
    sig_parts = []
    for s in signals[:5]:
        s_clr = "#dc2626" if "bull" in s[0] else "#16a34a" if "bear" in s[0] else "#d97706"
        sig_parts.append(f'<span style="color:{s_clr}">{s[1]}</span>')
    parts.append(f'<b>信号汇总：</b>共<b>{len(signals)}</b>个（'
                 f'<span style="color:#dc2626">多{bull_n}</span> '
                 f'<span style="color:#16a34a">空{bear_n}</span>）：{"、".join(sig_parts)}')

    # 族聚合
    if family_signals:
        fam_parts = []
        for fs in family_signals:
            f_clr = "#dc2626" if "bull" in fs[0] else "#16a34a" if "bear" in fs[0] else "#d97706"
            fam_parts.append(f'<span style="color:{f_clr}">{fs[2]}({fs[0]})</span>')
        parts.append(f'<b>族聚合：</b>保留{len(family_signals)}个独立信号：{"、".join(fam_parts)}')

    result["summary"] = "<br>".join(parts)

    return result


# ─── 基本面分析 ────────────────────────────────────────────────────────────────
def analyze_fundamental(stock_basic, fina_data, daily_basic, income_data,
                         balancesheet=None, forecast_data=None,
                         mainbz_data=None, report_rc=None):
    """
    多维基本面：盈利/成长/估值/偿债/现金流/运营效率 + 业绩预告/业务构成/券商预测
    """
    result = {
        "score": 50,
        "profitability": {"score": 50, "data": {}, "comment": ""},
        "growth":        {"score": 50, "data": {}, "comment": ""},
        "valuation":     {"score": 50, "data": {}, "comment": ""},
        "solvency":      {"score": 50, "data": {}, "comment": ""},
        "cashflow":      {"score": 50, "data": {}, "comment": ""},
        "efficiency":    {"score": 50, "data": {}, "comment": ""},
        "comment": ""
    }
    if not fina_data:
        result["comment"] = "财务数据获取失败，跳过基本面分析"
        return result

    latest = fina_data[0]
    sub_scores = []

    # ── 1. 盈利能力 ──
    roe  = sf(latest.get("roe_waa")) or sf(latest.get("roe"))
    roa  = sf(latest.get("roa"))  or sf(latest.get("roa2"))
    npm  = sf(latest.get("netprofit_margin"))
    gpm  = sf(latest.get("grossprofit_margin"))
    eps  = sf(latest.get("eps"))

    ps = 50
    ps += (25 if roe and roe > 20 else 18 if roe and roe > 15
           else 10 if roe and roe > 10 else 2 if roe and roe > 5
           else -5 if roe and roe > 0 else -20) if roe else 0
    ps += (10 if npm and npm > 30 else 5 if npm and npm > 15
           else 0 if npm and npm > 0 else -10) if npm else 0
    ps = max(0, min(100, ps))
    sub_scores.append(ps)
    result["profitability"] = {
        "score": ps,
        "data": {
            "ROE_加权(%)":  f"{roe:.2f}" if roe else "N/A",
            "ROA(%)":       f"{roa:.2f}" if roa else "N/A",
            "净利率(%)":    f"{npm:.2f}" if npm else "N/A",
            "毛利率(%)":    f"{gpm:.2f}" if gpm else "N/A",
            "每股收益(EPS)": f"{eps:.3f}" if eps else "N/A",
        },
        "comment": (f"ROE {roe:.1f}% —— "
                    + ("优秀" if roe and roe > 20 else "良好" if roe and roe > 15
                       else "一般" if roe and roe > 10 else "偏弱" if roe and roe > 0
                       else "亏损")) if roe else "数据缺失"
    }

    # ── 2. 成长能力 ──
    rev_yoy    = sf(latest.get("or_yoy"))
    profit_yoy = sf(latest.get("netprofit_yoy"))

    # 多期营收增速
    rev_trend = []
    if income_data and len(income_data) >= 2:
        for i in range(min(3, len(income_data) - 1)):
            cr = sf(income_data[i].get("total_revenue"))
            pr = sf(income_data[i + 1].get("total_revenue"))
            if cr and pr and pr > 0:
                rev_trend.append(round((cr - pr) / abs(pr) * 100, 1))

    gs = 50
    gs += (20 if rev_yoy and rev_yoy > 30 else 12 if rev_yoy and rev_yoy > 15
           else 5 if rev_yoy and rev_yoy > 5 else 0 if rev_yoy and rev_yoy > 0
           else -8 if rev_yoy and rev_yoy > -10 else -20) if rev_yoy else 0
    gs += (15 if profit_yoy and profit_yoy > 50 else 8 if profit_yoy and profit_yoy > 20
           else 2 if profit_yoy and profit_yoy > 0 else -8 if profit_yoy and profit_yoy > -20
           else -15) if profit_yoy else 0
    gs = max(0, min(100, gs))
    sub_scores.append(gs)
    result["growth"] = {
        "score": gs,
        "data": {
            "营收同比(%)":      f"{rev_yoy:+.2f}" if rev_yoy else "N/A",
            "净利润同比(%)":    f"{profit_yoy:+.2f}" if profit_yoy else "N/A",
            "历年营收增速趋势": [f"{g:+.1f}%" for g in rev_trend] if rev_trend else "N/A",
        },
        "comment": (f"营收{'+' if rev_yoy and rev_yoy > 0 else ''}{rev_yoy:.1f}%，"
                    f"净利{'+' if profit_yoy and profit_yoy > 0 else ''}{profit_yoy:.1f}%") if rev_yoy and profit_yoy else "增速数据缺失"
    }

    # ── 3. 估值水平 ──
    vs = 50
    val_data = {}
    if daily_basic:
        lb = daily_basic[-1]
        pe  = sf(lb.get("pe_ttm")) or sf(lb.get("pe"))
        pb  = sf(lb.get("pb"))
        ps_ = sf(lb.get("ps_ttm"))
        dv  = sf(lb.get("dv_ttm"))

        peg = None
        if pe and pe > 0 and profit_yoy and profit_yoy > 0:
            peg = pe / profit_yoy

        val_data = {
            "PE_TTM":      f"{pe:.2f}" if pe else "N/A",
            "PB":          f"{pb:.2f}" if pb else "N/A",
            "PS_TTM":      f"{ps_:.2f}" if ps_ else "N/A",
            "股息率_TTM(%)": f"{dv:.2f}" if dv else "N/A",
            "PEG":         f"{peg:.2f}" if peg else "N/A",
        }
        if peg is not None and peg > 0:
            vs += (25 if peg < 0.5 else 15 if peg < 1.0 else 5 if peg < 1.5 else 0 if peg < 2.0 else -10)
        elif pe and pe > 0:
            vs += (20 if pe < 15 else 10 if pe < 25 else 0 if pe < 40 else -10 if pe < 60 else -20)
        elif pe and pe < 0:
            vs -= 20
        if pb and pb > 0:
            vs += (10 if pb < 1 else 5 if pb < 2 else 0 if pb < 4 else -5)
        if dv and dv > 3:
            vs += 10
        vs = max(0, min(100, vs))

    sub_scores.append(vs)
    peg_comment = ""
    if val_data.get("PEG") and val_data["PEG"] != "N/A":
        peg_val = float(val_data["PEG"])
        peg_comment = f"，PEG={peg_val:.2f}" + ("(严重低估)" if peg_val < 0.5 else "(合理偏低)" if peg_val < 1.0 else "(合理)" if peg_val < 1.5 else "(偏高)")
    result["valuation"] = {
        "score": vs,
        "data": val_data,
        "comment": ("低估值，安全边际高" if vs >= 70 else
                    "估值合理" if vs >= 50 else "估值偏高，需关注") + peg_comment
    }

    # ── 4. 偿债能力 ──
    cur  = sf(latest.get("current_ratio"))
    qr   = sf(latest.get("quick_ratio"))
    d2a  = sf(latest.get("debt_to_assets"))

    ss = 50
    ss += (15 if cur and cur > 2 else 8 if cur and cur > 1.5 else 0 if cur and cur > 1 else -20) if cur else 0
    ss += (15 if d2a and d2a < 30 else 5 if d2a and d2a < 50 else 0 if d2a and d2a < 70 else -15) if d2a else 0
    ss = max(0, min(100, ss))
    sub_scores.append(ss)
    result["solvency"] = {
        "score": ss,
        "data": {
            "流动比率":      f"{cur:.2f}" if cur else "N/A",
            "速动比率":      f"{qr:.2f}" if qr else "N/A",
            "资产负债率(%)": f"{d2a:.2f}" if d2a else "N/A",
        },
        "comment": ("财务稳健，偿债能力强" if ss >= 70 else
                    "偿债能力一般" if ss >= 50 else "负债率偏高，关注偿债压力")
    }

    # ── 5. 现金流质量 ──
    ocfps = sf(latest.get("ocfps"))
    eps_v = sf(latest.get("eps"), 0)

    cs = 50
    cf_comment = "现金流数据缺失"
    if ocfps:
        if ocfps > 0 and ocfps > (eps_v or 0):
            cs += 20
            cf_comment = "经营现金流>净利润，利润质量高"
        elif ocfps > 0:
            cs += 8
            cf_comment = "经营现金流为正，现金盈利能力尚可"
        else:
            cs -= 15
            cf_comment = "经营现金流为负，利润质量存疑"
    cs = max(0, min(100, cs))
    sub_scores.append(cs)
    result["cashflow"] = {
        "score": cs,
        "data": {"每股经营现金流": f"{ocfps:.3f}" if ocfps else "N/A"},
        "comment": cf_comment
    }

    # ── 6. 运营效率 ──
    at  = sf(latest.get("assets_turn"))
    inv = sf(latest.get("inv_turn"))
    ar  = sf(latest.get("ar_turn"))

    es = 50
    if at:
        es += (15 if at > 1 else 5 if at > 0.5 else 0)
    es = max(0, min(100, es))
    sub_scores.append(es)
    result["efficiency"] = {
        "score": es,
        "data": {
            "总资产周转率":    f"{at:.3f}"  if at  else "N/A",
            "存货周转率":      f"{inv:.2f}" if inv else "N/A",
            "应收账款周转率":  f"{ar:.2f}"  if ar  else "N/A",
        },
        "comment": "运营效率较高" if es >= 65 else "运营效率一般"
    }

    # ── 7. 业绩预告（事件驱动） ──
    fc_score = 50
    fc_data = {}
    if forecast_data:
        # 取最新一条业绩预告
        latest_fc = sorted(forecast_data, key=lambda x: x.get("ann_date", ""))
        if latest_fc:
            lfc = latest_fc[-1]
            fc_type = lfc.get("type", "")
            p_min = sf(lfc.get("p_change_min"), 0)
            p_max = sf(lfc.get("p_change_max"), 0)
            fc_data = {
                "预告类型": fc_type,
                "净利变动幅度": f"{p_min:.1f}% ~ {p_max:.1f}%",
                "报告期": lfc.get("end_date", ""),
                "公告日期": lfc.get("ann_date", ""),
            }
            if fc_type in ("预增", "扭亏"):
                fc_score += 20
            elif fc_type in ("略增", "续盈"):
                fc_score += 10
            elif fc_type in ("略减",):
                fc_score -= 10
            elif fc_type in ("预减", "首亏", "续亏"):
                fc_score -= 20
    fc_score = max(0, min(100, fc_score))
    result["forecast"] = {"score": fc_score, "data": fc_data,
                           "comment": f"业绩预告：{fc_data.get('预告类型', '暂无')}" if fc_data else "暂无业绩预告"}

    # ── 8. 主营业务构成 ──
    bz_data = {}
    if mainbz_data:
        # 取最新报告期的产品分布
        latest_period = max(r.get("end_date", "") for r in mainbz_data) if mainbz_data else ""
        period_rows = [r for r in mainbz_data if r.get("end_date") == latest_period]
        total_sales = sum(sf(r.get("bz_sales"), 0) for r in period_rows)
        if total_sales > 0:
            top_bz = sorted(period_rows, key=lambda r: sf(r.get("bz_sales"), 0), reverse=True)[:5]
            bz_data = {
                "报告期": latest_period,
                "业务数量": len(period_rows),
                "主要业务": [{
                    "名称": r.get("bz_item", ""),
                    "收入占比": f"{sf(r.get('bz_sales'), 0) / total_sales * 100:.1f}%",
                } for r in top_bz],
            }
    result["mainbz"] = {"data": bz_data, "comment": f"共{bz_data.get('业务数量', 0)}项业务" if bz_data else "暂无数据"}

    # ── 9. 券商盈利预测（一致预期） ──
    rc_score = 50
    rc_data = {}
    if report_rc:
        recent = report_rc[-20:]  # 取最近20条
        ratings = [r.get("rating", "") for r in recent if r.get("rating")]
        max_prices = [sf(r.get("max_price")) for r in recent if sf(r.get("max_price"))]
        min_prices = [sf(r.get("min_price")) for r in recent if sf(r.get("min_price"))]
        eps_preds  = [sf(r.get("eps")) for r in recent if sf(r.get("eps"))]

        buy_count = sum(1 for r in ratings if "买入" in r or "增持" in r or "推荐" in r)
        hold_count = sum(1 for r in ratings if "中性" in r or "持有" in r)
        sell_count = sum(1 for r in ratings if "减持" in r or "卖出" in r)

        rc_data = {
            "近期研报数": len(recent),
            "评级分布": f"买入/增持{buy_count} 中性{hold_count} 减持{sell_count}",
        }
        if max_prices:
            avg_max = sum(max_prices) / len(max_prices)
            avg_min = sum(min_prices) / len(min_prices) if min_prices else avg_max * 0.8
            rc_data["一致目标价"] = f"{avg_min:.2f} ~ {avg_max:.2f}"
        if eps_preds:
            rc_data["预测EPS均值"] = f"{sum(eps_preds) / len(eps_preds):.2f}"

        # 评级倾向加分
        if buy_count > hold_count + sell_count:
            rc_score += 15
        elif sell_count > buy_count:
            rc_score -= 15
    rc_score = max(0, min(100, rc_score))
    result["analyst"] = {"score": rc_score, "data": rc_data,
                          "comment": f"券商覆盖{rc_data.get('近期研报数', 0)}篇" if rc_data else "暂无券商覆盖"}

    # ── 10. 资产负债表增强 ──
    bs_data = {}
    if balancesheet:
        lbs = balancesheet[-1]  # 最新一期
        goodwill = sf(lbs.get("goodwill"), 0)
        total_assets = sf(lbs.get("total_assets"), 0)
        acct_recv = sf(lbs.get("accounts_receiv"), 0)
        st_borr = sf(lbs.get("st_borr"), 0)
        lt_borr = sf(lbs.get("lt_borr"), 0)
        equity = sf(lbs.get("total_hldr_eqy_inc_min_int"), 0)
        interest_debt = st_borr + lt_borr
        bs_data["有息负债(亿)"] = round(interest_debt / 1e8, 2) if interest_debt else 0
        bs_data["商誉(亿)"] = round(goodwill / 1e8, 2) if goodwill else 0
        bs_data["应收账款(亿)"] = round(acct_recv / 1e8, 2) if acct_recv else 0
        if total_assets > 0:
            bs_data["商誉占比(%)"] = round(goodwill / total_assets * 100, 2)
            bs_data["应收占比(%)"] = round(acct_recv / total_assets * 100, 2)
        if equity > 0:
            bs_data["有息负债/净资产(%)"] = round(interest_debt / equity * 100, 2)
    result["balance_detail"] = {"data": bs_data,
                                 "comment": ("商誉风险需关注" if bs_data.get("商誉占比(%)", 0) > 20
                                             else "资产结构健康" if bs_data else "暂无数据")}

    # 加权合成（原6维 + 业绩预告 + 券商预期作为调节项）
    weights = [0.25, 0.20, 0.20, 0.15, 0.10, 0.10]
    base_score = round(sum(s * w for s, w in zip(sub_scores, weights)), 1)
    # 业绩预告和券商预期作为调节（±5分）
    adj = 0
    if fc_score > 60:
        adj += (fc_score - 50) * 0.1
    elif fc_score < 40:
        adj += (fc_score - 50) * 0.1
    if rc_score > 60:
        adj += (rc_score - 50) * 0.05
    elif rc_score < 40:
        adj += (rc_score - 50) * 0.05
    result["score"] = max(0, min(100, round(base_score + adj, 1)))
    result["comment"] = (
        "基本面扎实，具备长期配置价值" if result["score"] >= 70 else
        "基本面尚可，关注成长持续性" if result["score"] >= 50 else
        "基本面偏弱，需审慎评估风险"
    )

    # ── 生成基本面综合摘要（HTML格式）──
    def _sc(s):
        return "#dc2626" if s >= 60 else "#d97706" if s >= 40 else "#16a34a"

    sc = result["score"]
    parts = [f'<b style="font-size:14px">基本面综合评分 <span style="color:{_sc(sc)}">{sc}分</span></b>']

    def _fv(v):
        try: return float(str(v).replace("+","").replace("%",""))
        except: return 0

    # 盈利
    p = result.get("profitability", {})
    pd_ = p.get("data", {})
    roe_v = pd_.get("ROE_加权(%)")
    if roe_v:
        eps_v = pd_.get("EPS(元)")
        roe_clr = "#dc2626" if _fv(roe_v) > 15 else "#d97706" if _fv(roe_v) > 8 else "#16a34a"
        eps_str = f"，EPS <b>{eps_v}元</b>" if eps_v and eps_v != "N/A" else ""
        parts.append(f'<b>盈利能力（{p.get("score",50)}分）：</b>ROE_加权 <span style="color:{roe_clr}"><b>{roe_v}%</b></span>{eps_str}。{p.get("comment","")}')

    # 成长
    g = result.get("growth", {})
    gd = g.get("data", {})
    rev_g = gd.get("营收同比增长(%)") or gd.get("营收同比(%)")
    np_g = gd.get("净利同比增长(%)") or gd.get("净利润同比(%)")
    if rev_g is not None or np_g is not None:
        g_parts = []
        if rev_g is not None:
            rv = _fv(rev_g)
            rg_clr = "#dc2626" if rv > 15 else "#d97706" if rv > 0 else "#16a34a"
            g_parts.append(f'营收同比 <span style="color:{rg_clr}"><b>{rev_g}%</b></span>')
        if np_g is not None:
            nv = _fv(np_g)
            ng_clr = "#dc2626" if nv > 15 else "#d97706" if nv > 0 else "#16a34a"
            g_parts.append(f'净利同比 <span style="color:{ng_clr}"><b>{np_g}%</b></span>')
        parts.append(f'<b>成长能力（{g.get("score",50)}分）：</b>{"，".join(g_parts)}。{g.get("comment","")}')

    # 估值
    v = result.get("valuation", {})
    vd = v.get("data", {})
    pe_v = vd.get("PE_TTM")
    if pe_v:
        peg_v = vd.get("PEG")
        peg_str = ""
        if peg_v:
            peg_clr = "#dc2626" if _fv(peg_v) < 1 else "#d97706" if _fv(peg_v) < 2 else "#16a34a"
            peg_str = f'，PEG <span style="color:{peg_clr}"><b>{peg_v}</b></span>'
        parts.append(f'<b>估值水平（{v.get("score",50)}分）：</b>PE_TTM=<b>{pe_v}</b>{peg_str}。{v.get("comment","")}')

    # 偿债
    s = result.get("solvency", {})
    sd = s.get("data", {})
    alr = sd.get("资产负债率(%)")
    if alr:
        alr_clr = "#dc2626" if _fv(alr) < 40 else "#d97706" if _fv(alr) < 60 else "#16a34a"
        parts.append(f'<b>偿债安全（{s.get("score",50)}分）：</b>资产负债率 <span style="color:{alr_clr}"><b>{alr}%</b></span>。{s.get("comment","")}')

    # 现金流
    cf = result.get("cashflow", {})
    cfd = cf.get("data", {})
    ocf = cfd.get("每股经营现金流(元)") or cfd.get("每股经营现金流")
    if ocf:
        ocf_clr = "#dc2626" if _fv(ocf) > 0 else "#16a34a"
        parts.append(f'<b>现金流（{cf.get("score",50)}分）：</b>每股经营现金流 <span style="color:{ocf_clr}"><b>{ocf}元</b></span>。{cf.get("comment","")}')

    # 运营效率
    ef = result.get("efficiency", {})
    efd = ef.get("data", {})
    at = efd.get("总资产周转率")
    if at:
        parts.append(f'<b>运营效率（{ef.get("score",50)}分）：</b>总资产周转率 <b>{at}</b>。{ef.get("comment","")}')

    # 业绩预告
    fc = result.get("forecast", {})
    fcd = fc.get("data", {})
    fc_type = fcd.get("预告类型")
    if fc_type:
        fc_chg = fcd.get("净利变动幅度", "")
        fc_clr = "#dc2626" if fc_type in ("预增","略增","扭亏") else "#16a34a" if fc_type in ("预减","略减","首亏","续亏") else "#d97706"
        parts.append(f'<b>业绩预告：</b>类型 <span style="color:{fc_clr}"><b>{fc_type}</b></span>，净利变动幅度 <b>{fc_chg}</b>')

    # 券商预测
    an = result.get("analyst", {})
    and_ = an.get("data", {})
    an_cnt = and_.get("近期研报数")
    if an_cnt:
        an_rating = and_.get("评级分布", "")
        an_eps = and_.get("预测EPS均值", "")
        parts.append(f'<b>券商预测（{an.get("score",50)}分）：</b>近期<b>{an_cnt}</b>篇研报，评级 {an_rating}，预测EPS均值 <b>{an_eps}</b>')

    # 主营业务
    mb = result.get("mainbz", {})
    mbd = mb.get("data", {})
    mb_list = mbd.get("主要业务")
    if mb_list and isinstance(mb_list, list):
        biz_names = []
        for item in mb_list[:3]:
            if isinstance(item, dict):
                biz_names.append(f'<b>{item.get("名称", str(item))}</b>')
            else:
                biz_names.append(f'<b>{str(item)}</b>')
        parts.append(f'<b>主营业务：</b>共{mbd.get("业务数量",0)}项，主要包括{"、".join(biz_names)}等')

    # 资产负债增强
    bd = result.get("balance_detail", {})
    bdd = bd.get("data", {})
    gw = bdd.get("商誉占比(%)")
    if gw is not None:
        gw_clr = "#16a34a" if _fv(gw) > 20 else "#d97706" if _fv(gw) > 10 else "#dc2626"
        debt = bdd.get("有息负债(亿)", 0)
        parts.append(f'<b>资产结构：</b>商誉占比 <span style="color:{gw_clr}"><b>{gw}%</b></span>，有息负债 <b>{debt}亿</b>。{bd.get("comment","")}')

    result["summary"] = "<br>".join(parts)

    return result


# ─── 资金与筹码分析 ────────────────────────────────────────────────────────────
def analyze_capital(moneyflow_data, margin_data, top10_holders, holder_number, block_trades,
                    holdertrade=None, share_float=None, pledge_data=None,
                    hk_hold_data=None, surv_data=None):
    """
    资金面九维：
      - money_flow    主力大单/特大单净流入
      - margin        融资融券余额趋势
      - holders       前十大持仓 + 股东户数变化
      - block_trade   大宗交易折溢价
      - holdertrade   股东增减持
      - share_float   限售股解禁
      - pledge        股权质押风险
      - hk_hold       北向资金持仓
      - survey        机构调研热度
    """
    result = {
        "score": 50,
        "money_flow":   {"score": 50, "data": {}, "comment": ""},
        "margin":       {"score": 50, "data": {}, "comment": ""},
        "holders":      {"score": 50, "data": {}, "comment": ""},
        "block_trade":  {"score": 50, "data": {}, "comment": ""},
        "holdertrade":  {"score": 50, "data": {}, "comment": ""},
        "share_float":  {"score": 50, "data": {}, "comment": ""},
        "pledge":       {"score": 50, "data": {}, "comment": ""},
        "hk_hold":      {"score": 50, "data": {}, "comment": ""},
        "survey":       {"score": 50, "data": {}, "comment": ""},
        "comment": ""
    }
    sub = []

    # ── 1. 主力资金流向 ──
    mfs = 50
    mfd = {}
    if moneyflow_data and len(moneyflow_data) >= 3:
        def smart_net(rows):
            return sum(
                (sf(d.get("buy_elg_amount"), 0) + sf(d.get("buy_lg_amount"), 0)) -
                (sf(d.get("sell_elg_amount"), 0) + sf(d.get("sell_lg_amount"), 0))
                for d in rows
            )
        recent5 = moneyflow_data[-5:]  if len(moneyflow_data) >= 5  else moneyflow_data
        prev5   = moneyflow_data[-10:-5] if len(moneyflow_data) >= 10 else []

        sn5  = smart_net(recent5)
        net5 = sum(sf(d.get("net_mf_amount"), 0) for d in recent5)
        mfd["近5日主力净流入(万元)"]  = round(sn5, 2)
        mfd["近5日全市净流入(万元)"]  = round(net5, 2)
        if prev5:
            mfd["主力净流入趋势"] = "增强" if sn5 > smart_net(prev5) else "减弱"

        # 最新日明细
        lm = moneyflow_data[-1]
        mfd["昨日特大单净额(万元)"] = round(
            sf(lm.get("buy_elg_amount"), 0) - sf(lm.get("sell_elg_amount"), 0), 2)
        mfd["昨日大单净额(万元)"]   = round(
            sf(lm.get("buy_lg_amount"), 0) - sf(lm.get("sell_lg_amount"), 0), 2)

        mfs += (25 if sn5 > 5000 else 15 if sn5 > 1000 else 5 if sn5 > 0
                else -5 if sn5 > -1000 else -15 if sn5 > -5000 else -25)
    mfs = max(0, min(100, mfs))
    sub.append(mfs)
    result["money_flow"] = {
        "score": mfs,
        "data": mfd,
        "comment": ("主力资金持续净流入，多头强势" if mfs >= 65 else
                    "主力资金净流出，谨慎对待" if mfs <= 35 else "主力资金流向中性")
    }

    # ── 2. 融资融券 ──
    mgs = 50
    mgd = {}
    if margin_data and len(margin_data) >= 5:
        lm_, om = margin_data[-1], margin_data[0]
        # margin_detail API 返回元，需转换为万元
        rzye = sf(lm_.get("rzye"), 0) / 10000
        rqye = sf(lm_.get("rqye"), 0) / 10000
        rz_old = sf(om.get("rzye"), 0) / 10000
        mgd["融资余额(万元)"]  = round(rzye, 2)
        mgd["融券余额(万元)"]  = round(rqye, 2)
        if rz_old > 0:
            chg = (rzye - rz_old) / rz_old * 100
            mgd["融资余额变化(%)"] = round(chg, 2)
            mgs += (20 if chg > 20 else 10 if chg > 10 else 3 if chg > 0
                    else -5 if chg > -10 else -15)
        if rqye > 0:
            mgd["融资融券比"] = round(rzye / rqye, 2)
        mgd["近5日融资余额(万元)"] = [round(sf(d.get("rzye"), 0) / 10000, 0) for d in margin_data[-5:]]
    mgs = max(0, min(100, mgs))
    sub.append(mgs)
    result["margin"] = {
        "score": mgs,
        "data": mgd,
        "comment": ("融资余额上升，杠杆资金积极看多" if mgs >= 65 else
                    "融资余额下降，杠杆资金撤退" if mgs <= 35 else "融资融券趋势中性")
    }

    # ── 3. 股东结构 ──
    hs = 50
    hd = {}
    if top10_holders:
        # 取最新期
        periods = sorted(set(h.get("end_date", "") for h in top10_holders), reverse=True)
        latest_p = periods[0] if periods else ""
        lh = [h for h in top10_holders if h.get("end_date") == latest_p]
        total_pct = sum(sf(h.get("hold_ratio"), 0) for h in lh)
        hd["前十大流通股东总持仓(%)"] = round(total_pct, 2)
        hd["前十大股东数量"] = len(lh)

        foreign_kw = ["QFII", "外资", "香港", "HONG KONG", "MORGAN", "高盛",
                      "BLACKROCK", "贝莱德", "VANGUARD", "UBS"]
        fh = [h for h in lh if any(k.upper() in str(h.get("holder_name", "")).upper() for k in foreign_kw)]
        hd["外资持股机构数"] = len(fh)
        if fh:
            hs += 10

        # 持仓集中度
        if 30 < total_pct < 60:
            hs += 10
        elif total_pct > 70:
            hs -= 5

    # 股东户数变动
    if holder_number and len(holder_number) >= 2:
        lhn = sf(holder_number[0].get("holder_num"), 0)
        phn = sf(holder_number[1].get("holder_num"), 0)
        if phn > 0:
            hn_chg = (lhn - phn) / phn * 100
            hd["股东户数变化(%)"] = round(hn_chg, 2)
            hd["最新股东户数"]    = int(lhn)
            # 户数减少→筹码集中→偏多；户数增加→筹码分散→偏空（限幅±20）
            if hn_chg < 0:
                hs += min(abs(hn_chg) * 0.5, 20)
            else:
                hs -= min(hn_chg * 0.3, 20)
    hs = max(0, min(100, hs))
    sub.append(hs)
    result["holders"] = {
        "score": hs,
        "data": hd,
        "comment": ("筹码持续集中，机构认可度高" if hs >= 65 else
                    "筹码较分散，市场博弈程度高" if hs <= 35 else "股东结构正常")
    }

    # ── 4. 大宗交易 ──
    bs = 50
    bd = {}
    if block_trades:
        total_amt = sum(sf(t.get("amount"), 0) for t in block_trades)
        discounts = [sf(t.get("premium_ratio") or t.get("discount_ratio"), 0) for t in block_trades]
        avg_disc  = sum(discounts) / len(discounts) if discounts else 0
        bd["近期大宗交易笔数"]  = len(block_trades)
        bd["成交总额(万元)"]    = round(total_amt, 2)
        bd["平均折溢价率(%)"]   = round(avg_disc, 2)
        bs += (-10 if avg_disc < -5 else 5 if avg_disc > 0 else 0)
    else:
        bd["近期大宗交易"] = "无"
    bs = max(0, min(100, bs))
    sub.append(bs)
    result["block_trade"] = {
        "score": bs,
        "data": bd,
        "comment": ("大宗折价明显，机构出货压力存在" if bs <= 40 else
                    "大宗溢价成交，买方看好后市" if bs >= 60 else "大宗交易平淡")
    }

    # ── 5. 股东增减持 ──
    hts = 50
    htd = {}
    if holdertrade:
        inc_count = sum(1 for t in holdertrade if t.get("in_de") == "IN")
        dec_count = sum(1 for t in holdertrade if t.get("in_de") == "DE")
        inc_vol = sum(sf(t.get("change_vol"), 0) for t in holdertrade if t.get("in_de") == "IN")
        dec_vol = sum(sf(t.get("change_vol"), 0) for t in holdertrade if t.get("in_de") == "DE")
        htd["近半年增持笔数"] = inc_count
        htd["近半年减持笔数"] = dec_count
        htd["增持总股数(万股)"] = round(inc_vol / 10000, 2) if inc_vol else 0
        htd["减持总股数(万股)"] = round(dec_vol / 10000, 2) if dec_vol else 0
        # 高管增持为正面信号
        net_trades = inc_count - dec_count
        hts += (15 if net_trades >= 3 else 8 if net_trades > 0 else
                -8 if net_trades < -3 else -5 if net_trades < 0 else 0)
        # 减持规模压力
        if dec_vol > inc_vol * 3 and dec_vol > 0:
            hts -= 10
            htd["减持压力"] = "偏大"
        elif inc_vol > dec_vol * 2 and inc_vol > 0:
            hts += 5
            htd["增持信号"] = "积极"
    else:
        htd["股东增减持"] = "无近期数据"
    hts = max(0, min(100, hts))
    sub.append(hts)
    result["holdertrade"] = {
        "score": hts, "data": htd,
        "comment": ("股东增持积极，管理层看好" if hts >= 65 else
                    "股东减持较多，需关注抛压" if hts <= 35 else "股东增减持中性")
    }

    # ── 6. 限售解禁 ──
    sfs = 50
    sfd = {}
    if share_float:
        total_float = sum(sf(t.get("float_share"), 0) for t in share_float)
        total_ratio = sum(sf(t.get("float_ratio"), 0) for t in share_float)
        sfd["未来90天解禁批次"] = len(share_float)
        sfd["解禁总股数(万股)"] = round(total_float / 10000, 2) if total_float else 0
        sfd["解禁占总股本(%)"] = round(total_ratio, 2) if total_ratio else 0
        # 大量解禁是潜在抛压
        if total_ratio > 10:
            sfs -= 25
            sfd["解禁压力"] = "重大"
        elif total_ratio > 5:
            sfs -= 15
            sfd["解禁压力"] = "较大"
        elif total_ratio > 1:
            sfs -= 5
            sfd["解禁压力"] = "一般"
        else:
            sfd["解禁压力"] = "轻微"
    else:
        sfd["限售解禁"] = "未来90天无解禁"
        sfs += 5  # 无解禁是轻微正面
    sfs = max(0, min(100, sfs))
    sub.append(sfs)
    result["share_float"] = {
        "score": sfs, "data": sfd,
        "comment": ("近期大量限售股解禁，抛压风险高" if sfs <= 35 else
                    "无近期解禁压力" if sfs >= 55 else "存在一定解禁压力")
    }

    # ── 7. 股权质押 ──
    pls = 50
    pld = {}
    if pledge_data:
        lp = pledge_data[0] if isinstance(pledge_data, list) else pledge_data
        pledge_ratio = sf(lp.get("pledge_ratio"), 0)
        pledge_cnt = sf(lp.get("pledge_count"), 0)
        unrest = sf(lp.get("unrest_pledge"), 0)
        pld["质押比例(%)"] = round(pledge_ratio, 2)
        pld["质押笔数"] = int(pledge_cnt)
        pld["无限售质押股数(万股)"] = round(unrest / 10000, 2) if unrest else 0
        # 高质押比是风险信号
        if pledge_ratio > 50:
            pls -= 30
            pld["质押风险"] = "极高"
        elif pledge_ratio > 30:
            pls -= 20
            pld["质押风险"] = "较高"
        elif pledge_ratio > 15:
            pls -= 10
            pld["质押风险"] = "中等"
        else:
            pls += 5
            pld["质押风险"] = "低"
    else:
        pld["股权质押"] = "无数据"
    pls = max(0, min(100, pls))
    sub.append(pls)
    result["pledge"] = {
        "score": pls, "data": pld,
        "comment": ("质押比例过高，存在平仓风险" if pls <= 30 else
                    "质押比例健康" if pls >= 55 else "质押比例偏高，需关注")
    }

    # ── 8. 北向资金 ──
    hks = 50
    hkd = {}
    if hk_hold_data and len(hk_hold_data) >= 2:
        latest = hk_hold_data[-1]
        earliest = hk_hold_data[0]
        latest_vol = sf(latest.get("vol"), 0)
        earliest_vol = sf(earliest.get("vol"), 0)
        latest_ratio = sf(latest.get("ratio"), 0)
        hkd["北向持股数(万股)"] = round(latest_vol / 10000, 2) if latest_vol else 0
        hkd["持股占比(%)"] = round(latest_ratio, 2)
        if earliest_vol > 0:
            vol_chg = (latest_vol - earliest_vol) / earliest_vol * 100
            hkd["近期持股变化(%)"] = round(vol_chg, 2)
            hks += (15 if vol_chg > 20 else 10 if vol_chg > 5 else
                    -5 if vol_chg < -5 else -15 if vol_chg < -20 else 0)
        if latest_ratio > 5:
            hks += 5  # 北向重仓是正面信号
    elif hk_hold_data and len(hk_hold_data) == 1:
        latest = hk_hold_data[0]
        hkd["北向持股数(万股)"] = round(sf(latest.get("vol"), 0) / 10000, 2)
        hkd["持股占比(%)"] = round(sf(latest.get("ratio"), 0), 2)
    else:
        hkd["北向资金"] = "无持仓或数据停更"
    hks = max(0, min(100, hks))
    sub.append(hks)
    result["hk_hold"] = {
        "score": hks, "data": hkd,
        "comment": ("北向资金持续加仓，外资看好" if hks >= 65 else
                    "北向资金减仓，外资撤退" if hks <= 35 else "北向资金持仓稳定")
    }

    # ── 9. 机构调研 ──
    svs = 50
    svd = {}
    if surv_data:
        svd["近半年调研次数"] = len(surv_data)
        orgs = set(t.get("rece_org", "") for t in surv_data if t.get("rece_org"))
        svd["调研机构数"] = len(orgs)
        # 近30天密集调研
        recent_surv = [t for t in surv_data if t.get("surv_date", "") >= (
            datetime.now() - timedelta(days=30)).strftime("%Y%m%d")]
        svd["近30天调研次数"] = len(recent_surv)
        if len(recent_surv) >= 5:
            svs += 15
            svd["调研热度"] = "非常高"
        elif len(recent_surv) >= 2:
            svs += 8
            svd["调研热度"] = "较高"
        elif len(surv_data) >= 5:
            svs += 3
            svd["调研热度"] = "正常"
        else:
            svd["调研热度"] = "较低"
    else:
        svd["机构调研"] = "无近期调研记录"
    svs = max(0, min(100, svs))
    sub.append(svs)
    result["survey"] = {
        "score": svs, "data": svd,
        "comment": ("机构密集调研，市场关注度高" if svs >= 65 else
                    "机构调研较少" if svs <= 40 else "机构调研热度一般")
    }

    # 加权合成 (9维)
    # money_flow 0.25, margin 0.12, holders 0.15, block_trade 0.05,
    # holdertrade 0.10, share_float 0.08, pledge 0.10, hk_hold 0.08, survey 0.07
    w = [0.25, 0.12, 0.15, 0.05, 0.10, 0.08, 0.10, 0.08, 0.07]
    result["score"] = round(sum(s * wt for s, wt in zip(sub, w)), 1)
    result["comment"] = (
        "资金面积极，多头力量占优" if result["score"] >= 65 else
        "资金面承压，空头偏强" if result["score"] <= 35 else
        "资金面多空博弈，暂无明显方向"
    )

    # ── 生成资金面综合摘要（HTML格式）──
    def _sc(s):
        return "#dc2626" if s >= 60 else "#d97706" if s >= 40 else "#16a34a"
    def _fv(v):
        try: return float(str(v).replace("+","").replace("%",""))
        except: return 0

    sc = result["score"]
    parts = [f'<b style="font-size:14px">资金面综合评分 <span style="color:{_sc(sc)}">{sc}分</span></b>']

    # 主力资金
    mf = result.get("money_flow", {})
    mfd_ = mf.get("data", {})
    net5 = mfd_.get("近5日主力净流入(万元)")
    if net5 is not None:
        trend = mfd_.get("主力净流入趋势", "")
        n_clr = "#dc2626" if net5 > 0 else "#16a34a"
        parts.append(f'<b>主力资金（{mf.get("score",50)}分）：</b>近5日净流入 <span style="color:{n_clr}"><b>{net5}万元</b></span>，趋势{trend}。{mf.get("comment","")}')

    # 融资融券
    mg = result.get("margin", {})
    mgd_ = mg.get("data", {})
    rzye = mgd_.get("融资余额(万元)")
    if rzye:
        rz_chg = mgd_.get("融资余额变化(%)")
        rz_clr = "#dc2626" if rz_chg and _fv(rz_chg) > 0 else "#16a34a" if rz_chg else "#d97706"
        chg_str = f'，变化 <span style="color:{rz_clr}"><b>{rz_chg}%</b></span>' if rz_chg else ""
        parts.append(f'<b>融资融券（{mg.get("score",50)}分）：</b>融资余额 <b>{rzye}万元</b>{chg_str}。{mg.get("comment","")}')

    # 股东结构
    hl = result.get("holders", {})
    hld_ = hl.get("data", {})
    top10 = hld_.get("前十大流通股东总持仓(%)")
    if top10:
        hn_chg = hld_.get("股东户数变化(%)")
        hn_clr = "#dc2626" if hn_chg and _fv(hn_chg) < 0 else "#16a34a" if hn_chg and _fv(hn_chg) > 10 else "#d97706"
        parts.append(f'<b>股东结构（{hl.get("score",50)}分）：</b>前十大持仓 <b>{top10}%</b>，户数变化 <span style="color:{hn_clr}"><b>{hn_chg}%</b></span>。{hl.get("comment","")}')

    # 大宗交易
    bt = result.get("block_trade", {})
    btd_ = bt.get("data", {})
    bt_cnt = btd_.get("近期大宗交易笔数")
    if bt_cnt:
        bt_disc = btd_.get("平均折溢价率(%)")
        bd_clr = "#dc2626" if bt_disc and _fv(bt_disc) > 0 else "#16a34a"
        parts.append(f'<b>大宗交易（{bt.get("score",50)}分）：</b>近期<b>{bt_cnt}</b>笔，折溢价 <span style="color:{bd_clr}"><b>{bt_disc}%</b></span>。{bt.get("comment","")}')

    # 股东增减持
    ht = result.get("holdertrade", {})
    htd_ = ht.get("data", {})
    inc_n = htd_.get("近半年增持笔数")
    dec_n = htd_.get("近半年减持笔数")
    if inc_n is not None:
        ht_clr = "#dc2626" if (inc_n or 0) > (dec_n or 0) else "#16a34a" if (dec_n or 0) > (inc_n or 0) else "#d97706"
        parts.append(f'<b>股东增减持（{ht.get("score",50)}分）：</b>'
                     f'增持 <span style="color:#dc2626"><b>{inc_n}笔</b></span>、'
                     f'减持 <span style="color:#16a34a"><b>{dec_n}笔</b></span>。{ht.get("comment","")}')

    # 限售解禁
    sfl = result.get("share_float", {})
    sfld_ = sfl.get("data", {})
    sf_ratio = sfld_.get("解禁占总股本(%)")
    if sf_ratio is not None:
        sf_clr = "#16a34a" if _fv(sf_ratio) > 5 else "#d97706" if _fv(sf_ratio) > 1 else "#dc2626"
        sf_press = sfld_.get("解禁压力", "")
        parts.append(f'<b>限售解禁（{sfl.get("score",50)}分）：</b>未来90天解禁<b>{sfld_.get("未来90天解禁批次",0)}</b>批，'
                     f'占总股本 <span style="color:{sf_clr}"><b>{sf_ratio}%</b></span>，压力{sf_press}')
    else:
        sf_info = sfld_.get("限售解禁") or sfld_.get("解禁压力", "")
        if sf_info:
            parts.append(f'<b>限售解禁（{sfl.get("score",50)}分）：</b>{sf_info}')

    # 股权质押
    pl = result.get("pledge", {})
    pld_ = pl.get("data", {})
    pl_ratio = pld_.get("质押比例(%)")
    if pl_ratio is not None:
        pl_clr = "#16a34a" if _fv(pl_ratio) > 30 else "#d97706" if _fv(pl_ratio) > 10 else "#dc2626"
        parts.append(f'<b>股权质押（{pl.get("score",50)}分）：</b>质押比例 <span style="color:{pl_clr}"><b>{pl_ratio}%</b></span>，{pld_.get("质押风险","")}')

    # 北向资金
    hk = result.get("hk_hold", {})
    hkd_ = hk.get("data", {})
    hk_ratio = hkd_.get("持股占比(%)")
    if hk_ratio:
        hk_chg = hkd_.get("近期持股变化(%)")
        hk_clr = "#dc2626" if hk_chg and _fv(hk_chg) > 0 else "#16a34a" if hk_chg and _fv(hk_chg) < 0 else "#d97706"
        chg_str = f'，近期变化 <span style="color:{hk_clr}"><b>{hk_chg}%</b></span>' if hk_chg else ""
        parts.append(f'<b>北向资金（{hk.get("score",50)}分）：</b>持股占比 <b>{hk_ratio}%</b>{chg_str}。{hk.get("comment","")}')
    elif hkd_.get("北向资金"):
        parts.append(f'<b>北向资金：</b>{hkd_["北向资金"]}')

    # 机构调研
    sv = result.get("survey", {})
    svd_ = sv.get("data", {})
    sv_cnt = svd_.get("近半年调研次数")
    if sv_cnt:
        sv_clr = "#dc2626" if _fv(sv_cnt) > 5 else "#d97706" if _fv(sv_cnt) > 0 else "#16a34a"
        parts.append(f'<b>机构调研（{sv.get("score",50)}分）：</b>近半年调研 <span style="color:{sv_clr}"><b>{sv_cnt}次</b></span>，{svd_.get("调研热度","")}')
    elif svd_.get("机构调研"):
        parts.append(f'<b>机构调研：</b>{svd_["机构调研"]}')

    result["summary"] = "<br>".join(parts)

    return result


# ─── 消息面分析层 ─────────────────────────────────────────────────────────────
# 使用 urllib（stdlib）做 HTTP 请求，无需 requests 依赖
_NEWS_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def _news_get(url, params=None, extra_headers=None, timeout=12) -> dict | None:
    """GET JSON，失败返回 None"""
    import urllib.request, urllib.parse
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    hdrs = {**_NEWS_HEADERS, **(extra_headers or {})}
    req = urllib.request.Request(url, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"    [新闻] GET失败 {url[:60]}: {e}")
        return None


def _news_post_json(url, body: dict, extra_headers=None, timeout=12) -> dict | None:
    """POST JSON body，失败返回 None"""
    import urllib.request
    hdrs = {**_NEWS_HEADERS, "Content-Type": "application/json",
            **(extra_headers or {})}
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=hdrs, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"    [新闻] POST失败 {url[:60]}: {e}")
        return None


def _parse_news_date(value) -> datetime | None:
    """统一解析日期：支持 ISO字符串 / unix秒 / unix毫秒 / RFC 822（RSS pubDate）"""
    if not value:
        return None
    if isinstance(value, (int, float)):
        ts = value / 1000 if value > 9_999_999_999 else value
        try:
            return datetime.fromtimestamp(ts)
        except Exception:
            return None
    s = str(value)
    # RFC 822: "Sun, 22 Feb 2026 13:00:00 +0800"
    try:
        import email.utils
        return datetime(*email.utils.parsedate(s)[:6])
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _news_within_days(pub_dt: datetime | None, n_days: int) -> bool:
    """判断日期是否在最近 n_days 天内"""
    if pub_dt is None:
        return True  # 无法判断时默认保留
    return (datetime.now() - pub_dt).days <= n_days


def fetch_news_macro(n_days: int = 7) -> list[dict]:
    """
    获取近 n_days 天宏观/政策新闻。
    来源：财联社电报 + 第一财经 + 证券时报要闻。
    返回：list[{id, title, summary, url, published_at(str), source}]
    """
    print("  [新闻] 宏观新闻采集...")
    items = []

    # ── 1. 财联社电报
    try:
        r = _news_get("https://www.cls.cn/nodeapi/updateTelegraphList",
                      {"app": "CailianpressWeb", "os": "web", "sv": "8.4.6", "sign": ""},
                      extra_headers={"Referer": "https://www.cls.cn/"})
        for raw in (r or {}).get("data", {}).get("roll_data", [])[:30]:
            pub = _parse_news_date(raw.get("ctime"))
            if not _news_within_days(pub, n_days):
                continue
            title = raw.get("title") or (raw.get("content", "") or "")[:60]
            items.append({
                "id": f"cls_{raw.get('id','')}",
                "title": title,
                "summary": raw.get("content", "")[:150],
                "url": raw.get("shareurl", ""),
                "published_at": pub.strftime("%Y-%m-%d %H:%M") if pub else "",
                "source": "财联社",
            })
    except Exception:
        pass

    # ── 2. 第一财经
    try:
        r = _news_get("https://www.yicai.com/api/ajax/getjuhelist",
                      {"action": "news", "page": "1", "pagesize": "20"})
        for raw in (r or [])[:20]:
            pub = _parse_news_date(raw.get("CreateDate"))
            if not _news_within_days(pub, n_days):
                continue
            items.append({
                "id": f"yicai_{raw.get('NewsID','')}",
                "title": raw.get("NewsTitle", ""),
                "summary": raw.get("NewsNotes", "")[:150] if raw.get("NewsNotes") else "",
                "url": raw.get("url", ""),
                "published_at": pub.strftime("%Y-%m-%d %H:%M") if pub else "",
                "source": "第一财经",
            })
    except Exception:
        pass

    # ── 3. 证券时报要闻
    try:
        r = _news_get("https://www.stcn.com/article/list.html",
                      {"type": "yw"},
                      extra_headers={"X-Requested-With": "XMLHttpRequest"})
        for raw in (r or {}).get("data", [])[:20]:
            pub = _parse_news_date(raw.get("time"))
            if not _news_within_days(pub, n_days):
                continue
            url = raw.get("url", "")
            if url and not url.startswith("http"):
                url = "https://www.stcn.com" + url
            items.append({
                "id": f"stcn_{raw.get('id','')}",
                "title": raw.get("title", ""),
                "summary": (raw.get("content") or "")[:150],
                "url": url,
                "published_at": pub.strftime("%Y-%m-%d %H:%M") if pub else "",
                "source": "证券时报",
            })
    except Exception:
        pass

    # 去重（按 title 前20字）
    seen = set()
    result = []
    for it in items:
        key = it["title"][:20]
        if key not in seen:
            seen.add(key)
            result.append(it)

    return result


def fetch_news_industry(industry: str, n_days: int = 7) -> list[dict]:
    """
    获取近 n_days 天行业相关新闻。
    来源：东方财富关键词搜索研报 + 第一财经行业频道（标题过滤）。
    """
    print(f"  [新闻] 行业新闻采集 ({industry})...")
    import random, time, re

    items = []

    # ── 1. 东方财富搜索（JSONP）
    try:
        cb = f"jQuery{random.randint(10**15, 10**16-1)}_{int(time.time()*1000)}"
        body = {
            "uid": "", "keyword": industry,
            "type": ["cmsArticleWebOld"],
            "client": "web", "clientType": "web", "clientVersion": "curr",
            "params": {
                "cmsArticleWebOld": {
                    "searchScope": "default", "sort": "default",
                    "pageIndex": 1, "pageSize": 15,
                    "preTag": "", "postTag": "",
                }
            },
        }
        import urllib.parse
        search_url = ("https://search-api-web.eastmoney.com/search/jsonp"
                      "?cb=" + cb + "&param=" +
                      urllib.parse.quote(json.dumps(body)))
        import urllib.request
        req = urllib.request.Request(
            search_url, headers=_NEWS_HEADERS)
        with urllib.request.urlopen(req, timeout=12) as resp:
            text = resp.read().decode("utf-8")
        json_str = text[text.index("(") + 1: text.rindex(")")]
        data = json.loads(json_str)
        for raw in data.get("result", {}).get("cmsArticleWebOld", []):
            title = re.sub(r"</?em>", "", raw.get("title", ""))
            summary = re.sub(r"</?em>", "", raw.get("content", ""))[:150]
            pub = _parse_news_date(raw.get("date"))
            if not _news_within_days(pub, n_days):
                continue
            items.append({
                "id": f"em_{raw.get('docId','')}",
                "title": title,
                "summary": summary,
                "url": raw.get("url", ""),
                "published_at": pub.strftime("%Y-%m-%d %H:%M") if pub else "",
                "source": "东方财富",
            })
    except Exception:
        pass

    # ── 2. 第一财经（标题含行业关键词）
    try:
        r = _news_get("https://www.yicai.com/api/ajax/getjuhelist",
                      {"action": "news", "page": "1", "pagesize": "30"})
        for raw in (r or []):
            title = raw.get("NewsTitle", "")
            if industry not in title:
                continue
            pub = _parse_news_date(raw.get("CreateDate"))
            if not _news_within_days(pub, n_days):
                continue
            items.append({
                "id": f"yicai_{raw.get('NewsID','')}",
                "title": title,
                "summary": (raw.get("NewsNotes") or "")[:150],
                "url": raw.get("url", ""),
                "published_at": pub.strftime("%Y-%m-%d %H:%M") if pub else "",
                "source": "第一财经",
            })
    except Exception:
        pass

    # 去重
    seen = set()
    result = []
    for it in items:
        key = it["title"][:20]
        if key not in seen:
            seen.add(key)
            result.append(it)

    return result


def fetch_news_company(ts_code: str, stock_name: str, n_days: int = 7) -> list[dict]:
    """
    获取近 n_days 天公司相关新闻 + 交易所公告。
    ts_code 格式：600519.SH 或 000001.SZ
    来源：CLS + 第一财经 + 证券时报 + 东财搜索 + SSE/SZSE公告
    """
    print(f"  [新闻] 公司新闻采集 ({stock_name})...")
    import random, time, re
    items = []
    pure_code = ts_code.split(".")[0]  # "600519"
    is_sh = ts_code.endswith(".SH")

    # ── 1. 财联社电报（标题含公司名）
    try:
        r = _news_get("https://www.cls.cn/nodeapi/updateTelegraphList",
                      {"app": "CailianpressWeb", "os": "web", "sv": "8.4.6", "sign": ""},
                      extra_headers={"Referer": "https://www.cls.cn/"})
        for raw in (r or {}).get("data", {}).get("roll_data", [])[:50]:
            content = (raw.get("title") or "") + (raw.get("content") or "")
            if stock_name not in content and pure_code not in content:
                continue
            pub = _parse_news_date(raw.get("ctime"))
            if not _news_within_days(pub, n_days):
                continue
            items.append({
                "id": f"cls_{raw.get('id','')}",
                "title": raw.get("title") or raw.get("content", "")[:60],
                "summary": (raw.get("content") or "")[:150],
                "url": raw.get("shareurl", ""),
                "published_at": pub.strftime("%Y-%m-%d %H:%M") if pub else "",
                "source": "财联社",
            })
    except Exception:
        pass

    # ── 2. 第一财经（标题含公司名）
    try:
        r = _news_get("https://www.yicai.com/api/ajax/getjuhelist",
                      {"action": "news", "page": "1", "pagesize": "30"})
        for raw in (r or []):
            if stock_name not in (raw.get("NewsTitle") or ""):
                continue
            pub = _parse_news_date(raw.get("CreateDate"))
            if not _news_within_days(pub, n_days):
                continue
            items.append({
                "id": f"yicai_{raw.get('NewsID','')}",
                "title": raw.get("NewsTitle", ""),
                "summary": (raw.get("NewsNotes") or "")[:150],
                "url": raw.get("url", ""),
                "published_at": pub.strftime("%Y-%m-%d %H:%M") if pub else "",
                "source": "第一财经",
            })
    except Exception:
        pass

    # ── 3. 证券时报（标题含公司名）
    try:
        for cat in ["gsxw", "yw"]:
            r = _news_get("https://www.stcn.com/article/list.html", {"type": cat},
                          extra_headers={"X-Requested-With": "XMLHttpRequest"})
            for raw in (r or {}).get("data", [])[:30]:
                if stock_name not in (raw.get("title") or ""):
                    continue
                pub = _parse_news_date(raw.get("time"))
                if not _news_within_days(pub, n_days):
                    continue
                url = raw.get("url", "")
                if url and not url.startswith("http"):
                    url = "https://www.stcn.com" + url
                items.append({
                    "id": f"stcn_{raw.get('id','')}",
                    "title": raw.get("title", ""),
                    "summary": (raw.get("content") or "")[:150],
                    "url": url,
                    "published_at": pub.strftime("%Y-%m-%d %H:%M") if pub else "",
                    "source": "证券时报",
                })
    except Exception:
        pass

    # ── 4. 东方财富搜索（公司名关键词）
    try:
        cb = f"jQuery{random.randint(10**15,10**16-1)}_{int(time.time()*1000)}"
        body = {
            "uid": "", "keyword": stock_name,
            "type": ["cmsArticleWebOld"],
            "client": "web", "clientType": "web", "clientVersion": "curr",
            "params": {"cmsArticleWebOld": {
                "searchScope": "default", "sort": "default",
                "pageIndex": 1, "pageSize": 15,
                "preTag": "", "postTag": "",
            }},
        }
        import urllib.request, urllib.parse
        search_url = ("https://search-api-web.eastmoney.com/search/jsonp"
                      "?cb=" + cb + "&param=" + urllib.parse.quote(json.dumps(body)))
        req = urllib.request.Request(search_url, headers=_NEWS_HEADERS)
        with urllib.request.urlopen(req, timeout=12) as resp:
            text = resp.read().decode("utf-8")
        json_str = text[text.index("(") + 1: text.rindex(")")]
        data = json.loads(json_str)
        for raw in data.get("result", {}).get("cmsArticleWebOld", []):
            title = re.sub(r"</?em>", "", raw.get("title", ""))
            pub = _parse_news_date(raw.get("date"))
            if not _news_within_days(pub, n_days):
                continue
            items.append({
                "id": f"em_{raw.get('docId','')}",
                "title": title,
                "summary": re.sub(r"</?em>", "", raw.get("content", ""))[:150],
                "url": raw.get("url", ""),
                "published_at": pub.strftime("%Y-%m-%d %H:%M") if pub else "",
                "source": "东方财富",
            })
    except Exception:
        pass

    # ── 5. 交易所公告
    try:
        if is_sh:
            # 上交所
            params = {
                "isPagination": "true",
                "securityType": "0101,120100,020100,020200,120200",
                "reportType": "ALL",
                "pageHelp.pageSize": "15",
                "pageHelp.pageCount": "50",
                "pageHelp.pageNo": "1",
                "pageHelp.beginPage": "1",
                "pageHelp.cacheSize": "1",
                "pageHelp.endPage": "5",
                "_": str(int(datetime.now().timestamp() * 1000)),
                "productId": pure_code,
            }
            r = _news_get(
                "https://query.sse.com.cn/security/stock/queryCompanyBulletin.do",
                params,
                extra_headers={"Referer": "https://www.sse.com.cn/"}
            )
            for raw in (r or {}).get("pageHelp", {}).get("data", []):
                pub = _parse_news_date(raw.get("ADDDATE"))
                if not _news_within_days(pub, n_days):
                    continue
                url = "https://static.sse.com.cn" + raw.get("URL", "")
                items.append({
                    "id": f"sse_{raw.get('BULLETINID','')}",
                    "title": raw.get("TITLE", ""),
                    "summary": f"上交所公告 - {raw.get('BULLETIN_TYPE','')}",
                    "url": url,
                    "published_at": pub.strftime("%Y-%m-%d %H:%M") if pub else "",
                    "source": "上交所公告",
                })
        else:
            # 深交所
            body = {
                "seDate": ["", ""],
                "channelCode": ["listedNotice_disc"],
                "stock": pure_code,
                "pageSize": 15,
                "pageNum": 1,
            }
            r = _news_post_json(
                "https://www.szse.cn/api/disc/announcement/annList",
                body,
                extra_headers={"Referer": "https://www.szse.cn/"}
            )
            for raw in (r or {}).get("data", []):
                pub = _parse_news_date(raw.get("publishTime"))
                if not _news_within_days(pub, n_days):
                    continue
                attach = raw.get("attachPath", "")
                url = f"https://www.szse.cn{attach}" if attach else ""
                sec_names = raw.get("secName", [])
                author = sec_names[0] if isinstance(sec_names, list) and sec_names else ""
                items.append({
                    "id": f"szse_{raw.get('id','')}",
                    "title": raw.get("title", ""),
                    "summary": f"深交所公告 - {author}",
                    "url": url,
                    "published_at": pub.strftime("%Y-%m-%d %H:%M") if pub else "",
                    "source": "深交所公告",
                })
    except Exception:
        pass

    # 去重
    seen = set()
    result = []
    for it in items:
        key = it["title"][:20]
        if key not in seen:
            seen.add(key)
            result.append(it)

    return result


# ─── 东财股吧抓取 ─────────────────────────────────────────────────────────────
# 基于 nautilus_trader/guba_scraper 优化实现

_GUBA_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/18.1 Safari/605.1.15",
]

_GUBA_LIST_URL = "https://guba.eastmoney.com/list,{code},f_1.html"
_GUBA_DETAIL_URL = "https://guba.eastmoney.com/news,{code},{postid}.html"
_GUBA_COMMENT_API = "https://guba.eastmoney.com/interface/GetData.aspx"
_GUBA_COMMENT_LIST_PATH = "reply/api/Reply/ArticleNewReplyList"


def _guba_random_ua() -> str:
    """随机选择 UA"""
    import random
    return random.choice(_GUBA_USER_AGENTS)


def _guba_build_headers(referer: str = "") -> dict:
    """构建股吧请求头"""
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
        "User-Agent": _guba_random_ua(),
    }
    if referer:
        headers["Referer"] = referer
    return headers


def _guba_request_with_retry(url: str, headers: dict = None, 
                              retry: int = 3, backoff: float = 1.5,
                              timeout: int = 12) -> str | None:
    """带重试的HTTP请求，返回响应文本"""
    import urllib.request
    import time
    
    headers = headers or _guba_build_headers()
    
    for attempt in range(retry):
        try:
            if attempt > 0:
                time.sleep(backoff ** attempt)  # 指数退避
            
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8")
        except Exception as e:
            if attempt == retry - 1:
                print(f"    [股吧] 请求失败 (尝试{attempt+1}/{retry}): {url[:60]}... - {e}")
    return None


def _guba_clean_text(content: str) -> str:
    """清理HTML标签和多余空白"""
    import re
    if not content:
        return ""
    content = re.sub(r"<[^>]+>", "", content)
    content = re.sub(r"\s+", " ", content)
    return content.strip()


def _guba_parse_read_count(text: str) -> str:
    """解析阅读量（保留原格式如 '1.2万'）"""
    if not text:
        return "0"
    return text.strip()


def _guba_parse_comment_count(text: str) -> int:
    """解析评论数"""
    if not text:
        return 0
    text = text.strip()
    try:
        if "万" in text:
            return int(float(text.replace("万", "")) * 10000)
        return int(text)
    except ValueError:
        return 0


def _guba_parse_html_list(html: str, stock_code: str) -> list[dict]:
    """
    解析股吧列表页HTML，提取帖子元数据。
    使用 BeautifulSoup 解析 HTML 表格结构。
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("    [股吧] 需要安装 beautifulsoup4: pip install beautifulsoup4")
        return []
    
    # 尝试使用 lxml，不可用则回退到 html.parser
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")
    
    posts = []
    current_year = datetime.now().year
    last_month = 13  # 用于跨年推断
    
    for item in soup.select("tr.listitem"):
        try:
            # 阅读量
            read_elem = item.select_one(".read")
            read_count = _guba_parse_read_count(read_elem.text if read_elem else "0")
            
            # 评论数
            reply_elem = item.select_one(".reply")
            comment_count = _guba_parse_comment_count(reply_elem.text if reply_elem else "0")
            
            # 标题和链接
            title_link = item.select_one(".title a")
            if not title_link:
                continue
            
            title = title_link.get_text(strip=True)
            href = str(title_link.get("href", ""))
            post_id = title_link.get("data-postid")
            
            # 构建完整URL
            if href.startswith("//"):
                post_url = "https:" + href
            elif href.startswith("/"):
                post_url = "https://guba.eastmoney.com" + href
            else:
                post_url = href
            
            # 提取 post_id
            post_id_str = str(post_id) if post_id else ""
            if not post_id_str:
                import re
                match = re.search(r"news,[^,]+,(\d+)\.html", href)
                if match:
                    post_id_str = match.group(1)
                else:
                    continue
            
            # 只保留股吧帖子（过滤财富号等）
            if "guba.eastmoney.com/news" not in post_url:
                continue
            
            # 作者
            author_elem = item.select_one(".author a")
            author = author_elem.get_text(strip=True) if author_elem else ""
            
            # 日期解析（推断年份）
            update_elem = item.select_one(".update")
            post_date = ""
            post_time = ""
            if update_elem:
                date_str = update_elem.get_text(strip=True)
                parts = date_str.split()
                if len(parts) >= 1:
                    md = parts[0].split("-")
                    if len(md) == 2:
                        try:
                            month = int(md[0])
                            day = int(md[1])
                            # 跨年推断：如果月份变大了，说明跨年了
                            if last_month < month:
                                current_year -= 1
                            last_month = month
                            post_date = f"{current_year}-{month:02d}-{day:02d}"
                        except ValueError:
                            pass
                if len(parts) >= 2:
                    post_time = parts[1]
            
            posts.append({
                "post_id": int(post_id_str),
                "stock_code": stock_code,
                "title": title,
                "author": author,
                "read_count": read_count,
                "comment_count": comment_count,
                "post_url": post_url,
                "post_date": post_date,
                "post_time": post_time,
            })
        except Exception as e:
            continue
    
    return posts


def _guba_fetch_content(post_url: str) -> str:
    """抓取单个帖子的正文内容"""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return ""
    
    html = _guba_request_with_retry(post_url, 
                                     _guba_build_headers(referer=post_url))
    if not html:
        return ""
    
    try:
        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception:
            soup = BeautifulSoup(html, "html.parser")
        
        # 多选择器回退
        content_elem = (
            soup.select_one(".newstext") or
            soup.select_one("#zwconbody") or
            soup.select_one(".stockcodec") or
            soup.select_one(".article-body")
        )
        if content_elem:
            return _guba_clean_text(content_elem.get_text())
    except Exception:
        pass
    return ""


def _guba_fetch_comments(post_id: int, referer: str, limit: int = 10) -> list[dict]:
    """通过API抓取帖子评论"""
    import urllib.request
    import time
    
    all_comments = []
    
    url = f"{_GUBA_COMMENT_API}?path={_GUBA_COMMENT_LIST_PATH}"
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://guba.eastmoney.com",
        "Referer": referer,
        "User-Agent": _guba_random_ua(),
    }
    
    payload = f"param=postid={post_id}&sort=1&sorttype=1&p=1&ps={limit}"
    payload = payload.encode("utf-8")
    
    try:
        time.sleep(0.5)  # 小延迟避免过快
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        
        for comment in data.get("re", [])[:limit]:
            import re
            reply_date = comment.get("reply_date", "")
            comment_date = ""
            comment_time = ""
            if reply_date:
                match = re.search(r"(\d{4}-\d{2}-\d{2})\s*(\d{2}:\d{2})", reply_date)
                if match:
                    comment_date = match.group(1)
                    comment_time = match.group(2)
            
            all_comments.append({
                "content": _guba_clean_text(comment.get("reply_text", "")),
                "author": comment.get("user_nickname", ""),
                "like_count": int(comment.get("like_count", 0) or 0),
                "comment_date": comment_date,
                "comment_time": comment_time,
            })
    except Exception as e:
        print(f"    [股吧] 评论获取失败: {e}")
    
    return all_comments


def fetch_sentiment_eastmoney(ts_code: str, n: int = 50,
                               fetch_content: bool = False,
                               fetch_comments: bool = False) -> list[dict]:
    """
    获取东财股吧近期帖子（用于情绪分析）。
    
    基于 nautilus_trader/guba_scraper 实现，采用 HTML 解析方式。
    
    Args:
        ts_code: 股票代码，如 "600519.SH"
        n: 返回帖子数量上限
        fetch_content: 是否抓取帖子正文（增加耗时）
        fetch_comments: 是否抓取热门评论（增加耗时）
    
    Returns:
        [{
            'title': str,         # 帖子标题
            'author': str,        # 作者
            'read_count': str,    # 阅读量 (如 "1.2万")
            'comment_count': int, # 评论数
            'post_date': str,     # 发布日期 "YYYY-MM-DD"
            'post_url': str,      # 帖子URL
            'content': str,       # 正文 (fetch_content=True时)
            'top_comments': list, # 热门评论 (fetch_comments=True时)
        }, ...]
    """
    print(f"  [新闻] 东财股吧情绪采集...")
    
    pure_code = ts_code.split(".")[0]
    list_url = _GUBA_LIST_URL.format(code=pure_code)
    
    # 请求列表页
    html = _guba_request_with_retry(
        list_url,
        _guba_build_headers(referer=f"https://guba.eastmoney.com/list,{pure_code}.html")
    )
    
    if not html:
        print(f"    [股吧] 列表页获取失败")
        return []
    
    # 解析HTML
    posts = _guba_parse_html_list(html, pure_code)
    
    if not posts:
        print(f"    [股吧] 未解析到帖子，尝试API备用方案...")
        # API 备用方案
        posts = _guba_fetch_via_api(pure_code, n)
    
    # 截取前n条
    posts = posts[:n]
    
    # 可选：抓取正文
    if fetch_content and posts:
        import time
        for i, post in enumerate(posts[:10]):  # 最多抓10条正文
            post_url = post.get("post_url", "")
            if post_url:
                time.sleep(0.5)
                content = _guba_fetch_content(post_url)
                post["content"] = content
    
    # 可选：抓取评论
    if fetch_comments and posts:
        for i, post in enumerate(posts[:5]):  # 最多抓5条帖子的评论
            post_id = post.get("post_id")
            post_url = post.get("post_url", "")
            if post_id and post_url:
                comments = _guba_fetch_comments(post_id, post_url, limit=5)
                post["top_comments"] = comments
    
    print(f"    [股吧] 获取到 {len(posts)} 条帖子")
    return posts


def _guba_fetch_via_api(stock_code: str, n: int = 50) -> list[dict]:
    """API 备用方案（当HTML解析失败时使用）"""
    try:
        r = _news_get(
            "https://guba.eastmoney.com/interface/GetData.aspx",
            {"type": "get_live_list", "code": stock_code, "page": "1", "count": str(n)},
            extra_headers={"Referer": f"https://guba.eastmoney.com/list,{stock_code}.html"},
        )
        
        raw_list = []
        if isinstance(r, dict):
            raw_list = r.get("data", []) or r.get("re", []) or []
        elif isinstance(r, list):
            raw_list = r
        
        posts = []
        for raw in raw_list[:n]:
            if not isinstance(raw, dict):
                continue
            title = raw.get("post_title") or raw.get("title", "")
            if not title:
                continue
            
            pub = _parse_news_date(raw.get("post_publish_time") or raw.get("posttime"))
            posts.append({
                "title": title,
                "author": raw.get("user_nickname") or raw.get("author", ""),
                "read_count": str(raw.get("post_read_count") or raw.get("readcount", 0)),
                "comment_count": int(raw.get("post_comment_count") or raw.get("replycount", 0) or 0),
                "post_date": pub.strftime("%Y-%m-%d") if pub else "",
                "post_url": "",
            })
        return posts
    except Exception as e:
        print(f"    [股吧] API备用方案失败: {e}")
        return []


def _xueqiu_via_rsshub(symbol: str, n: int, rsshub: str) -> list[dict]:
    """通过 RSSHub 获取雪球评论 (备用方案)"""
    import urllib.request
    import xml.etree.ElementTree as ET
    
    url = f"{rsshub.rstrip('/')}/xueqiu/stock_comments/{symbol}"
    items = []
    try:
        req = urllib.request.Request(url, headers=_NEWS_HEADERS)
        with urllib.request.urlopen(req, timeout=12) as resp:
            content = resp.read()
        root = ET.fromstring(content)
        for item in root.findall(".//item")[:n]:
            title_el = item.find("title")
            pub_el = item.find("pubDate")
            title = (title_el.text or "").strip() if title_el is not None else ""
            if not title:
                continue
            pub_dt = _parse_news_date(pub_el.text if pub_el is not None else None)
            if not _news_within_days(pub_dt, 7):
                continue
            items.append({
                "title": title,
                "like_count": 0,
                "reply_count": 0,
                "published_at": pub_dt.strftime("%Y-%m-%d %H:%M") if pub_dt else "",
            })
    except Exception:
        pass
    return items


def _xueqiu_parse_response(data: dict, n: int) -> list[dict]:
    import re
    from html import unescape
    
    items = []
    for status in data.get("list", [])[:n]:
        text_html = status.get("text", "")
        text_clean = re.sub(r"<[^>]+>", "", unescape(text_html)).strip()
        if not text_clean:
            continue
        if len(text_clean) > 200:
            text_clean = text_clean[:200] + "..."
        
        created_at = status.get("created_at", 0)
        pub_dt = None
        if created_at:
            try:
                pub_dt = datetime.fromtimestamp(created_at / 1000)
            except Exception:
                pass
        
        if not _news_within_days(pub_dt, 7):
            continue
        
        items.append({
            "title": text_clean,
            "like_count": status.get("like_count", 0) or 0,
            "reply_count": status.get("reply_count", 0) or 0,
            "user": status.get("user", {}).get("screen_name", ""),
            "published_at": pub_dt.strftime("%Y-%m-%d %H:%M") if pub_dt else "",
        })
    return items


def _xueqiu_via_cookie(symbol: str, n: int, cookie: str) -> list[dict]:
    import urllib.request
    import json

    api_url = f"https://xueqiu.com/query/v1/symbol/search/status?u=11111&count={n}&comment=0&symbol={symbol}&source=all&sort=time"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": f"https://xueqiu.com/S/{symbol}",
        "Cookie": cookie,
    }

    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
            if "aliyun_waf" in raw or "<html" in raw[:100]:
                return []
            data = json.loads(raw)
        return _xueqiu_parse_response(data, n)
    except Exception:
        return []


def _xueqiu_via_playwright(symbol: str, n: int) -> list[dict]:
    """通过 Playwright 浏览器自动化抓取雪球股票讨论页评论，绕过 WAF。"""
    import re
    from html import unescape
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return []

    items = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                args=["--disable-blink-features=AutomationControlled"],
            )
            ctx = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
            )
            page = ctx.new_page()
            page.add_init_script(
                "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
            )

            page.goto(
                f"https://xueqiu.com/S/{symbol}",
                wait_until="networkidle",
                timeout=30000,
            )
            page.wait_for_timeout(4000)

            # 向下滚动加载更多评论
            for _ in range(min(n // 10, 3)):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1500)

            raw_items = page.evaluate(
                """(maxN) => {
                    const nodes = document.querySelectorAll('.timeline__item');
                    return Array.from(nodes).slice(0, maxN).map(el => {
                        const textEl = el.querySelector('.status-content, .timeline__item__content');
                        const timeEl = el.querySelector('time, .timeline__item__time, [class*="time"]');
                        const likeEl = el.querySelector('[class*="like"] span, [class*="like_count"]');
                        const replyEl = el.querySelector('[class*="reply"] span, [class*="comment"] span');
                        const userEl = el.querySelector('.status-username, a[href*="/u/"]');
                        return {
                            text: (textEl || el).innerText.substring(0, 300),
                            time: timeEl ? timeEl.innerText : '',
                            likes: likeEl ? likeEl.innerText : '0',
                            replies: replyEl ? replyEl.innerText : '0',
                            user: userEl ? userEl.innerText : '',
                        };
                    });
                }""",
                n,
            )

            browser.close()

        for raw in raw_items:
            text = raw.get("text", "").strip()
            if not text:
                continue
            # 清理多余空白
            text = re.sub(r"\s+", " ", text)
            if len(text) > 200:
                text = text[:200] + "..."

            like_count = 0
            reply_count = 0
            try:
                like_count = int(re.sub(r"\D", "", raw.get("likes", "0")) or 0)
            except Exception:
                pass
            try:
                reply_count = int(re.sub(r"\D", "", raw.get("replies", "0")) or 0)
            except Exception:
                pass

            items.append({
                "title": text,
                "like_count": like_count,
                "reply_count": reply_count,
                "user": raw.get("user", ""),
                "published_at": raw.get("time", ""),
            })
    except Exception as e:
        print(f"    [新闻] Playwright异常: {e}")
    return items


def fetch_sentiment_xueqiu(ts_code: str, n: int = 50, rsshub: str = "https://rsshub.app",
                           xueqiu_cookie: str = "") -> list[dict]:
    """
    获取雪球股票评论。
    回退链: cookie API → Playwright 浏览器自动化 → RSSHub。
    """
    import os

    pure_code = ts_code.split(".")[0]
    prefix = "SH" if ts_code.endswith(".SH") else "SZ"
    symbol = f"{prefix}{pure_code}"

    print(f"  [新闻] 雪球评论采集...")

    # 1) cookie API (最快)
    cookie = xueqiu_cookie or os.environ.get("XUEQIU_COOKIE", "")
    if cookie:
        items = _xueqiu_via_cookie(symbol, n, cookie)
        if items:
            print(f"    [雪球] API模式 {len(items)} 条")
            return items
        print(f"    [雪球] API失败，尝试Playwright...")

    # 2) Playwright 浏览器自动化 (绕过 WAF)
    items = _xueqiu_via_playwright(symbol, n)
    if items:
        print(f"    [雪球] Playwright模式 {len(items)} 条")
        return items
    print(f"    [雪球] Playwright失败，尝试RSSHub...")

    # 3) RSSHub (备用)
    items = _xueqiu_via_rsshub(symbol, n, rsshub)
    if items:
        print(f"    [雪球] RSSHub模式 {len(items)} 条")
    else:
        print(f"    [雪球] 所有方式均失败")
    return items


_POS_KW = ["增长", "突破", "超预期", "利好", "中标", "新签", "上调", "提升",
           "盈利", "增持", "回购", "创新高", "扩张", "战略合作", "大涨",
           "强势", "好于预期", "净利增", "营收增", "新高", "降准", "宽松"]
_NEG_KW = ["亏损", "下调", "处罚", "违规", "减持", "质押", "退市", "下滑",
           "风险", "监管", "立案", "问询", "不及预期", "净利降", "营收降",
           "诉讼", "处罚决定", "财务造假", "终止", "撤销"]
_HIGH_KW = ["央行", "财政部", "国务院", "政策", "降息", "降准", "年报", "季报",
            "重大合同", "并购", "重组", "定增", "起诉", "处罚决定", "业绩预告",
            "重大资产", "停牌", "复牌"]


def _classify_news(title: str, summary: str = "") -> dict:
    """对单条新闻进行情感标注和重要性评估"""
    text = title + " " + (summary or "")
    pos = sum(kw in text for kw in _POS_KW)
    neg = sum(kw in text for kw in _NEG_KW)
    sentiment = 1 if pos > neg else (-1 if neg > pos else 0)
    importance = "high" if any(kw in text for kw in _HIGH_KW) else "mid"
    return {"sentiment": sentiment, "importance": importance}


def _filter_and_sort(items: list[dict], limit: int) -> list[dict]:
    """
    对新闻列表做分类、去空标题过滤，high 优先，返回前 limit 条。
    同时在每条记录中附加 sentiment / importance 字段。
    """
    result = []
    for it in items:
        if not it.get("title"):
            continue
        cls = _classify_news(it["title"], it.get("summary", ""))
        it["sentiment"] = cls["sentiment"]
        it["importance"] = cls["importance"]
        result.append(it)

    # high importance 优先
    result.sort(key=lambda x: (0 if x["importance"] == "high" else 1))
    return result[:limit]


def call_doubao_news_analysis(stock_name: str, industry: str,
                               macro: list, industry_news: list,
                               company: list) -> dict:
    """
    Doubao 调用 1：三层新闻 → 宏观/行业/公司分析 JSON。
    失败时返回空字典（由 local_news_analysis 兜底）。
    """
    def _fmt(items, limit):
        return "\n".join(
            f"{i+1}. [{it['source']}] {it['title']} | {it.get('summary','')[:50]}"
            for i, it in enumerate(items[:limit])
        ) or "（暂无数据）"

    prompt = f"""你是专业A股分析师。分析以下近7天新闻对股票「{stock_name}」（{industry}行业）的潜在影响。

【宏观新闻】（共{len(macro[:10])}条）
{_fmt(macro, 10)}

【行业新闻】（共{len(industry_news[:8])}条）
{_fmt(industry_news, 8)}

【公司新闻】（共{len(company[:10])}条）
{_fmt(company, 10)}

请输出严格JSON格式（无任何markdown代码块，直接输出花括号开头）：
{{
  "macro": {{"rating": "利好|中性|利空", "score": 0-100, "key_events": ["事件1", "事件2"], "analysis": "2-3句话分析"}},
  "industry": {{"rating": "利好|中性|利空", "score": 0-100, "key_events": ["事件1"], "analysis": "2-3句话分析"}},
  "company": {{"rating": "利好|中性|利空", "score": 0-100, "key_events": ["事件1"], "analysis": "2-3句话分析"}},
  "overall_impact": "综合消息面对该股的一句话总结"
}}"""

    raw = call_doubao(prompt,
                      system_prompt="你是专业A股分析师，严格按JSON格式输出，不使用markdown。",
                      max_tokens=800)
    if not raw:
        return {}
    try:
        # 提取 JSON（处理可能的前导文字）
        start = raw.index("{")
        end = raw.rindex("}") + 1
        return json.loads(raw[start:end])
    except Exception:
        return {}


def call_doubao_sentiment(stock_name: str, guba: list, xueqiu: list) -> dict:
    """Doubao 调用：股吧+雪球评论 → 情绪分析 JSON"""
    def _fmt_titles(items, limit):
        return "\n".join(f"- {it['title']}" for it in items[:limit]) or "（暂无数据）"

    guba_text = _fmt_titles(guba, 30) if guba else "（暂无数据）"
    xq_text = _fmt_titles(xueqiu, 30) if xueqiu else "（暂无数据）"

    prompt = f"""分析以下A股「{stock_name}」两大散户社区评论，判断市场情绪：

【东财股吧】（共{len(guba[:30])}条）
{guba_text}

【雪球评论】（共{len(xueqiu[:30])}条）
{xq_text}

请输出严格JSON（无markdown）：
{{
  "eastmoney_guba": {{
    "sentiment_score": -1.0到1.0,
    "crowd_emotion": "极度乐观|乐观|中性|悲观|极度悲观",
    "bull_ratio": 0-100,
    "top_themes": ["主题1", "主题2", "主题3"]
  }},
  "xueqiu": {{
    "sentiment_score": -1.0到1.0,
    "crowd_emotion": "极度乐观|乐观|中性|悲观|极度悲观",
    "bull_ratio": 0-100,
    "top_themes": ["主题1", "主题2", "主题3"]
  }},
  "overall_sentiment": "综合两大社区散户情绪一句话描述"
}}"""

    raw = call_doubao(prompt,
                      system_prompt="你是A股市场情绪分析专家，严格JSON输出。",
                      max_tokens=600)
    if not raw:
        return {}
    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        return json.loads(raw[start:end])
    except Exception:
        return {}


def _local_news_analysis(macro: list, industry_news: list, company: list) -> dict:
    """不调用 AI，用规则统计给出粗略分析（--no-ai 时使用）"""
    def _layer_score(items):
        if not items:
            return {"rating": "中性", "score": 50, "key_events": [], "analysis": "暂无相关新闻"}
        sentiments = [it.get("sentiment", 0) for it in items]
        avg = sum(sentiments) / len(sentiments) if sentiments else 0
        score = int(50 + avg * 20)
        rating = "利好" if avg > 0.2 else "利空" if avg < -0.2 else "中性"
        key = [it["title"][:30] for it in items
               if it.get("importance") == "high"][:3]
        return {
            "rating": rating, "score": score,
            "key_events": key,
            "analysis": f"共{len(items)}条新闻，情感得分{avg:.2f}（规则统计，建议启用AI模式）",
        }

    macro_r = _layer_score(macro)
    industry_r = _layer_score(industry_news)
    company_r = _layer_score(company)
    avg_score = (macro_r["score"] + industry_r["score"] + company_r["score"]) // 3
    return {
        "macro": macro_r, "industry": industry_r, "company": company_r,
        "overall_impact": f"消息面综合评分约{avg_score}分（宏观{macro_r['rating']}/行业{industry_r['rating']}/公司{company_r['rating']}）",
    }


def _local_sentiment_analysis(guba: list, xueqiu: list) -> dict:
    """本地规则情绪统计（--no-ai 时使用）"""
    def _calc(items):
        if not items:
            return {}
        sentiments = [_classify_news(it["title"])["sentiment"] for it in items]
        avg = sum(sentiments) / len(sentiments)
        bull_ratio = int((sum(1 for s in sentiments if s > 0) / len(sentiments)) * 100)
        emotion = ("极度乐观" if avg > 0.5 else "乐观" if avg > 0.2
                   else "极度悲观" if avg < -0.5 else "悲观" if avg < -0.2 else "中性")
        return {
            "sentiment_score": round(avg, 2),
            "crowd_emotion": emotion,
            "bull_ratio": bull_ratio,
            "top_themes": [],
        }
    guba_r = _calc(guba)
    xq_r = _calc(xueqiu)
    
    parts = []
    if guba_r:
        parts.append(f"股吧{guba_r['crowd_emotion']}")
    if xq_r:
        parts.append(f"雪球{xq_r['crowd_emotion']}")
    overall = "、".join(parts) + "（规则统计）" if parts else "暂无情绪数据"
    
    return {
        "eastmoney_guba": guba_r,
        "xueqiu": xq_r,
        "overall_sentiment": overall,
    }


def analyze_news(ts_code: str, stock_name: str, industry: str, no_ai: bool = False) -> dict:
    """消息面分析主函数：采集→预处理→AI/本地分析→返回标准化字典"""
    macro_raw = fetch_news_macro(n_days=7)
    industry_raw = fetch_news_industry(industry, n_days=7)
    company_raw = fetch_news_company(ts_code, stock_name, n_days=7)
    guba_posts = fetch_sentiment_eastmoney(ts_code, n=50)
    xueqiu_posts = fetch_sentiment_xueqiu(ts_code, n=30)

    macro_filtered = _filter_and_sort(macro_raw, limit=10)
    industry_filtered = _filter_and_sort(industry_raw, limit=8)
    company_filtered = _filter_and_sort(company_raw, limit=10)

    if no_ai:
        news_analysis = _local_news_analysis(macro_filtered, industry_filtered, company_filtered)
        sentiment_analysis = _local_sentiment_analysis(guba_posts, xueqiu_posts)
    else:
        news_analysis = call_doubao_news_analysis(
            stock_name, industry, macro_filtered, industry_filtered, company_filtered
        )
        sentiment_analysis = call_doubao_sentiment(stock_name, guba_posts, xueqiu_posts)
        if not news_analysis:
            news_analysis = _local_news_analysis(macro_filtered, industry_filtered, company_filtered)
        if not sentiment_analysis:
            sentiment_analysis = _local_sentiment_analysis(guba_posts, xueqiu_posts)

    macro_r = news_analysis.get("macro", {}) or {}
    industry_r = news_analysis.get("industry", {}) or {}
    company_r = news_analysis.get("company", {}) or {}
    sentiment_r = sentiment_analysis or {}
    guba_r = sentiment_r.get("eastmoney_guba") or {}
    xueqiu_r = sentiment_r.get("xueqiu") or {}
    overall = news_analysis.get("overall_impact", "")

    def _rating_color(rating: str) -> str:
        if "利好" in rating:
            return "#dc2626"
        if "利空" in rating:
            return "#16a34a"
        return "#d97706"

    lines = []
    for label, r in [("宏观层", macro_r), ("行业层", industry_r), ("公司层", company_r)]:
        rating = r.get("rating", "中性")
        score = r.get("score", "-")
        analysis = r.get("analysis", "")
        key_events = r.get("key_events", [])
        color = _rating_color(rating)
        lines.append(
            f'<b>{label}</b> <span style="color:{color}">[{rating}]</span> 评分:{score}<br>'
        )
        if key_events:
            lines.append("关键事件: " + "、".join(key_events[:3]) + "<br>")
        if analysis:
            lines.append(f"{analysis}<br>")

    lines.append("<b>散户情绪</b><br>")
    guba_emotion = guba_r.get("crowd_emotion", "")
    guba_bull = guba_r.get("bull_ratio", "")
    if guba_emotion:
        guba_bear = 100 - int(guba_bull) if str(guba_bull).isdigit() else "?"
        lines.append(f"东财股吧: {guba_emotion} 多空比:{guba_bull}:{guba_bear}<br>")
    
    xueqiu_emotion = xueqiu_r.get("crowd_emotion", "")
    xueqiu_bull = xueqiu_r.get("bull_ratio", "")
    if xueqiu_emotion:
        xq_bear = 100 - int(xueqiu_bull) if str(xueqiu_bull).isdigit() else "?"
        lines.append(f"雪球: {xueqiu_emotion} 多空比:{xueqiu_bull}:{xq_bear}<br>")
    
    overall_sentiment = sentiment_r.get("overall_sentiment", "")
    if overall_sentiment:
        lines.append(f"综合情绪: {overall_sentiment}<br>")
    if overall:
        lines.append(f"<b>综合消息面:</b> {overall}")

    ai_summary = "".join(lines)

    return {
        "macro": macro_r,
        "industry": industry_r,
        "company": company_r,
        "sentiment": {
            "eastmoney_guba": guba_r,
            "xueqiu": xueqiu_r,
            "overall_sentiment": overall_sentiment,
        },
        "overall_impact": overall,
        "raw_articles": {
            "macro": macro_filtered,
            "industry": industry_filtered,
            "company": company_filtered,
        },
        "ai_summary": ai_summary,
    }


def analyze_weekly_trend(weekly_data):
    """周线级别趋势判断，返回 'bullish' / 'bearish' / 'neutral'"""
    if not weekly_data or len(weekly_data) < 10:
        return "neutral", "周线数据不足"
    closes = [sf(d.get("close"), 0) for d in weekly_data]

    ma5  = ma(closes, 5)
    ma10 = ma(closes, 10)
    ma20 = ma(closes, 20) if len(closes) >= 20 else None
    price = closes[-1]

    bull_pts, bear_pts = 0, 0
    reasons = []

    # 周线均线排列
    if ma5 and ma10:
        if ma5 > ma10 and price > ma5:
            bull_pts += 2
            reasons.append("周线MA5>MA10，价格在均线上方")
        elif ma5 < ma10 and price < ma5:
            bear_pts += 2
            reasons.append("周线MA5<MA10，价格在均线下方")
    if ma20:
        if price > ma20:
            bull_pts += 1
            reasons.append("周线价格站上MA20")
        else:
            bear_pts += 1

    # 周线趋势斜率
    slope = linear_slope(closes[-10:])
    if slope > 0:
        bull_pts += 1
    else:
        bear_pts += 1

    if bull_pts >= bear_pts + 2:
        return "bullish", "；".join(reasons[:2])
    elif bear_pts >= bull_pts + 2:
        return "bearish", "；".join(reasons[:2])
    else:
        return "neutral", "周线多空均衡"


# ─── 未来一周预测 ──────────────────────────────────────────────────────────────
def predict_next_week(daily_data, technical, fundamental, capital, weekly_data=None):
    """
    量化预测框架（未来约5个交易日）：
      - 信号聚合：技术面(60%) + 资金面(25%) + 基本面(15%)
      - 方向判断：上涨概率区间 [25%, 75%]（避免过度自信）
      - 价格目标：ATR × 1.5 + BOLL辅助 + 支撑阻力修正
      - 风险收益比、关键事件提示
    """
    pred = {
        "direction": "震荡整理",
        "probability_up": 50.0,
        "current_price": None,
        "target_high": None,
        "target_low": None,
        "key_support": None,
        "key_resistance": None,
        "risk_reward": None,
        "risk_level": "中等",
        "catalysts": [],
        "risks": [],
        "signal_stats": {},
        "summary": "",
    }
    if not daily_data:
        pred["summary"] = "数据不足，无法预测"
        return pred

    closes = [sf(d.get("close"), 0) for d in daily_data]
    price  = closes[-1]
    pred["current_price"] = price

    bull, bear = 0.0, 0.0
    cats, risks = [], []

    # ── 技术信号（使用族聚合信号避免相关信号重复投票）
    w_map = {"strong_bull": 2.0, "bull": 1.5, "weak_bull": 0.8,
             "weak_bear": -0.8, "bear": -1.5, "strong_bear": -2.0}
    family_sigs = technical.get("family_signals", [])
    if family_sigs:
        for fs in family_sigs:
            sig_type, sig_msg = fs[0], fs[1]
            agreement = fs[3] if len(fs) > 3 else 1.0
            v = w_map.get(sig_type, 0) * agreement
            if v > 0:
                bull += v
                cats.append(f"[技术] {sig_msg}")
            elif v < 0:
                bear += abs(v)
                risks.append(f"[技术] {sig_msg}")
    else:
        # 回退：无族信号时用原始信号
        for sig_type, sig_msg in technical.get("signals", []):
            v = w_map.get(sig_type, 0)
            if v > 0:
                bull += v
                cats.append(f"[技术] {sig_msg}")
            elif v < 0:
                bear += abs(v)
                risks.append(f"[技术] {sig_msg}")

    # ── 资金面加成
    mf_s = capital.get("money_flow", {}).get("score", 50)
    mg_s = capital.get("margin",     {}).get("score", 50)
    hs_s = capital.get("holders",    {}).get("score", 50)

    if mf_s >= 70:
        bull += 1.5;  cats.append("[资金] 主力大单持续净流入，支撑上涨")
    elif mf_s >= 60:
        bull += 0.8
    elif mf_s <= 30:
        bear += 1.5;  risks.append("[资金] 主力大单持续净流出，压制上涨")
    elif mf_s <= 40:
        bear += 0.8

    if mg_s >= 65:
        bull += 0.5;  cats.append("[融资] 融资余额上升，多头情绪升温")
    elif mg_s <= 35:
        bear += 0.5;  risks.append("[融资] 融资余额持续下降，谨慎操作")

    if hs_s >= 65:
        bull += 0.5;  cats.append("[筹码] 股东户数减少，筹码趋向集中")

    # 新增资金维度信号
    ht_s = capital.get("holdertrade", {}).get("score", 50)
    sf_s = capital.get("share_float", {}).get("score", 50)
    pl_s = capital.get("pledge",      {}).get("score", 50)
    hk_s = capital.get("hk_hold",     {}).get("score", 50)
    sv_s = capital.get("survey",      {}).get("score", 50)

    if ht_s >= 65:
        bull += 0.5;  cats.append("[增减持] 股东/高管净增持，管理层看好")
    elif ht_s <= 35:
        bear += 0.5;  risks.append("[增减持] 股东减持频繁，抛压较大")

    if sf_s <= 35:
        bear += 0.8;  risks.append("[解禁] 近期大量限售股解禁，供给压力大")
    elif sf_s <= 45:
        bear += 0.3;  risks.append("[解禁] 存在一定解禁压力")

    if pl_s <= 30:
        bear += 0.8;  risks.append("[质押] 质押比例过高，存在平仓风险")
    elif pl_s <= 40:
        bear += 0.3;  risks.append("[质押] 质押比例偏高，需警惕")

    if hk_s >= 65:
        bull += 0.5;  cats.append("[北向] 北向资金持续加仓")
    elif hk_s <= 35:
        bear += 0.5;  risks.append("[北向] 北向资金减仓")

    if sv_s >= 65:
        bull += 0.3;  cats.append("[调研] 机构密集调研，关注度高")

    # ── 基本面加成（短周期权重低）
    fa_s  = fundamental.get("score", 50)
    val_s = fundamental.get("valuation", {}).get("score", 50)
    if fa_s >= 70:
        bull += 0.5;  cats.append("[基本面] 财务扎实，具备估值支撑")
    elif fa_s <= 30:
        bear += 0.5;  risks.append("[基本面] 基本面偏弱，缺乏上行驱动")
    if val_s >= 70:
        bull += 0.5;  cats.append("[估值] 当前低估，安全边际较高")
    elif val_s <= 35:
        bear += 0.5;  risks.append("[估值] 当前高估，上行空间受限")

    # 业绩预告与券商预测加成
    fc = fundamental.get("forecast", {})
    fc_type = fc.get("data", {}).get("预告类型", "")
    if fc_type in ("预增", "扭亏", "续盈", "略增"):
        bull += 0.5;  cats.append(f"[业绩] 业绩预告：{fc_type}")
    elif fc_type in ("预减", "首亏", "续亏", "略减"):
        bear += 0.5;  risks.append(f"[业绩] 业绩预告：{fc_type}")

    analyst = fundamental.get("analyst", {})
    analyst_score = analyst.get("score", 50)
    if analyst_score >= 65:
        bull += 0.3;  cats.append("[研报] 券商评级以买入为主")
    elif analyst_score <= 35:
        bear += 0.3;  risks.append("[研报] 券商评级偏保守")

    # ── 周线共振修正
    weekly_trend = "neutral"
    weekly_reason = ""
    if weekly_data:
        weekly_trend, weekly_reason = analyze_weekly_trend(weekly_data)
    daily_bias = "bullish" if bull > bear else "bearish" if bear > bull else "neutral"

    weekly_adj = 0.0
    if weekly_trend == "bullish" and daily_bias == "bullish":
        weekly_adj = 1.0     # 日周共振看多 → 加成
        cats.append(f"[周线] 日周共振看多（{weekly_reason}）")
    elif weekly_trend == "bearish" and daily_bias == "bearish":
        weekly_adj = -1.0    # 日周共振看空 → 加成
        risks.append(f"[周线] 日周共振看空（{weekly_reason}）")
    elif weekly_trend == "bearish" and daily_bias == "bullish":
        weekly_adj = -0.5    # 周线空+日线多 → 反弹减持信号
        risks.append(f"[周线] 周线偏空，日线反弹可能受限")
    elif weekly_trend == "bullish" and daily_bias == "bearish":
        weekly_adj = 0.3     # 周线多+日线空 → 回调买入机会
        cats.append(f"[周线] 周线偏多，日线回调或为买入机会")

    if weekly_adj > 0:
        bull += weekly_adj
    elif weekly_adj < 0:
        bear += abs(weekly_adj)
    pred["weekly_trend"] = weekly_trend

    # ── 概率计算
    total = bull + bear
    raw_prob = (bull / total * 100) if total > 0 else 50
    # 映射到 [25, 75]（±2σ区间，避免过度自信）
    prob_up = 25 + (raw_prob / 100) * 50
    prob_up = max(25, min(75, prob_up))
    pred["probability_up"] = round(prob_up, 1)
    pred["signal_stats"] = {
        "看多信号强度": round(bull, 2),
        "看空信号强度": round(bear, 2),
        "上涨概率":     f"{prob_up:.1f}%",
    }

    # ── 目标价区间（ATR + BOLL）
    atr   = sf(technical.get("volatility", {}).get("ATR_14"))
    vol   = technical.get("volatility", {})
    mom   = technical.get("momentum",   {})
    bu    = sf(mom.get("BOLL_上"))
    bm    = sf(mom.get("BOLL_中"))
    bl    = sf(mom.get("BOLL_下"))
    supp  = sf(vol.get("近期关键支撑"))
    resis = sf(vol.get("近期关键阻力"))

    pred["key_support"]    = supp
    pred["key_resistance"] = resis

    if atr and price:
        base = atr * 1.5   # 一周预期波幅 ≈ 1.5 × ATR

        if prob_up >= 58:
            # 偏多
            th = min(filter(None, [price + base * 1.3, bu, resis]),
                     default=price + base)
            tl = max(filter(None, [price - base * 0.5, bl, supp]),
                     default=price - base * 0.8)
        elif prob_up <= 42:
            # 偏空
            th = min(filter(None, [price + base * 0.5, bm, resis]),
                     default=price + base * 0.5)
            tl = max(filter(None, [price - base * 1.3, bl, supp]),
                     default=price - base)
        else:
            # 震荡
            th = price + base * 0.8
            tl = price - base * 0.8

        pred["target_high"] = round(th, 2)
        pred["target_low"]  = round(tl, 2)

        upside   = (th - price) / price * 100
        downside = (price - tl) / price * 100
        if downside > 0:
            pred["risk_reward"] = round(upside / downside, 2)

    # ── 风险等级
    atr_pct = sf(technical.get("volatility", {}).get("ATR_%(日波幅预期)"), 2)
    if atr_pct:
        pred["risk_level"] = ("高风险" if atr_pct > 4 else
                              "中等风险" if atr_pct > 2 else "低风险")

    # ── 方向
    if prob_up >= 63:
        pred["direction"] = "看涨"
    elif prob_up >= 55:
        pred["direction"] = "偏多震荡"
    elif prob_up <= 37:
        pred["direction"] = "看跌"
    elif prob_up <= 45:
        pred["direction"] = "偏空震荡"
    else:
        pred["direction"] = "震荡整理"

    pred["catalysts"] = cats[:6]
    pred["risks"]     = risks[:6]

    # ── 摘要
    tl_str = f"{pred['target_low']:.2f}"  if pred["target_low"]  else "N/A"
    th_str = f"{pred['target_high']:.2f}" if pred["target_high"] else "N/A"
    rr_str = f"1:{pred['risk_reward']:.2f}" if pred.get("risk_reward") else "N/A"
    su_str = f"{supp:.2f}"  if supp  else "N/A"
    re_str = f"{resis:.2f}" if resis else "N/A"

    pred["summary"] = (
        f"综合 {len(technical.get('signals', []))} 个技术信号及资金面、基本面分析，"
        f"未来一周（约5个交易日）预判走势为【{pred['direction']}】，"
        f"上涨概率约 {prob_up:.0f}%。"
        f"价格参考区间 [{tl_str}, {th_str}]，"
        f"风险等级：{pred['risk_level']}，风险收益比 {rr_str}。"
        f"关键支撑 {su_str}，关键阻力 {re_str}。"
    )

    return pred


# ─── 综合评分 ──────────────────────────────────────────────────────────────────
def compute_composite(fundamental, technical, capital):
    fa = fundamental.get("score", 50)
    ta = technical.get("score",   50)
    ca = capital.get("score",     50)
    # 权重：基本面 40 | 技术面 35 | 资金面 25
    score = round(fa * 0.40 + ta * 0.35 + ca * 0.25, 1)

    if score >= 80:   rating = "★★★★★  强烈看多"
    elif score >= 70: rating = "★★★★   偏多"
    elif score >= 58: rating = "★★★    中性偏多"
    elif score >= 42: rating = "★★★    中性"
    elif score >= 30: rating = "★★     中性偏空"
    elif score >= 20: rating = "★★     偏空"
    else:             rating = "★      强烈看空"

    return {
        "score":             score,
        "rating":            rating,
        "fundamental_score": round(fa, 1),
        "technical_score":   round(ta, 1),
        "capital_score":     round(ca, 1),
        "weights": {"基本面": "40%", "技术面": "35%", "资金面": "25%"},
    }


# ─── 图表数据构建 ──────────────────────────────────────────────────────────────
def build_chart_data(daily_data, factor_data):
    """为前端 Chart.js 准备数据（含均线 + 技术指标）"""
    if not daily_data:
        return []

    closes = [sf(d.get("close"), 0) for d in daily_data]
    f_map  = {f.get("trade_date"): f for f in factor_data} if factor_data else {}
    chart  = []

    for i, d in enumerate(daily_data):
        row = {
            "trade_date": d.get("trade_date", ""),
            "open":   sf(d.get("open")),
            "high":   sf(d.get("high")),
            "low":    sf(d.get("low")),
            "close":  sf(d.get("close")),
            "vol":    sf(d.get("vol")),
            "amount": sf(d.get("amount")),
        }
        if i >= 4:  row["MA5"]  = round(sum(closes[i-4:i+1]) / 5,  3)
        if i >= 19: row["MA20"] = round(sum(closes[i-19:i+1]) / 20, 3)
        if i >= 59: row["MA60"] = round(sum(closes[i-59:i+1]) / 60, 3)

        f = f_map.get(row["trade_date"], {})
        row.update({
            "DIF":       sf(f.get("macd_dif")),
            "DEA":       sf(f.get("macd_dea")),
            "MACD_hist": sf(f.get("macd")),
            "RSI_6":     sf(f.get("rsi_6")),
            "KDJ_K":     sf(f.get("kdj_k")),
            "KDJ_D":     sf(f.get("kdj_d")),
            "KDJ_J":     sf(f.get("kdj_j")),
            "BOLL_up":   sf(f.get("boll_upper")),
            "BOLL_mid":  sf(f.get("boll_mid")),
            "BOLL_low":  sf(f.get("boll_lower")),
        })
        chart.append(row)

    return chart


# ─── 主流程 ───────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="A股股票专业深度分析 v2.0")
    parser.add_argument("--code",   required=True, help="股票代码，如 600519 或 600519.SH")
    parser.add_argument("--output", default=".",   help="JSON 输出目录")
    parser.add_argument("--no-ai",  action="store_true", help="跳过AI总结，使用本地格式化摘要")
    args = parser.parse_args()

    ts_code = args.code
    if "." not in ts_code:
        ts_code += ".SZ" if ts_code.startswith(("0", "3")) else ".SH"

    print(f"\n{'='*60}")
    print(f"  A股专业深度分析系统 v2.0  —  {ts_code}")
    print(f"  分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    # ── 数据采集（基础）
    print("\n[1/4] 基础数据采集中...")
    stock_basic    = fetch_stock_basic(ts_code)
    daily_data     = fetch_daily(ts_code, 120)
    daily_basic    = fetch_daily_basic(ts_code, 60)
    factor_data    = fetch_stk_factor(ts_code, 60)
    fina_data      = fetch_fina_indicator(ts_code)
    income_data    = fetch_income(ts_code)
    moneyflow      = fetch_moneyflow(ts_code, 30)
    margin_data    = fetch_margin(ts_code, 30)
    top10_holders  = fetch_top10_holders(ts_code)
    holder_number  = fetch_holder_number(ts_code)
    block_trades   = fetch_block_trade(ts_code, 30)
    concepts       = fetch_concepts(ts_code)
    weekly_data    = fetch_weekly(ts_code, 30)

    # ── 数据采集（增强）
    print("\n[2/4] 增强数据采集中...")
    report_rc      = fetch_report_rc(ts_code, 90)
    holdertrade    = fetch_holdertrade(ts_code, 180)
    forecast_data  = fetch_forecast(ts_code)
    balancesheet   = fetch_balancesheet(ts_code)
    cyq_perf_data  = fetch_cyq_perf(ts_code, 10)
    share_float    = fetch_share_float(ts_code, 90)
    mainbz_data    = fetch_mainbz(ts_code)
    pledge_data    = fetch_pledge_stat(ts_code)
    hk_hold_data   = fetch_hk_hold(ts_code, 30)
    surv_data      = fetch_stk_surv(ts_code, 180)
    nineturn_data  = fetch_nineturn(ts_code, 30)

    # ── 多维分析
    print("\n[3/4] 多维分析引擎运行中...")
    fundamental = analyze_fundamental(stock_basic, fina_data, daily_basic, income_data,
                                       balancesheet=balancesheet, forecast_data=forecast_data,
                                       mainbz_data=mainbz_data, report_rc=report_rc)
    technical   = analyze_technical(daily_data, factor_data,
                                     cyq_perf_data=cyq_perf_data, nineturn_data=nineturn_data)
    capital     = analyze_capital(moneyflow, margin_data, top10_holders,
                                  holder_number, block_trades,
                                  holdertrade=holdertrade, share_float=share_float,
                                  pledge_data=pledge_data, hk_hold_data=hk_hold_data,
                                  surv_data=surv_data)
    composite   = compute_composite(fundamental, technical, capital)
    prediction  = predict_next_week(daily_data, technical, fundamental, capital, weekly_data)
    chart_data  = build_chart_data(daily_data, factor_data)

    # ── AI 总结生成（可通过 --no-ai 跳过，使用本地HTML格式化摘要）
    if not args.no_ai:
        print("\n[4/4] AI 总结生成中...")
        stock_info_brief = {
            "名称": stock_basic.get("name", ts_code),
            "代码": stock_basic.get("ts_code", ts_code),
            "行业": stock_basic.get("industry", ""),
        }
        generate_ai_summaries(fundamental, technical, capital, stock_info_brief)
    else:
        print("\n[4/4] 使用本地格式化摘要（--no-ai）")

    # ── 消息面分析
    print(f"\n[5/5] 消息面分析中...")
    stock_name = stock_basic.get("name", ts_code)
    industry = stock_basic.get("industry", "")
    try:
        news = analyze_news(ts_code, stock_name, industry, no_ai=args.no_ai)
    except Exception as e:
        print(f"  消息面分析失败: {e}")
        news = {}

    # ── 整理输出
    result = {
        "ts_code": ts_code,
        "stock_info": {
            "名称":    stock_basic.get("name", ts_code),
            "代码":    stock_basic.get("ts_code", ts_code),
            "行业":    stock_basic.get("industry", ""),
            "市场":    stock_basic.get("market", ""),
            "概念":    concepts[:8],
            "上市日期": stock_basic.get("list_date", ""),
        },
        "composite":   composite,
        "fundamental": fundamental,
        "technical":   technical,
        "capital":     capital,
        "prediction":  prediction,
        "chart_data":  chart_data,
        "news":        news,
        "analyze_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # ── 保存
    print("\n[3/3] 保存分析结果...")
    os.makedirs(args.output, exist_ok=True)
    out_path = os.path.join(args.output, f"{ts_code}_analysis.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)

    # ── 控制台摘要
    p = prediction
    print(f"\n{'='*60}")
    print(f"  综合评分  : {composite['score']} | {composite['rating']}")
    print(f"  基本面    : {composite['fundamental_score']}  "
          f"技术面: {composite['technical_score']}  "
          f"资金面: {composite['capital_score']}")
    print(f"\n  ═══ 未来一周预测 ═══")
    print(f"  方向      : {p['direction']}  （上涨概率 {p['probability_up']}%）")
    if p["target_high"]:
        print(f"  目标区间  : [{p['target_low']:.2f},  {p['target_high']:.2f}]")
    print(f"  风险等级  : {p['risk_level']}"
          + (f"  ｜ 风险收益比 1:{p['risk_reward']:.2f}" if p.get("risk_reward") else ""))
    print(f"\n  预测摘要  : {p['summary'][:120]}...")
    print(f"\n  结果已保存: {out_path}")
    print(f"{'='*60}\n")

    return result


if __name__ == "__main__":
    main()
