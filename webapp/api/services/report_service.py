"""
报告管理服务
"""

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


# 单例
report_service = ReportService()
