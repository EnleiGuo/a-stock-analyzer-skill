"""
分析任务服务
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional
from nanoid import generate as nanoid

from config import settings
import sys
sys.path.insert(0, str(settings.SCRIPTS_DIR))

try:
    from stock_analyzer import (
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
        generate_ai_summaries,
        analyze_news,
    )
    ANALYZER_AVAILABLE = True
except ImportError as e:
    print(f"警告: 无法导入 stock_analyzer: {e}")
    ANALYZER_AVAILABLE = False


class AnalyzerService:
    """分析任务服务"""
    
    def __init__(self):
        # 内存任务存储（生产环境应使用 Redis）
        self._tasks: dict[str, dict] = {}
    
    async def create_task(self, ts_code: str, options: dict) -> str:
        """创建分析任务"""
        task_id = nanoid(size=12)
        
        # 标准化代码
        ts_code = self._normalize_code(ts_code)
        
        self._tasks[task_id] = {
            "id": task_id,
            "ts_code": ts_code,
            "options": options,
            "status": "queued",
            "progress": 0,
            "message": "等待处理",
            "result": None,
            "created_at": datetime.now().isoformat(),
        }
        
        return task_id
    
    async def get_task(self, task_id: str) -> Optional[dict]:
        """获取任务状态"""
        return self._tasks.get(task_id)
    
    async def run_analysis(self, task_id: str):
        """执行分析任务"""
        task = self._tasks.get(task_id)
        if not task:
            return
        
        if not ANALYZER_AVAILABLE:
            task["status"] = "failed"
            task["message"] = "分析引擎不可用"
            return
        
        ts_code = task["ts_code"]
        options = task["options"]
        no_ai = options.get("no_ai", False)
        
        try:
            task["status"] = "processing"
            
            # 获取数据（同步调用包装为异步）
            loop = asyncio.get_event_loop()
            
            # 1. 基本信息
            task["message"] = "获取基本信息"
            task["progress"] = 5
            stock_basic = await loop.run_in_executor(
                None, lambda: fetch_stock_basic(ts_code)
            )
            if not stock_basic:
                raise ValueError(f"无法获取股票 {ts_code} 的基本信息")
            
            # 2. 日线数据
            task["message"] = "获取日线数据"
            task["progress"] = 10
            daily_data = await loop.run_in_executor(
                None, lambda: fetch_daily(ts_code, 120)
            )
            
            # 3. 每日指标
            task["message"] = "获取每日指标"
            task["progress"] = 15
            daily_basic = await loop.run_in_executor(
                None, lambda: fetch_daily_basic(ts_code, 60)
            )
            
            # 4. 技术因子
            task["message"] = "获取技术因子"
            task["progress"] = 20
            factor_data = await loop.run_in_executor(
                None, lambda: fetch_stk_factor(ts_code, 60)
            )
            
            # 5. 财务指标
            task["message"] = "获取财务指标"
            task["progress"] = 25
            fina_data = await loop.run_in_executor(
                None, lambda: fetch_fina_indicator(ts_code)
            )
            
            # 6. 利润表
            task["message"] = "获取利润表"
            task["progress"] = 30
            income_data = await loop.run_in_executor(
                None, lambda: fetch_income(ts_code)
            )
            
            # 7. 资金流向
            task["message"] = "获取资金流向"
            task["progress"] = 35
            moneyflow = await loop.run_in_executor(
                None, lambda: fetch_moneyflow(ts_code, 30)
            )
            
            # 8. 融资融券
            task["message"] = "获取融资融券"
            task["progress"] = 40
            margin_data = await loop.run_in_executor(
                None, lambda: fetch_margin(ts_code, 30)
            )
            
            # 9. 股东数据
            task["message"] = "获取股东数据"
            task["progress"] = 45
            top10_holders = await loop.run_in_executor(
                None, lambda: fetch_top10_holders(ts_code)
            )
            holder_number = await loop.run_in_executor(
                None, lambda: fetch_holder_number(ts_code)
            )
            
            # 10. 大宗交易
            task["message"] = "获取大宗交易"
            task["progress"] = 50
            block_trades = await loop.run_in_executor(
                None, lambda: fetch_block_trade(ts_code, 30)
            )
            
            # 11. 周线数据
            task["message"] = "获取周线数据"
            task["progress"] = 55
            weekly_data = await loop.run_in_executor(
                None, lambda: fetch_weekly(ts_code, 30)
            )
            
            # 12. 其他数据
            task["message"] = "获取扩展数据"
            task["progress"] = 60
            report_rc = await loop.run_in_executor(
                None, lambda: fetch_report_rc(ts_code, 90)
            )
            holdertrade = await loop.run_in_executor(
                None, lambda: fetch_holdertrade(ts_code, 180)
            )
            forecast_data = await loop.run_in_executor(
                None, lambda: fetch_forecast(ts_code)
            )
            balancesheet = await loop.run_in_executor(
                None, lambda: fetch_balancesheet(ts_code)
            )
            cyq_perf_data = await loop.run_in_executor(
                None, lambda: fetch_cyq_perf(ts_code, 10)
            )
            share_float = await loop.run_in_executor(
                None, lambda: fetch_share_float(ts_code, 90)
            )
            mainbz_data = await loop.run_in_executor(
                None, lambda: fetch_mainbz(ts_code)
            )
            pledge_data = await loop.run_in_executor(
                None, lambda: fetch_pledge_stat(ts_code)
            )
            hk_hold_data = await loop.run_in_executor(
                None, lambda: fetch_hk_hold(ts_code, 30)
            )
            surv_data = await loop.run_in_executor(
                None, lambda: fetch_stk_surv(ts_code, 180)
            )
            nineturn_data = await loop.run_in_executor(
                None, lambda: fetch_nineturn(ts_code, 30)
            )
            
            # 13. 分析计算
            task["message"] = "计算基本面分析"
            task["progress"] = 70
            fundamental = analyze_fundamental(
                stock_basic, fina_data, daily_basic, income_data,
                balancesheet=balancesheet, forecast_data=forecast_data,
                mainbz_data=mainbz_data, report_rc=report_rc
            )
            
            task["message"] = "计算技术面分析"
            task["progress"] = 75
            technical = analyze_technical(
                daily_data, factor_data,
                cyq_perf_data=cyq_perf_data, nineturn_data=nineturn_data
            )
            
            task["message"] = "计算资金面分析"
            task["progress"] = 80
            capital = analyze_capital(
                moneyflow, margin_data, top10_holders,
                holder_number, block_trades,
                holdertrade=holdertrade, share_float=share_float,
                pledge_data=pledge_data, hk_hold_data=hk_hold_data,
                surv_data=surv_data
            )
            
            # 14. 综合评分
            task["message"] = "计算综合评分"
            task["progress"] = 85
            composite = compute_composite(fundamental, technical, capital)
            
            # 15. 走势预测
            task["message"] = "生成走势预测"
            task["progress"] = 88
            prediction = predict_next_week(
                daily_data, technical, fundamental, capital, weekly_data
            )
            
            # 16. AI 摘要（可选）
            if not no_ai:
                task["message"] = "生成 AI 摘要"
                task["progress"] = 90
                await loop.run_in_executor(
                    None,
                    lambda: generate_ai_summaries(fundamental, technical, capital, stock_basic)
                )
            
            # 17. 消息面分析
            task["message"] = "消息面分析"
            task["progress"] = 95
            stock_name = stock_basic.get("name", ts_code)
            industry = stock_basic.get("industry", "")
            try:
                news = await loop.run_in_executor(
                    None,
                    lambda: analyze_news(ts_code, stock_name, industry, no_ai=no_ai)
                )
            except Exception as e:
                print(f"消息面分析失败: {e}")
                news = {}
            # 18. 组装结果
            task["message"] = "完成"
            task["progress"] = 100
            task["status"] = "completed"
            
            # 适配前端数据结构（使用中文字段名）
            task["result"] = {
                "ts_code": ts_code,
                "stock_info": {
                    "名称": stock_basic.get("name", ""),
                    "代码": stock_basic.get("ts_code", ts_code),
                    "行业": stock_basic.get("industry", ""),
                    "市场": "SH" if ts_code.endswith(".SH") else "SZ" if ts_code.endswith(".SZ") else "BJ",
                    "概念": [],  # 暂无概念数据
                    "上市日期": stock_basic.get("list_date", ""),
                },
                "composite": composite,
                "fundamental": fundamental,
                "technical": technical,
                "capital": capital,
                "prediction": prediction,
                "news": news,
                "chart_data": {
                    "daily": daily_data[-60:] if daily_data else [],
                    "factor": factor_data[-60:] if factor_data else [],
                    "ma5": self._calc_ma(daily_data, 5) if daily_data else [],
                    "ma10": self._calc_ma(daily_data, 10) if daily_data else [],
                    "ma20": self._calc_ma(daily_data, 20) if daily_data else [],
                    "ma60": self._calc_ma(daily_data, 60) if daily_data else [],
                },
                "analyze_date": datetime.now().strftime("%Y-%m-%d"),
            }
            
        except Exception as e:
            task["status"] = "failed"
            task["message"] = str(e)
            print(f"分析任务 {task_id} 失败: {e}")
    
    def _normalize_code(self, code: str) -> str:
        """标准化股票代码"""
        code = code.upper().strip()
        
        if "." in code:
            return code
        
        if code.startswith("6"):
            return f"{code}.SH"
        elif code.startswith(("0", "3")):
            return f"{code}.SZ"
        elif code.startswith(("4", "8")):
            return f"{code}.BJ"
        else:
            return f"{code}.SH"

    def _calc_ma(self, daily_data: list, period: int) -> list:
        """计算移动平均线"""
        if not daily_data or len(daily_data) < period:
            return []
        
        closes = [d.get("close", 0) for d in daily_data]
        ma_values = []
        
        # 只计算最后60个数据点的MA（与 chart_data.daily 对应）
        start_idx = max(0, len(closes) - 60)
        for i in range(start_idx, len(closes)):
            if i >= period - 1:
                ma = sum(closes[i - period + 1:i + 1]) / period
                ma_values.append(round(ma, 2))
            else:
                ma_values.append(None)
        
        return ma_values


# 单例
analyzer_service = AnalyzerService()
