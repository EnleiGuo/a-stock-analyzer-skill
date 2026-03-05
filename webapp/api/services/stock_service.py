"""
股票查询服务
"""
from __future__ import annotations

import asyncio
import time
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
    
    # 类级别缓存（所有实例共享）
    _stock_cache: list[dict] = []
    _cache_time: float = 0
    _cache_ttl: int = 3600 * 6  # 缓存6小时
    _cache_lock: asyncio.Lock | None = None
    
    def __init__(self):
        pass
    
    async def _ensure_cache(self):
        """确保股票列表缓存有效"""
        # 延迟初始化锁
        if StockService._cache_lock is None:
            StockService._cache_lock = asyncio.Lock()
        
        current_time = time.time()
        
        # 检查缓存是否有效
        if StockService._stock_cache and (current_time - StockService._cache_time) < StockService._cache_ttl:
            return
        
        # 获取锁，防止并发刷新
        async with StockService._cache_lock:
            # 双重检查
            if StockService._stock_cache and (current_time - StockService._cache_time) < StockService._cache_ttl:
                return
            
            if not curl_api:
                return
            
            print("[StockService] 正在刷新股票列表缓存...")
            
            # 在线程池中执行同步 API 调用
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: curl_api("stock_basic", {"list_status": "L"})
            )
            
            if results:
                # 预处理缓存数据，添加小写字段用于快速匹配
                StockService._stock_cache = [
                    {
                        "ts_code": s.get("ts_code", ""),
                        "code": s.get("ts_code", "").split(".")[0].lower(),
                        "name": s.get("name", ""),
                        "name_lower": s.get("name", "").lower(),
                        "industry": s.get("industry"),
                        "market": s.get("market"),
                        "list_date": s.get("list_date"),
                    }
                    for s in results
                ]
                StockService._cache_time = current_time
                print(f"[StockService] 股票列表缓存已更新，共 {len(StockService._stock_cache)} 只股票")
    
    async def search(self, query: str, limit: int = 10) -> list[dict]:
        """
        搜索股票
        
        支持代码和名称模糊匹配
        """
        await self._ensure_cache()
        
        if not StockService._stock_cache:
            return []
        
        query_lower = query.lower().strip()
        if not query_lower:
            return []
        
        matched = []
        
        # 精确匹配优先
        exact_matches = []
        prefix_matches = []
        contains_matches = []
        
        for stock in StockService._stock_cache:
            code = stock["code"]
            name_lower = stock["name_lower"]
            
            # 精确代码匹配
            if code == query_lower:
                exact_matches.append(stock)
            # 代码前缀匹配
            elif code.startswith(query_lower):
                prefix_matches.append(stock)
            # 名称包含匹配
            elif query_lower in name_lower:
                contains_matches.append(stock)
            # 代码包含匹配
            elif query_lower in code:
                contains_matches.append(stock)
        
        # 按优先级合并结果
        matched = exact_matches + prefix_matches + contains_matches
        
        # 返回格式化结果
        return [
            {
                "ts_code": s["ts_code"],
                "name": s["name"],
                "industry": s["industry"],
                "market": s["market"],
                "list_date": s["list_date"],
            }
            for s in matched[:limit]
        ]
    
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
    
    async def preload_cache(self):
        """预加载缓存（可在启动时调用）"""
        await self._ensure_cache()


# 单例
stock_service = StockService()
