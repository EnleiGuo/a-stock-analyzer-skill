"""
报告管理路由
/api/reports/*
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from services.report_service import report_service


router = APIRouter()


class ReportCreate(BaseModel):
    """创建报告请求"""
    task_id: str
    title: Optional[str] = None


class ReportSummary(BaseModel):
    """报告摘要"""
    id: str
    title: str
    ts_code: str
    stock_name: str
    score: float
    created_at: str


class ReportDetail(BaseModel):
    """报告详情"""
    id: str
    title: str
    ts_code: str
    stock_name: str
    created_at: str
    data: dict


class ReportListResponse(BaseModel):
    """报告列表响应"""
    reports: list[ReportSummary]
    total: int


@router.post("")
async def create_report(request: ReportCreate):
    """
    保存分析结果为报告
    
    - task_id: 已完成的分析任务 ID
    - title: 自定义报告标题（可选）
    """
    report_id = await report_service.save(
        task_id=request.task_id,
        title=request.title,
    )
    
    if not report_id:
        raise HTTPException(status_code=400, detail="保存报告失败，任务可能未完成")
    
    return {
        "report_id": report_id,
        "share_url": f"/r/{report_id}",
    }


@router.get("", response_model=ReportListResponse)
async def list_reports(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    获取报告列表
    """
    reports, total = await report_service.list(limit=limit, offset=offset)
    return ReportListResponse(reports=reports, total=total)


@router.get("/{report_id}", response_model=ReportDetail)
async def get_report(report_id: str):
    """
    获取报告详情
    """
    report = await report_service.get(report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"报告 {report_id} 不存在")
    return report


@router.delete("/{report_id}")
async def delete_report(report_id: str):
    """
    删除报告
    """
    success = await report_service.delete(report_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"报告 {report_id} 不存在")
    return {"message": "报告已删除"}
