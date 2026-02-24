"""
股票查询服务
"""

import asyncio
from functools import lru_cache
from typing import Optional

# 导入现有分析引擎
from config import settings
import sys
sys.path.insert(0, str(settings.SCRIPTS_DIR))

try:
    from stock_analyzer import curl_api, fetch_stock_basic, fetch_daily
except ImportError as e:
    print(f"警告: 无法导入 stock_analyzer: {e}")
    curl_api = None
    fetch_stock_basic = None
    fetch_daily = None


class StockService:
    """股票查询服务"""
    
    def __init__(self):
        self._cache = {}
    
    async def search(self, query: str, limit: int = 10) -> list[dict]:
        """
        搜索股票
        
        支持代码和名称模糊匹配
        """
        if not curl_api:
            return []
        
        # 在线程池中执行同步 API 调用
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: curl_api("stock_basic", {"list_status": "L"})
        )
        
        if not results:
            return []
        
        query_lower = query.lower()
        matched = []
        
        for stock in results:
            ts_code = stock.get("ts_code", "")
            name = stock.get("name", "")
            
            # 代码匹配（不区分大小写，支持不带后缀）
            code_match = (
                query_lower in ts_code.lower() or
                query_lower in ts_code.split(".")[0].lower()
            )
            # 名称匹配
            name_match = query_lower in name.lower()
            
            if code_match or name_match:
                matched.append({
                    "ts_code": ts_code,
                    "name": name,
                    "industry": stock.get("industry"),
                    "market": stock.get("market"),
                    "list_date": stock.get("list_date"),
                })
                
                if len(matched) >= limit:
                    break
        
        return matched
    
    async def get_info(self, ts_code: str) -> Optional[dict]:
        """获取股票基本信息"""
        if not fetch_stock_basic:
            return None
        
        # 补全代码后缀
        ts_code = self._normalize_code(ts_code)
        
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(
            None,
            lambda: fetch_stock_basic(ts_code)
        )
        
        if not info:
            return None
        
        return {
            "ts_code": info.get("ts_code"),
            "name": info.get("name"),
            "industry": info.get("industry"),
            "market": info.get("market"),
            "list_date": info.get("list_date"),
        }
    
    async def get_quote(self, ts_code: str) -> Optional[dict]:
        """获取实时行情摘要"""
        if not fetch_daily:
            return None
        
        ts_code = self._normalize_code(ts_code)
        
        loop = asyncio.get_event_loop()
        daily_data = await loop.run_in_executor(
            None,
            lambda: fetch_daily(ts_code, n=5)
        )
        
        if not daily_data:
            return None
        
        latest = daily_data[-1]
        prev = daily_data[-2] if len(daily_data) > 1 else latest
        
        close = float(latest.get("close", 0))
        prev_close = float(prev.get("close", 0))
        change = close - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0
        
        return {
            "ts_code": ts_code,
            "trade_date": latest.get("trade_date"),
            "open": latest.get("open"),
            "high": latest.get("high"),
            "low": latest.get("low"),
            "close": close,
            "volume": latest.get("vol"),
            "amount": latest.get("amount"),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
        }
    
    def _normalize_code(self, code: str) -> str:
        """标准化股票代码"""
        code = code.upper().strip()
        
        if "." in code:
            return code
        
        # 根据代码前缀判断市场
        if code.startswith("6"):
            return f"{code}.SH"
        elif code.startswith(("0", "3")):
            return f"{code}.SZ"
        elif code.startswith(("4", "8")):
            return f"{code}.BJ"
        else:
            return f"{code}.SH"


# 单例
stock_service = StockService()
