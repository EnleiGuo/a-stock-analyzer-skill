"""
报告管理路由
/api/reports/*
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from services.report_service import report_service


router = APIRouter()


class ReportCreate(BaseModel):
    """创建报告请求"""
    task_id: Optional[str] = None
    ts_code: Optional[str] = None
    name: Optional[str] = None
    data: Optional[dict] = None
    title: Optional[str] = None


class BatchDeleteRequest(BaseModel):
    """批量删除请求"""
    ids: list[str]

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
    
    支持两种方式：
    1. task_id: 从已完成的分析任务保存
    2. ts_code + name + data: 直接保存分析数据
    """
    if request.task_id:
        report_id = await report_service.save(
            task_id=request.task_id,
            title=request.title,
        )
    elif request.data:
        report_id = await report_service.save_direct(
            ts_code=request.ts_code or "",
            name=request.name or "",
            data=request.data,
            title=request.title,
        )
    else:
        raise HTTPException(status_code=400, detail="缺少 task_id 或 data")
    
    if not report_id:
        raise HTTPException(status_code=400, detail="保存报告失败")
    
    return {
        "id": report_id,
        "report_id": report_id,
        "share_url": f"/r/{report_id}",
    }


@router.post("/batch-delete")
async def batch_delete_reports(request: BatchDeleteRequest):
    """
    批量删除报告
    """
    deleted_count = await report_service.batch_delete(request.ids)
    return {"deleted": deleted_count}

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
