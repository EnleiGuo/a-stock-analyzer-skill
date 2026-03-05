"""
批量扫描服务
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
    from scan_hs300 import (
        fetch_stocks_by_scope,
        analyze_single_stock,
    )
    SCANNER_AVAILABLE = True
except ImportError as e:
    print(f"警告: 无法导入 scan_hs300: {e}")
    SCANNER_AVAILABLE = False


class ScannerService:
    """批量扫描服务"""
    
    def __init__(self):
        # 内存任务存储
        self._scans: dict[str, dict] = {}
    
    async def create_scan(self, market: str, threshold: float) -> str:
        """创建扫描任务"""
        scan_id = nanoid(size=12)
        
        self._scans[scan_id] = {
            "id": scan_id,
            "market": market,
            "threshold": threshold,
            "status": "queued",
            "total": 0,
            "completed": 0,
            "progress": 0,
            "high_score_count": 0,
            "results": [],
            "created_at": datetime.now().isoformat(),
        }
        
        return scan_id
    
    async def get_status(self, scan_id: str) -> Optional[dict]:
        """获取扫描状态"""
        scan = self._scans.get(scan_id)
        if not scan:
            return None
        
        return {
            "scan_id": scan_id,
            "status": scan["status"],
            "total": scan["total"],
            "completed": scan["completed"],
            "progress": scan["progress"],
            "high_score_count": scan["high_score_count"],
        }
    
    async def get_results(
        self,
        scan_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """获取扫描结果"""
        scan = self._scans.get(scan_id)
        if not scan:
            return []
        
        results = scan["results"]
        return results[offset:offset + limit]
    
    async def run_scan(self, scan_id: str):
        """执行扫描任务"""
        scan = self._scans.get(scan_id)
        if not scan:
            return
        
        if not SCANNER_AVAILABLE:
            scan["status"] = "failed"
            return
        
        market = scan["market"]
        threshold = scan["threshold"]
        
        try:
            scan["status"] = "running"
            
            # 获取股票列表
            loop = asyncio.get_event_loop()
            stocks = await loop.run_in_executor(
                None,
                lambda: fetch_stocks_by_scope(market)
            )
            
            scan["total"] = len(stocks)
            
            # 逐一分析
            for i, stock in enumerate(stocks):
                ts_code = stock["ts_code"]
                
                result = await loop.run_in_executor(
                    None,
                    lambda code=ts_code: analyze_single_stock(code)
                )
                
                scan["completed"] = i + 1
                scan["progress"] = round((i + 1) / len(stocks) * 100, 1)
                
                if result and result.get("composite_score", 0) >= threshold:
                    pred = result.get("prediction", {})
                    scan["results"].append({
                        "rank": len(scan["results"]) + 1,
                        "ts_code": ts_code,
                        "name": result.get("name", ""),
                        "composite_score": result.get("composite_score", 0),
                        "fundamental_score": result.get("fundamental_score", 0),
                        "technical_score": result.get("technical_score", 0),
                        "capital_score": result.get("capital_score", 0),
                        "direction": pred.get("direction", ""),
                        "target_low": pred.get("target_low"),
                        "target_high": pred.get("target_high"),
                        "risk_level": pred.get("risk_level", ""),
                    })
                    scan["high_score_count"] = len(scan["results"])
                
                # 让出控制权
                await asyncio.sleep(0.1)
            
            # 按评分排序
            scan["results"].sort(
                key=lambda x: x.get("composite_score", 0),
                reverse=True
            )
            
            # 更新排名
            for i, r in enumerate(scan["results"], 1):
                r["rank"] = i
            
            scan["status"] = "completed"
            
        except Exception as e:
            scan["status"] = "failed"
            print(f"扫描任务 {scan_id} 失败: {e}")


# 单例
scanner_service = ScannerService()
