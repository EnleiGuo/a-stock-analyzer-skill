"""
报告管理服务
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from nanoid import generate as nanoid

from config import settings
from services.analyzer_service import analyzer_service


class ReportService:
    """报告管理服务"""
    
    def __init__(self):
        self.reports_dir = settings.REPORTS_DIR
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    async def save(self, task_id: str, title: Optional[str] = None) -> Optional[str]:
        """
        保存分析结果为报告
        
        返回报告 ID，失败返回 None
        """
        task = await analyzer_service.get_task(task_id)
        if not task or task["status"] != "completed":
            return None
        
        result = task.get("result")
        if not result:
            return None
        
        report_id = nanoid(size=10)
        stock_info = result.get("stock_info", {})
        
        report = {
            "id": report_id,
            "title": title or f"{stock_info.get('name', '')} 分析报告",
            "ts_code": stock_info.get("ts_code", ""),
            "stock_name": stock_info.get("name", ""),
            "score": result.get("composite", {}).get("score", 0),
            "created_at": datetime.now().isoformat(),
            "data": result,
        }
        
        report_path = self.reports_dir / f"{report_id}.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        
        return report_id

    async def save_direct(
        self,
        ts_code: str,
        name: str,
        data: dict,
        title: Optional[str] = None
    ) -> Optional[str]:
        """
        直接保存分析数据为报告
        
        返回报告 ID，失败返回 None
        """
        stock_info = data.get("stock_info", {})
        stock_name = stock_info.get("名称", name) or name
        stock_code = stock_info.get("代码", ts_code) or ts_code
        
        # 去重逻辑：检查同一股票是否在1分钟内已有报告
        now = datetime.now()
        for report_path in self.reports_dir.glob("*.json"):
            try:
                # 检查文件修改时间
                mtime = datetime.fromtimestamp(report_path.stat().st_mtime)
                if (now - mtime).total_seconds() > 60:  # 超过1分钟的跳过
                    continue
                
                # 检查是否同一股票
                report = json.loads(report_path.read_text())
                if report.get("ts_code") == stock_code:
                    # 返回已存在的报告 ID
                    return report.get("id")
            except Exception:
                continue
        
        # 创建新报告
        report_id = nanoid(size=10)
        
        report = {
            "id": report_id,
            "title": title or f"{stock_name} 分析报告",
            "ts_code": stock_code,
            "stock_name": stock_name,
            "score": data.get("composite", {}).get("score", 0),
            "created_at": now.isoformat(),
            "data": data,
        }
        
        report_path = self.reports_dir / f"{report_id}.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        
        return report_id
    async def get(self, report_id: str) -> Optional[dict]:
        """获取报告详情"""
        report_path = self.reports_dir / f"{report_id}.json"
        
        if not report_path.exists():
            return None
        
        try:
            report = json.loads(report_path.read_text())
            return {
                "id": report["id"],
                "title": report["title"],
                "ts_code": report["ts_code"],
                "stock_name": report["stock_name"],
                "created_at": report["created_at"],
                "data": report["data"],
            }
        except Exception:
            return None
    
    async def list(self, limit: int = 20, offset: int = 0) -> tuple[list[dict], int]:
        """获取报告列表"""
        reports = []
        
        # 获取所有报告文件
        report_files = sorted(
            self.reports_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        
        total = len(report_files)
        
        # 分页
        for report_path in report_files[offset:offset + limit]:
            try:
                report = json.loads(report_path.read_text())
                reports.append({
                    "id": report["id"],
                    "title": report["title"],
                    "ts_code": report["ts_code"],
                    "stock_name": report["stock_name"],
                    "score": report.get("score", 0),
                    "created_at": report["created_at"],
                })
            except Exception:
                continue
        
        return reports, total
    
    async def delete(self, report_id: str) -> bool:
        """删除报告"""
        report_path = self.reports_dir / f"{report_id}.json"
        
        if not report_path.exists():
            return False
        
        try:
            report_path.unlink()
            return True
        except Exception:
            return False

    async def batch_delete(self, report_ids: list[str]) -> int:
        """
        批量删除报告
        
        返回实际删除的数量
        """
        deleted_count = 0
        for report_id in report_ids:
            report_path = self.reports_dir / f"{report_id}.json"
            if report_path.exists():
                try:
                    report_path.unlink()
                    deleted_count += 1
                except Exception:
                    pass
        return deleted_count


# 单例
report_service = ReportService()
