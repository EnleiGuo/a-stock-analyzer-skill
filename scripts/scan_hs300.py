#!/usr/bin/env python3
"""
沪深300高分股扫描器
扫描沪深300成分股，筛选综合评分≥阈值的股票
不使用AI摘要和消息面分析
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime

try:
    from tqdm import tqdm
except ImportError:
    print("请先安装 tqdm: pip install tqdm")
    sys.exit(1)

try:
    from tabulate import tabulate
except ImportError:
    print("请先安装 tabulate: pip install tabulate")
    sys.exit(1)

# 添加当前目录到路径以便导入 stock_analyzer
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stock_analyzer import (
    curl_api,
    fetch_stock_basic,
    fetch_daily,
    fetch_daily_basic,
    fetch_stk_factor,
    fetch_fina_indicator,
    fetch_income,
    fetch_moneyflow,
    fetch_margin,
    fetch_top10_holders,
    fetch_holder_number,
    fetch_block_trade,
    fetch_weekly,
    fetch_report_rc,
    fetch_holdertrade,
    fetch_forecast,
    fetch_balancesheet,
    fetch_cyq_perf,
    fetch_share_float,
    fetch_mainbz,
    fetch_pledge_stat,
    fetch_hk_hold,
    fetch_stk_surv,
    fetch_nineturn,
    analyze_fundamental,
    analyze_technical,
    analyze_capital,
    compute_composite,
    predict_next_week,
)


# 市场范围配置
MARKET_SCOPES = {
    "all": "全部A股",
    "hs300": "沪深300",
    "zz500": "中证500",
    "sz50": "上证50",
    "sse": "上证主板",
    "szse": "深证主板",
    "gem": "创业板",
    "star": "科创板",
    "bse": "北交所",
}


def fetch_index_constituents(index_code: str) -> list[dict]:
    """获取指数成分股"""
    now = datetime.now()
    start_date = now.replace(day=1).strftime("%Y%m%d")
    end_date = now.strftime("%Y%m%d")
    data = curl_api("index_weight", {
        "index_code": index_code,
        "start_date": start_date,
        "end_date": end_date,
    })
    if not data:
        last_month = now.replace(day=1) - __import__('datetime').timedelta(days=1)
        start_date = last_month.replace(day=1).strftime("%Y%m%d")
        end_date = last_month.strftime("%Y%m%d")
        data = curl_api("index_weight", {
            "index_code": index_code,
            "start_date": start_date,
            "end_date": end_date,
        })
    seen = set()
    result = []
    for item in data:
        code = item.get("con_code")
        if code and code not in seen:
            seen.add(code)
            result.append({"ts_code": code, "weight": item.get("weight", 0)})
    return result


def fetch_stocks_by_exchange(exchange: str = None, market: str = None) -> list[dict]:
    """按交易所或板块获取股票列表"""
    params = {"list_status": "L"}  # 只获取上市状态的
    if exchange:
        params["exchange"] = exchange
    if market:
        params["market"] = market
    
    data = curl_api("stock_basic", params)
    if not data:
        return []
    result = []
    for item in data:
        code = item.get("ts_code")
        if code:
            result.append({"ts_code": code, "name": item.get("name", "")})
    
    return result


def fetch_stocks_by_scope(scope: str) -> list[dict]:
    """根据市场范围获取股票列表"""
    if scope == "hs300":
        return fetch_index_constituents("399300.SZ")
    elif scope == "zz500":
        return fetch_index_constituents("000905.SH")
    elif scope == "sz50":
        return fetch_index_constituents("000016.SH")
    elif scope == "sse":
        # 上证主板: exchange=SSE, 排除科创板(688开头)
        stocks = fetch_stocks_by_exchange(exchange="SSE")
        return [s for s in stocks if not s["ts_code"].startswith("688")]
    elif scope == "szse":
        # 深证主板: exchange=SZSE, 排除创业板(300开头)
        stocks = fetch_stocks_by_exchange(exchange="SZSE")
        return [s for s in stocks if not s["ts_code"].startswith("300")]
    elif scope == "gem":
        # 创业板: 300开头
        stocks = fetch_stocks_by_exchange(exchange="SZSE")
        return [s for s in stocks if s["ts_code"].startswith("300")]
    elif scope == "star":
        # 科创板: 688开头
        stocks = fetch_stocks_by_exchange(exchange="SSE")
        return [s for s in stocks if s["ts_code"].startswith("688")]
    elif scope == "bse":
        # 北交所
        return fetch_stocks_by_exchange(exchange="BSE")
    elif scope == "all":
        # 全部A股
        return fetch_stocks_by_exchange()
    else:
        print(f"  未知的市场范围: {scope}，使用默认 hs300")
        return fetch_index_constituents("399300.SZ")


def analyze_single_stock(ts_code: str, retry: int = 2) -> dict | None:




    for attempt in range(retry + 1):
        try:
            stock_basic = fetch_stock_basic(ts_code)
            if not stock_basic:
                return None
            
            daily_data = fetch_daily(ts_code, 120)
            if not daily_data or len(daily_data) < 20:
                return None
            
            daily_basic = fetch_daily_basic(ts_code, 60)
            factor_data = fetch_stk_factor(ts_code, 60)
            fina_data = fetch_fina_indicator(ts_code)
            income_data = fetch_income(ts_code)
            moneyflow = fetch_moneyflow(ts_code, 30)
            margin_data = fetch_margin(ts_code, 30)
            top10_holders = fetch_top10_holders(ts_code)
            holder_number = fetch_holder_number(ts_code)
            block_trades = fetch_block_trade(ts_code, 30)
            weekly_data = fetch_weekly(ts_code, 30)
            
            report_rc = fetch_report_rc(ts_code, 90)
            holdertrade = fetch_holdertrade(ts_code, 180)
            forecast_data = fetch_forecast(ts_code)
            balancesheet = fetch_balancesheet(ts_code)
            cyq_perf_data = fetch_cyq_perf(ts_code, 10)
            share_float = fetch_share_float(ts_code, 90)
            mainbz_data = fetch_mainbz(ts_code)
            pledge_data = fetch_pledge_stat(ts_code)
            hk_hold_data = fetch_hk_hold(ts_code, 30)
            surv_data = fetch_stk_surv(ts_code, 180)
            nineturn_data = fetch_nineturn(ts_code, 30)
            
            fundamental = analyze_fundamental(
                stock_basic, fina_data, daily_basic, income_data,
                balancesheet=balancesheet, forecast_data=forecast_data,
                mainbz_data=mainbz_data, report_rc=report_rc
            )
            technical = analyze_technical(
                daily_data, factor_data,
                cyq_perf_data=cyq_perf_data, nineturn_data=nineturn_data
            )
            capital = analyze_capital(
                moneyflow, margin_data, top10_holders,
                holder_number, block_trades,
                holdertrade=holdertrade, share_float=share_float,
                pledge_data=pledge_data, hk_hold_data=hk_hold_data,
                surv_data=surv_data
            )
            
            composite = compute_composite(fundamental, technical, capital)
            prediction = predict_next_week(daily_data, technical, fundamental, capital, weekly_data)
            
            return {
                "ts_code": ts_code,
                "name": stock_basic.get("name", ""),
                "composite_score": composite["score"],
                "fundamental_score": composite["fundamental_score"],
                "technical_score": composite["technical_score"],
                "capital_score": composite["capital_score"],
                "prediction": {
                    "direction": prediction.get("direction", ""),
                    "target_low": prediction.get("target_low"),
                    "target_high": prediction.get("target_high"),
                    "risk_level": prediction.get("risk_level", ""),
                },
            }
            
        except Exception as e:
            if attempt < retry:
                time.sleep(3)
                continue
            return None
    
    return None


def save_partial_results(results: list[dict], output_dir: str, market: str):

    path = os.path.join(output_dir, f"_{market}_partial.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


def delete_partial_file(output_dir: str, market: str):

    path = os.path.join(output_dir, f"_{market}_partial.json")
    if os.path.exists(path):
        os.remove(path)


def format_terminal_output(results: list[dict], scan_info: dict) -> str:

    header = f"""
{'='*100}
  {scan_info['market_name']}扫描结果 — 综合评分 ≥ {scan_info['threshold']}  |  扫描时间: {scan_info['scan_time']}
  扫描股票: {scan_info['total_scanned']} 只  |  符合条件: {scan_info['total_matched']} 只  |  耗时: {scan_info['duration']}
{'='*100}
"""
    
    if not results:
        return header + "\n  未找到符合条件的股票\n"
    
    table_data = []
    for i, r in enumerate(results, 1):
        pred = r.get("prediction", {})
        target_low = pred.get("target_low")
        target_high = pred.get("target_high")
        if target_low and target_high:
            target_range = f"{target_low:.2f}-{target_high:.2f}"
        else:
            target_range = "-"
        
        table_data.append([
            i,
            r["ts_code"],
            r["name"],
            f"{r['composite_score']:.1f}",
            f"{r['fundamental_score']:.1f}",
            f"{r['technical_score']:.1f}",
            f"{r['capital_score']:.1f}",
            pred.get("direction", "-"),
            target_range,
            pred.get("risk_level", "-"),
        ])
    
    headers = ["排名", "代码", "名称", "综合评分", "基本面", "技术面", "资金面", 
               "预测方向", "目标区间", "风险等级"]
    table = tabulate(table_data, headers=headers, tablefmt="simple")
    
    return header + "\n" + table + "\n"


def format_csv_output(results: list[dict]) -> str:

    output = []
    output.append("排名,代码,名称,综合评分,基本面,技术面,资金面,预测方向,目标价低,目标价高,风险等级")
    
    for i, r in enumerate(results, 1):
        pred = r.get("prediction", {})
        target_low = pred.get("target_low", "")
        target_high = pred.get("target_high", "")
        if target_low:
            target_low = f"{target_low:.2f}"
        if target_high:
            target_high = f"{target_high:.2f}"
        
        output.append(",".join([
            str(i),
            r["ts_code"],
            r["name"],
            f"{r['composite_score']:.1f}",
            f"{r['fundamental_score']:.1f}",
            f"{r['technical_score']:.1f}",
            f"{r['capital_score']:.1f}",
            pred.get("direction", ""),
            str(target_low),
            str(target_high),
            pred.get("risk_level", ""),
        ]))
    
    return "\n".join(output)


def format_json_output(results: list[dict], scan_info: dict) -> str:

    for i, r in enumerate(results, 1):
        r["rank"] = i
    
    output = {
        "scan_time": scan_info["scan_time"],
        "threshold": scan_info["threshold"],
        "total_scanned": scan_info["total_scanned"],
        "total_analyzed": scan_info["total_analyzed"],
        "total_matched": scan_info["total_matched"],
        "duration_seconds": scan_info["duration_seconds"],
        "results": results,
    }
    
    return json.dumps(output, ensure_ascii=False, indent=2)


def show_market_menu() -> str:
    """显示市场范围选择菜单"""
    print("\n" + "="*60)
    print("  A股高分股扫描器 - 市场范围选择")
    print("="*60)
    print()
    
    # 按类别分组显示
    print("  【指数成分股】")
    print("    1. 沪深300    - 沪深两市市值最大的300只")
    print("    2. 中证500    - 排除沪深300后的500只中盘股")
    print("    3. 上证50     - 上交所规模最大的50只")
    print()
    print("  【按交易所】")
    print("    4. 上证主板   - 上交所主板（不含科创板）")
    print("    5. 深证主板   - 深交所主板（不含创业板）")
    print("    6. 创业板     - 深交所创业板（300开头）")
    print("    7. 科创板     - 上交所科创板（688开头）")
    print("    8. 北交所     - 北京证券交易所")
    print()
    print("  【全市场】")
    print("    9. 全部A股    - 沪深京三市全部股票")
    print()
    print("    0. 退出")
    print()
    
    menu_map = {
        "1": "hs300", "2": "zz500", "3": "sz50",
        "4": "sse", "5": "szse", "6": "gem", "7": "star", "8": "bse",
        "9": "all", "0": None
    }
    
    while True:
        choice = input("  请选择市场范围 [1-9, 0退出]: ").strip()
        if choice in menu_map:
            return menu_map[choice]
        print("  ❌ 无效选择，请重新输入")


def main():
    parser = argparse.ArgumentParser(description="A股高分股扫描器")
    parser.add_argument("--market", default=None, choices=MARKET_SCOPES.keys(),
                        help="直接指定市场范围（跳过菜单）")
    parser.add_argument("--output", default="./scan_results", help="输出目录")
    parser.add_argument("--threshold", type=float, default=80, help="最低综合评分阈值")
    parser.add_argument("--limit", type=int, default=0, help="最多扫描股票数（调试用，0=全部）")
    parser.add_argument("--no-save", action="store_true", help="不保存文件，仅终端显示")
    args = parser.parse_args()
    # 如果没有通过命令行指定市场，显示交互式菜单
    if args.market is None:
        selected_market = show_market_menu()
        if selected_market is None:
            print("\n  👋 已退出扫描器\n")
            sys.exit(0)
        args.market = selected_market
    
    market_name = MARKET_SCOPES.get(args.market, args.market)
    print(f"\n{'='*60}")
    print(f"  A股高分股扫描器")
    print(f"  市场: {market_name}  |  阈值: ≥{args.threshold}")
    print(f"  启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    print(f"[1/4] 获取{market_name}股票列表...")
    constituents = fetch_stocks_by_scope(args.market)
    if not constituents:
        print(f"  错误: 无法获取{market_name}股票列表")
        sys.exit(1)
    print(f"  获取到 {len(constituents)} 只股票")
    if args.limit > 0:
        constituents = constituents[:args.limit]
        print(f"  调试模式: 仅扫描前 {args.limit} 只")
    if not args.no_save:
        os.makedirs(args.output, exist_ok=True)
    print(f"\n[2/4] 开始扫描分析...")
    start_time = time.time()
    all_results = []
    skipped = []
    with tqdm(total=len(constituents), desc=f"{market_name}扫描中", 
              bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]") as pbar:
        for i, item in enumerate(constituents):
            ts_code = item["ts_code"]
            pbar.set_postfix_str(f"当前: {ts_code}")
            result = analyze_single_stock(ts_code)
            if result:
                all_results.append(result)
            else:
                # 分析失败的股票也记录，评分设为 -1 表示无数据
                all_results.append({
                    "ts_code": ts_code,
                    "name": "",
                    "composite_score": -1,
                    "fundamental_score": -1,
                    "technical_score": -1,
                    "capital_score": -1,
                    "prediction": {
                        "direction": "数据异常",
                        "target_low": None,
                        "target_high": None,
                        "risk_level": "",
                    },
                    "error": True,
                })
                skipped.append({"ts_code": ts_code, "reason": "数据异常"})
            # 每10只保存中间结果
            if (i + 1) % 10 == 0 and not args.no_save:
                save_partial_results(all_results, args.output, args.market)
            pbar.update(1)
    
    end_time = time.time()
    duration_seconds = int(end_time - start_time)
    duration_str = f"{duration_seconds // 60}分{duration_seconds % 60}秒"
    
    print(f"\n[3/4] 整理扫描结果...")
    # 按评分排序所有结果
    all_results.sort(key=lambda x: x["composite_score"], reverse=True)
    # 筛选高分股用于终端显示
    qualified = [r for r in all_results if r["composite_score"] >= args.threshold]
    scan_info = {
        "scan_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "threshold": args.threshold,
        "total_scanned": len(constituents),
        "total_analyzed": len(all_results),
        "total_matched": len(qualified),
        "duration": duration_str,
        "duration_seconds": duration_seconds,
        "market_name": market_name,
    }
    
    print(f"\n[4/4] 输出结果...")
    
    terminal_output = format_terminal_output(qualified, scan_info)
    print(terminal_output)
    
    if skipped:
        print(f"\n⚠️  跳过 {len(skipped)} 只股票（数据异常）:")
        for s in skipped[:10]:
            print(f"    - {s['ts_code']}: {s['reason']}")
        if len(skipped) > 10:
            print(f"    ... 及其他 {len(skipped) - 10} 只")
    
    if not args.no_save:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 保存所有结果（不只是高分股）
        csv_path = os.path.join(args.output, f"{args.market}_scan_{timestamp}.csv")
        with open(csv_path, "w", encoding="utf-8-sig") as f:
            f.write(format_csv_output(all_results))
        json_path = os.path.join(args.output, f"{args.market}_scan_{timestamp}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(format_json_output(all_results, scan_info))
        
        delete_partial_file(args.output, args.market)
        
        print(f"\n结果已保存（含全部 {len(all_results)} 只股票）:")
        print(f"  CSV:  {csv_path}")
        print(f"  JSON: {json_path}")
    
    print(f"\n{'='*60}")
    print(f"  扫描完成！共 {len(qualified)} 只股票评分 ≥ {args.threshold}")
    print(f"{'='*60}\n")
    
    return qualified


if __name__ == "__main__":
    main()
