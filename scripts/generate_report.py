#!/usr/bin/env python3
"""
A股深度分析 HTML 报告生成器 v2.0
读取 stock_analyzer.py 输出的 JSON，生成可视化 HTML 报告。
新增：未来一周预测面板、资金流向详情、信号列表、KDJ图表。
"""

import argparse
import json
import os
import sys
from datetime import datetime


# ─── 数据加载 ──────────────────────────────────────────────────────────────────
def load_data(data_dir, ts_code):
    path = os.path.join(data_dir, f"{ts_code}_analysis.json")
    if not os.path.exists(path):
        print(f"错误：找不到分析文件 {path}")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ─── 渲染工具 ──────────────────────────────────────────────────────────────────
def score_color(s):
    s = float(s) if s else 50
    return "#ef4444" if s >= 65 else "#f59e0b" if s >= 40 else "#22c55e"


def render_score_bar(score, label):
    c = score_color(score)
    return f'''
    <div class="score-bar">
      <div class="score-label">{label}</div>
      <div class="score-track"><div class="score-fill" style="width:{score}%;background:{c}"></div></div>
      <div class="score-value" style="color:{c}">{score}</div>
    </div>'''


def _fmt_list_item(x):
    """将列表元素格式化为可读字符串"""
    if isinstance(x, dict):
        name = x.get("名称") or x.get("name", "")
        parts = [name] if name else []
        for dk, dv in x.items():
            if dk in ("名称", "name"):
                continue
            parts.append(f"{dk}{dv}")
        return "，".join(parts) if parts else str(x)
    return str(x)


def render_kv_table(data_dict):
    if not data_dict:
        return '<p class="muted">暂无数据</p>'
    rows = ""
    for k, v in data_dict.items():
        if isinstance(v, list):
            v = " → ".join(_fmt_list_item(x) for x in v)
        elif v is None:
            v = '<span class="muted">N/A</span>'
        elif isinstance(v, bool):
            v = "✅ 是" if v else "❌ 否"
        rows += f'<tr><td class="td-k">{k}</td><td class="td-v">{v}</td></tr>'
    return f'<table class="kv-table">{rows}</table>'


def render_card(title, section, icon="📊", extra_html=""):
    score   = section.get("score", 50)
    comment = section.get("comment", "")
    data    = section.get("data", {})
    c       = score_color(score)
    return f'''
<div class="card">
  <div class="card-header">
    <span>{icon} {title}</span>
    <span class="card-score" style="color:{c}">{score} 分</span>
  </div>
  <div class="card-comment">{comment}</div>
  {render_kv_table(data)}
  {extra_html}
</div>'''


def render_summary_box(summary_text, color="#3b82f6"):
    if not summary_text:
        return ""
    return f'''
<div style="background:#fff;border-radius:12px;padding:18px;margin-bottom:14px;box-shadow:0 1px 3px rgba(0,0,0,.07);border-left:4px solid {color};">
  <div style="font-size:13px;color:#374151;line-height:1.8">{summary_text}</div>
</div>'''


def render_signal_list(signals):
    """渲染技术信号列表"""
    if not signals:
        return ""
    colors = {
        "strong_bull": "#dc2626", "bull": "#ef4444", "weak_bull": "#fca5a5",
        "weak_bear":   "#86efac", "bear": "#22c55e", "strong_bear": "#16a34a",
    }
    icons = {
        "strong_bull": "⬆⬆", "bull": "⬆", "weak_bull": "↑",
        "weak_bear":   "↓",   "bear": "⬇", "strong_bear": "⬇⬇",
    }
    items = ""
    for sig_type, sig_msg in signals:
        c = colors.get(sig_type, "#94a3b8")
        ic = icons.get(sig_type, "•")
        items += f'<li style="border-left:3px solid {c};padding:4px 8px;margin:4px 0;font-size:13px;">{ic} {sig_msg}</li>'
    return f'<ul style="list-style:none;padding:0;margin:0">{items}</ul>'


def render_news_section(news: dict) -> str:
    """渲染消息面分析部分"""
    if not news:
        return ""

    ai_summary = news.get("ai_summary", "")

    # Build section HTML
    section = '<div class="section news-section">\n'
    section += '<h2>消息面分析</h2>\n'

    if ai_summary:
        section += render_summary_box(ai_summary) + "\n"
    else:
        # Fallback: structured rendering
        for key, label in [("macro", "宏观层"), ("industry", "行业层"), ("company", "公司层")]:
            layer = news.get(key, {}) or {}
            rating = layer.get("rating", "中性")
            score = layer.get("score", "-")
            analysis = layer.get("analysis", "")
            key_events = layer.get("key_events", [])
            if "利好" in rating:
                color = "#dc2626"
            elif "利空" in rating:
                color = "#16a34a"
            else:
                color = "#d97706"
            section += f'<div class="news-layer"><b>{label}</b> <span style="color:{color}">[{rating}]</span> 评分:{score}<br>'
            if key_events:
                section += "关键事件: " + "、".join(key_events[:3]) + "<br>"
            if analysis:
                section += f"{analysis}"
            section += "</div>\n"

    # Raw articles table (show top 5 company news)
    company_articles = (news.get("raw_articles", {}) or {}).get("company", [])
    if company_articles:
        section += '<h3>公司相关新闻</h3>\n'
        section += '<table class="data-table"><tr><th>来源</th><th>标题</th><th>情感</th></tr>\n'
        for art in company_articles[:5]:
            title = art.get("title", "")
            source = art.get("source", "")
            clf = art.get("_classify", {}) or {}
            sentiment = clf.get("sentiment", 0)
            if sentiment == 1:
                sent_str = '<span style="color:#dc2626">利好</span>'
            elif sentiment == -1:
                sent_str = '<span style="color:#16a34a">利空</span>'
            else:
                sent_str = '<span style="color:#d97706">中性</span>'
            section += f"<tr><td>{source}</td><td>{title}</td><td>{sent_str}</td></tr>\n"
        section += "</table>\n"

    # Sentiment summary
    sentiment = news.get("sentiment", {}) or {}
    overall_sentiment = sentiment.get("overall_sentiment", "")
    overall_impact = news.get("overall_impact", "")
    if overall_sentiment or overall_impact:
        section += '<div class="news-overall">'
        if overall_sentiment:
            section += f"<b>散户情绪:</b> {overall_sentiment}<br>"
        if overall_impact:
            section += f"<b>综合消息面:</b> {overall_impact}"
        section += "</div>\n"

    section += "</div>\n"
    return section


def render_prediction_panel(prediction):
    """渲染预测面板（独立大卡片）"""
    if not prediction:
        return ""

    direction = prediction.get("direction", "震荡")
    prob_up   = prediction.get("probability_up", 50)
    t_high    = prediction.get("target_high")
    t_low     = prediction.get("target_low")
    price     = prediction.get("current_price")
    rr        = prediction.get("risk_reward")
    risk_lv   = prediction.get("risk_level", "中等")
    cats      = prediction.get("catalysts", [])
    risks     = prediction.get("risks", [])
    summary   = prediction.get("summary", "")
    stats     = prediction.get("signal_stats", {})
    supp      = prediction.get("key_support")
    resis     = prediction.get("key_resistance")

    # 方向颜色（A股惯例：红涨绿跌）
    dir_color = ("#ef4444" if "涨" in direction or "多" in direction
                 else "#22c55e" if "跌" in direction or "空" in direction
                 else "#f59e0b")
    prob_color = score_color(prob_up)
    risk_color = {"高风险": "#dc2626", "中等风险": "#f59e0b", "低风险": "#16a34a"}.get(risk_lv, "#64748b")

    # 目标区间文字
    range_html = ""
    if t_low and t_high and price:
        up_pct   = (t_high - price) / price * 100
        down_pct = (price  - t_low)  / price * 100
        range_html = f'''
        <div class="pred-range">
          <div class="pred-range-item" style="color:#ef4444">
            <div class="pred-range-val">{t_high:.2f}</div>
            <div class="pred-range-lbl">目标上沿 (+{up_pct:.1f}%)</div>
          </div>
          <div class="pred-range-mid">
            <div class="pred-range-val" style="color:#3b82f6">{price:.2f}</div>
            <div class="pred-range-lbl">当前价格</div>
          </div>
          <div class="pred-range-item" style="color:#22c55e">
            <div class="pred-range-val">{t_low:.2f}</div>
            <div class="pred-range-lbl">目标下沿 (-{down_pct:.1f}%)</div>
          </div>
        </div>'''

    # 看多/看空催化剂
    cat_items  = "".join(f'<li>✅ {c}</li>' for c in cats)
    risk_items = "".join(f'<li>⚠️ {r}</li>' for r in risks)

    supp_resis = ""
    if supp or resis:
        supp_str  = f"{supp:.2f}"  if supp  else "N/A"
        resis_str = f"{resis:.2f}" if resis else "N/A"
        supp_resis = f'''
        <div style="display:flex;gap:16px;margin-top:8px;font-size:13px;">
          <div style="flex:1;text-align:center;background:#dcfce7;border-radius:8px;padding:8px;">
            <div style="color:#16a34a;font-weight:600">关键支撑</div>
            <div style="font-size:16px;font-weight:700;color:#16a34a">{supp_str}</div>
          </div>
          <div style="flex:1;text-align:center;background:#fee2e2;border-radius:8px;padding:8px;">
            <div style="color:#dc2626;font-weight:600">关键阻力</div>
            <div style="font-size:16px;font-weight:700;color:#dc2626">{resis_str}</div>
          </div>
        </div>'''

    rr_html = f"<span style='color:#3b82f6;font-weight:600'>风险收益比 1:{rr:.2f}</span>" if rr else ""

    return f'''
<div class="pred-panel">
  <div class="pred-title">🔮 未来一周走势预测</div>

  <div class="pred-grid">
    <!-- 方向 + 概率 -->
    <div class="pred-metric">
      <div class="pred-metric-val" style="color:{dir_color}">{direction}</div>
      <div class="pred-metric-lbl">预判方向</div>
    </div>
    <div class="pred-metric">
      <div class="pred-metric-val" style="color:{prob_color}">{prob_up:.0f}%</div>
      <div class="pred-metric-lbl">上涨概率</div>
    </div>
    <div class="pred-metric">
      <div class="pred-metric-val" style="color:{risk_color}">{risk_lv}</div>
      <div class="pred-metric-lbl">波动风险等级</div>
    </div>
    <div class="pred-metric">
      <div class="pred-metric-val" style="color:#6366f1">{rr if not rr else f"1:{rr:.2f}"}</div>
      <div class="pred-metric-lbl">风险收益比</div>
    </div>
  </div>

  <!-- 信号统计 -->
  <div class="pred-stats">
    <span style="color:#ef4444">看多强度：{stats.get("看多信号强度", 0)}</span>
    &nbsp;&nbsp;|&nbsp;&nbsp;
    <span style="color:#22c55e">看空强度：{stats.get("看空信号强度", 0)}</span>
  </div>

  <!-- 目标区间 -->
  {range_html}
  {supp_resis}

  <!-- 催化剂 & 风险 -->
  <div class="pred-reasons">
    <div class="pred-reasons-col">
      <div class="pred-reasons-title" style="color:#ef4444">📈 看多催化剂</div>
      <ul style="margin:0;padding-left:16px;font-size:12px;color:#374151">
        {cat_items if cat_items else "<li>暂无明显看多信号</li>"}
      </ul>
    </div>
    <div class="pred-reasons-col">
      <div class="pred-reasons-title" style="color:#22c55e">📉 主要风险</div>
      <ul style="margin:0;padding-left:16px;font-size:12px;color:#374151">
        {risk_items if risk_items else "<li>暂无明显风险信号</li>"}
      </ul>
    </div>
  </div>

  <!-- 预测摘要 -->
  <div class="pred-summary">{summary}</div>
</div>'''


def generate_chart_js(chart_data):
    """生成 K 线 + 指标图表的 JS（Chart.js）"""
    if not chart_data:
        return ""

    dates      = [d["trade_date"] for d in chart_data]
    closes     = [d.get("close")    for d in chart_data]
    ma5        = [d.get("MA5")      for d in chart_data]
    ma20       = [d.get("MA20")     for d in chart_data]
    ma60       = [d.get("MA60")     for d in chart_data]
    volumes    = [d.get("vol", 0)   for d in chart_data]
    boll_up    = [d.get("BOLL_up")  for d in chart_data]
    boll_mid   = [d.get("BOLL_mid") for d in chart_data]
    boll_lo    = [d.get("BOLL_low") for d in chart_data]
    dif        = [d.get("DIF")      for d in chart_data]
    dea        = [d.get("DEA")      for d in chart_data]
    macd_hist  = [d.get("MACD_hist")for d in chart_data]
    rsi        = [d.get("RSI_6")    for d in chart_data]
    kdj_k      = [d.get("KDJ_K")    for d in chart_data]
    kdj_d      = [d.get("KDJ_D")    for d in chart_data]
    kdj_j      = [d.get("KDJ_J")    for d in chart_data]

    return f'''<script>
const labels = {json.dumps(dates)}.map(d => d.substring(4));
const closes = {json.dumps(closes)};
const ma5    = {json.dumps(ma5)};
const ma20   = {json.dumps(ma20)};
const ma60   = {json.dumps(ma60)};
const vols   = {json.dumps(volumes)};
const bollUp = {json.dumps(boll_up)};
const bollMid= {json.dumps(boll_mid)};
const bollLo = {json.dumps(boll_lo)};
const dif    = {json.dumps(dif)};
const dea    = {json.dumps(dea)};
const macdH  = {json.dumps(macd_hist)};
const rsi6   = {json.dumps(rsi)};
const kdjK   = {json.dumps(kdj_k)};
const kdjD   = {json.dumps(kdj_d)};
const kdjJ   = {json.dumps(kdj_j)};

const lineOpt = (label, data, color, dash=[]) => ({{
  label, data, borderColor: color, borderWidth: 1.5,
  pointRadius: 0, fill: false,
  borderDash: dash,
}});

function mkChart(id, config) {{
  const ctx = document.getElementById(id);
  if (ctx) new Chart(ctx.getContext('2d'), config);
}}

window.addEventListener('DOMContentLoaded', () => {{
  // 1. 价格 + 均线 + 布林带
  mkChart('priceChart', {{
    type: 'line',
    data: {{ labels, datasets: [
      lineOpt('收盘价', closes, '#3b82f6'),
      lineOpt('MA5',   ma5,    '#f59e0b', [2,2]),
      lineOpt('MA20',  ma20,   '#22c55e'),
      lineOpt('MA60',  ma60,   '#ef4444'),
      lineOpt('BOLL上', bollUp, '#94a3b880', [3,3]),
      lineOpt('BOLL中', bollMid,'#64748b80', [3,3]),
      lineOpt('BOLL下', bollLo, '#94a3b880', [3,3]),
    ]}},
    options: {{
      responsive:true, maintainAspectRatio:false,
      plugins:{{ title:{{ display:true, text:'价格走势与均线/布林带', font:{{size:13}} }} }},
      scales:{{ x:{{ ticks:{{ maxTicksLimit:10 }} }} }}
    }}
  }});

  // 2. 成交量
  const volColors = closes.map((c,i) => i>0 && c >= closes[i-1] ? '#ef444480' : '#22c55e80');
  mkChart('volChart', {{
    type: 'bar',
    data: {{ labels, datasets: [{{ label:'成交量', data:vols, backgroundColor:volColors }}] }},
    options: {{
      responsive:true, maintainAspectRatio:false,
      plugins:{{ title:{{ display:true, text:'成交量', font:{{size:13}} }}, legend:{{display:false}} }},
      scales:{{ x:{{ ticks:{{ maxTicksLimit:10 }} }} }}
    }}
  }});

  // 3. MACD
  const mColors = macdH.map(v => v >= 0 ? '#ef4444cc' : '#22c55ecc');
  mkChart('macdChart', {{
    type: 'bar',
    data: {{ labels, datasets: [
      {{ type:'line', label:'DIF', data:dif, borderColor:'#3b82f6', borderWidth:1.5, pointRadius:0, fill:false, order:0 }},
      {{ type:'line', label:'DEA', data:dea, borderColor:'#f59e0b', borderWidth:1.5, pointRadius:0, fill:false, order:0 }},
      {{ label:'MACD', data:macdH, backgroundColor:mColors, order:1 }},
    ]}},
    options: {{
      responsive:true, maintainAspectRatio:false,
      plugins:{{ title:{{ display:true, text:'MACD', font:{{size:13}} }} }},
      scales:{{ x:{{ ticks:{{ maxTicksLimit:10 }} }} }}
    }}
  }});

  // 4. RSI
  mkChart('rsiChart', {{
    type:'line',
    data:{{ labels, datasets:[
      lineOpt('RSI(6)', rsi6, '#8b5cf6'),
      {{ label:'超买70', data:labels.map(()=>70), borderColor:'#ef444480', borderWidth:1, pointRadius:0, fill:false, borderDash:[4,4] }},
      {{ label:'超卖30', data:labels.map(()=>30), borderColor:'#22c55e80', borderWidth:1, pointRadius:0, fill:false, borderDash:[4,4] }},
    ]}},
    options:{{
      responsive:true, maintainAspectRatio:false,
      plugins:{{ title:{{ display:true, text:'RSI(6)', font:{{size:13}} }} }},
      scales:{{ y:{{ min:0, max:100 }}, x:{{ ticks:{{ maxTicksLimit:10 }} }} }}
    }}
  }});

  // 5. KDJ
  mkChart('kdjChart', {{
    type:'line',
    data:{{ labels, datasets:[
      lineOpt('K', kdjK, '#3b82f6'),
      lineOpt('D', kdjD, '#f59e0b'),
      lineOpt('J', kdjJ, '#8b5cf6', [2,2]),
      {{ label:'超买80', data:labels.map(()=>80), borderColor:'#ef444860', borderWidth:1, pointRadius:0, fill:false, borderDash:[4,4] }},
      {{ label:'超卖20', data:labels.map(()=>20), borderColor:'#22c55e60', borderWidth:1, pointRadius:0, fill:false, borderDash:[4,4] }},
    ]}},
    options:{{
      responsive:true, maintainAspectRatio:false,
      plugins:{{ title:{{ display:true, text:'KDJ', font:{{size:13}} }} }},
      scales:{{ y:{{ min:-20, max:120 }}, x:{{ ticks:{{ maxTicksLimit:10 }} }} }}
    }}
  }});
}});
</script>'''


# ─── HTML 报告生成 ─────────────────────────────────────────────────────────────
def generate_html(data, out_path):
    info       = data.get("stock_info",  {})
    composite  = data.get("composite",   {})
    fundamental= data.get("fundamental", {})
    technical  = data.get("technical",   {})
    capital    = data.get("capital",     {})
    prediction = data.get("prediction",  {})
    chart_data = data.get("chart_data",  [])

    score  = composite.get("score",  50)
    rating = composite.get("rating", "中性")
    name   = info.get("名称", "")
    code   = info.get("代码", "")
    indust = info.get("行业", "")
    now    = data.get("analyze_date", datetime.now().strftime("%Y-%m-%d %H:%M"))
    concepts = info.get("概念", [])
    concept_tags = " ".join(f'<span class="tag">{c}</span>' for c in concepts[:6])

    sc = score_color(score)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{name}({code}) 深度分析报告</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:#f0f4f8;color:#1e293b;line-height:1.6}}
.wrap{{max-width:1160px;margin:0 auto;padding:20px}}

/* Header */
.header{{background:linear-gradient(135deg,#0f2544,#1d4ed8);color:#fff;padding:36px 32px;border-radius:16px;margin-bottom:20px}}
.header h1{{font-size:26px;margin-bottom:6px}}
.header .sub{{opacity:.82;font-size:13px}}
.tag{{display:inline-block;background:rgba(255,255,255,.18);border-radius:99px;padding:2px 10px;font-size:12px;margin:3px 2px}}

/* Score overview */
.score-box{{display:grid;grid-template-columns:180px 1fr;gap:20px;background:#fff;border-radius:16px;padding:24px;margin-bottom:20px;box-shadow:0 1px 4px rgba(0,0,0,.07)}}
.big-score{{display:flex;flex-direction:column;align-items:center;justify-content:center}}
.bsn{{font-size:64px;font-weight:700;color:{sc};line-height:1}}
.bsl{{font-size:13px;color:#64748b;margin-top:6px}}
.bsr{{font-size:16px;font-weight:600;color:{sc};margin-top:6px}}
.score-bars{{display:flex;flex-direction:column;justify-content:center;gap:14px}}
.score-bar{{display:flex;align-items:center;gap:10px}}
.score-label{{width:64px;font-size:13px;color:#475569;text-align:right}}
.score-track{{flex:1;height:22px;background:#e2e8f0;border-radius:11px;overflow:hidden}}
.score-fill{{height:100%;border-radius:11px}}
.score-value{{width:32px;font-size:15px;font-weight:600}}

/* Prediction panel */
.pred-panel{{background:#fff;border-radius:16px;padding:28px;margin-bottom:20px;box-shadow:0 1px 4px rgba(0,0,0,.07);border-top:4px solid #6366f1}}
.pred-title{{font-size:18px;font-weight:700;margin-bottom:18px;color:#1e293b}}
.pred-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px}}
.pred-metric{{text-align:center;background:#f8fafc;border-radius:12px;padding:14px 8px}}
.pred-metric-val{{font-size:22px;font-weight:700;margin-bottom:4px}}
.pred-metric-lbl{{font-size:12px;color:#64748b}}
.pred-stats{{text-align:center;font-size:13px;color:#64748b;margin-bottom:14px}}
.pred-range{{display:flex;justify-content:space-around;background:#f8fafc;border-radius:12px;padding:16px;margin-bottom:12px}}
.pred-range-item,.pred-range-mid{{text-align:center}}
.pred-range-val{{font-size:20px;font-weight:700}}
.pred-range-lbl{{font-size:12px;color:#64748b;margin-top:4px}}
.pred-reasons{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:14px}}
.pred-reasons-col{{background:#f8fafc;border-radius:10px;padding:12px}}
.pred-reasons-title{{font-size:13px;font-weight:600;margin-bottom:8px}}
.pred-summary{{margin-top:14px;background:#eff6ff;border-left:4px solid #3b82f6;padding:12px 14px;border-radius:0 8px 8px 0;font-size:13px;color:#1e3a5f;line-height:1.7}}

/* Section grid */
.dim-title{{font-size:18px;font-weight:700;margin:24px 0 12px;padding-left:12px;border-left:4px solid #3b82f6;color:#1e293b}}
.card-grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:16px}}
@media(max-width:768px){{.card-grid,.pred-grid,.pred-reasons{{grid-template-columns:1fr}}.score-box{{grid-template-columns:1fr}}}}

/* Card */
.card{{background:#fff;border-radius:12px;padding:18px;box-shadow:0 1px 3px rgba(0,0,0,.07)}}
.card-header{{display:flex;justify-content:space-between;align-items:center;font-size:15px;font-weight:600;margin-bottom:8px}}
.card-score{{font-size:18px;font-weight:700}}
.card-comment{{font-size:12px;color:#64748b;background:#f8fafc;border-left:3px solid #3b82f6;padding:6px 10px;border-radius:0 6px 6px 0;margin-bottom:10px}}

/* KV Table */
.kv-table{{width:100%;border-collapse:collapse;font-size:13px}}
.kv-table tr{{border-bottom:1px solid #f1f5f9}}
.kv-table tr:last-child{{border-bottom:none}}
.td-k{{padding:5px 0;color:#64748b;width:48%}}
.td-v{{padding:5px 0;font-weight:500;text-align:right}}
.muted{{color:#94a3b8;font-style:italic}}

/* Charts */
.chart-section{{background:#fff;border-radius:12px;padding:20px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,.07)}}
.chart-grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
@media(max-width:768px){{.chart-grid{{grid-template-columns:1fr}}.chart-box{{height:220px}}}}
@media(max-width:480px){{.chart-box{{height:180px}}.chart-caption{{font-size:11px}}}}
.chart-wrapper{{display:flex;flex-direction:column}}
.chart-box{{position:relative;height:240px;width:100%}}
.chart-caption{{font-size:12px;color:#64748b;text-align:center;margin-top:8px;line-height:1.5;padding:0 8px}}

/* Signals */
.signal-card{{background:#fff;border-radius:12px;padding:18px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.07)}}

/* News Section */
.news-section{{margin:20px 0}}
.news-layer{{margin:8px 0;padding:8px;background:#f9f9f9;border-radius:4px}}
.news-overall{{margin-top:12px;padding:10px;background:#fff8e1;border-radius:4px}}

/* Disclaimer */
.disc{{background:#fefce8;border:1px solid #fbbf24;border-radius:12px;padding:14px 18px;margin-top:20px;font-size:12px;color:#92400e}}
.footer{{text-align:center;color:#94a3b8;font-size:11px;margin-top:12px;padding-bottom:20px}}
</style>
</head>
<body>
<div class="wrap">

<!-- Header -->
<div class="header">
  <h1>{name} ({code})</h1>
  <div class="sub">{indust} &nbsp;|&nbsp; 报告生成时间: {now}</div>
  <div style="margin-top:10px">{concept_tags}</div>
</div>

<!-- Score Overview -->
<div class="score-box">
  <div class="big-score">
    <div class="bsn">{score}</div>
    <div class="bsl">综合评分</div>
    <div class="bsr">{rating}</div>
  </div>
  <div class="score-bars">
    {render_score_bar(composite.get("fundamental_score", 50), "基本面")}
    {render_score_bar(composite.get("technical_score",   50), "技术面")}
    {render_score_bar(composite.get("capital_score",     50), "资金面")}
  </div>
</div>

<!-- Prediction -->
{render_prediction_panel(prediction)}
'''

    # ── 技术图表
    if chart_data:
        html += '''
<div class="chart-section">
  <div class="dim-title">技术图表</div>
  <div class="chart-grid">
    <div class="chart-wrapper">
      <div class="chart-box"><canvas id="priceChart"></canvas></div>
      <div class="chart-caption">收盘价走势与MA5/MA20/MA60均线、布林带（BOLL）上中下轨叠加，反映趋势方向与价格运行通道</div>
    </div>
    <div class="chart-wrapper">
      <div class="chart-box"><canvas id="volChart"></canvas></div>
      <div class="chart-caption">每日成交量柱状图，红色为上涨日、绿色为下跌日，量能变化揭示多空力量对比</div>
    </div>
    <div class="chart-wrapper">
      <div class="chart-box"><canvas id="macdChart"></canvas></div>
      <div class="chart-caption">MACD指标：DIF线（蓝）与DEA线（橙）的金叉/死叉信号，柱状体红正绿负反映动能强弱</div>
    </div>
    <div class="chart-wrapper">
      <div class="chart-box"><canvas id="rsiChart"></canvas></div>
      <div class="chart-caption">RSI(6)相对强弱指标，70以上超买区间（红虚线）、30以下超卖区间（绿虚线），判断短期超买超卖</div>
    </div>
    <div class="chart-wrapper">
      <div class="chart-box"><canvas id="kdjChart"></canvas></div>
      <div class="chart-caption">KDJ随机指标：K线（蓝）、D线（橙）、J线（紫），80以上超买、20以下超卖，J值极端时关注反转</div>
    </div>
  </div>
</div>'''

    # ── 技术信号列表
    signals = technical.get("signals", [])
    if signals:
        html += f'''
<div class="dim-title">技术信号列表（共 {len(signals)} 个）</div>
<div class="signal-card">
  {render_signal_list(signals)}
</div>'''

    # ── 基本面
    html += '<div class="dim-title">基本面分析</div>'
    html += render_summary_box(fundamental.get("summary", ""), "#3b82f6")
    html += '<div class="card-grid">'
    for key, title, icon in [
        ("profitability",   "盈利能力",     "💰"),
        ("growth",          "成长能力",     "📈"),
        ("valuation",       "估值水平",     "🏷️"),
        ("solvency",        "偿债能力",     "🛡️"),
        ("cashflow",        "现金流质量",   "💵"),
        ("efficiency",      "运营效率",     "⚙️"),
        ("forecast",        "业绩预告",     "📢"),
        ("mainbz",          "主营业务构成", "🏭"),
        ("analyst",         "券商盈利预测", "🔬"),
        ("balance_detail",  "资产负债增强", "📑"),
    ]:
        sec = fundamental.get(key)
        if sec and sec.get("data"):
            html += render_card(title, sec, icon)
    html += "</div>"

    # ── 技术面
    html += '<div class="dim-title">技术面分析</div>'
    html += render_summary_box(technical.get("summary", ""), "#8b5cf6")
    html += '<div class="card-grid">'
    for key, title, icon in [
        ("trend",      "趋势分析",       "📊"),
        ("momentum",   "动量指标",       "🚀"),
        ("volume",     "量能分析",       "📶"),
        ("volatility", "波动与支撑阻力", "🌊"),
    ]:
        if key in technical:
            html += render_card(title, {"score": technical.get("score", 50),
                                        "data": technical[key],
                                        "comment": technical.get("comment", "")
                                        if key == "trend" else ""}, icon)
    # 新增技术面子维度
    for key, title, icon in [
        ("chip_data",  "筹码胜率分布", "🎯"),
        ("nineturn",   "神奇九转指标", "🔢"),
    ]:
        sec = technical.get(key)
        if sec and sec.get("data"):
            html += render_card(title, sec, icon)
    html += "</div>"

    # ── 资金面
    html += '<div class="dim-title">资金与筹码分析</div>'
    html += render_summary_box(capital.get("summary", ""), "#f59e0b")
    html += '<div class="card-grid">'
    for key, title, icon in [
        ("money_flow",  "主力资金流向", "💹"),
        ("margin",      "融资融券",     "📋"),
        ("holders",     "股东结构",     "👥"),
        ("block_trade", "大宗交易",     "🏢"),
        ("holdertrade", "股东增减持",   "📊"),
        ("share_float", "限售解禁",     "🔓"),
        ("pledge",      "股权质押",     "⛓️"),
        ("hk_hold",     "北向资金",     "🌏"),
        ("survey",      "机构调研",     "🔍"),
    ]:
        sec = capital.get(key)
        if sec and sec.get("data"):
            html += render_card(title, sec, icon)
    html += "</div>"

    # ── 消息面
    news_html = render_news_section(data.get("news", {}))
    html += news_html

    # ── 免责声明
    html += '''
<div class="disc">
  <strong>⚠️ 免责声明：</strong>
  本报告由程序自动生成，仅供研究参考，<strong>不构成任何投资建议</strong>。股市有风险，投资需谨慎。
  所有分析基于历史数据与量化模型，过往表现不代表未来收益。预测区间仅为统计估计，实际走势可能因突发事件、
  政策变化、市场情绪等多种不可控因素而显著偏离。请投资者独立判断，自行承担投资风险。
</div>
<div class="footer">A股专业深度分析系统 v2.0 &nbsp;·&nbsp; 数据来源：Tushare Pro &nbsp;·&nbsp; Generated by Claude</div>
</div>'''

    # ── 图表 JS
    if chart_data:
        html += generate_chart_js(chart_data)

    html += "\n</body>\n</html>"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML 报告已生成: {out_path}")


# ─── 主函数 ───────────────────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser(description="生成A股深度分析HTML报告 v2.0")
    p.add_argument("--code",     required=True, help="股票代码")
    p.add_argument("--data-dir", required=True, help="JSON 数据目录")
    p.add_argument("--output",   required=True, help="报告输出路径(.html)")
    args = p.parse_args()

    data = load_data(args.data_dir, args.code)
    generate_html(data, args.output)


if __name__ == "__main__":
    main()
