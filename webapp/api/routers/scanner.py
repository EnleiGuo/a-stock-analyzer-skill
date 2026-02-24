"""
批量扫描路由
/api/scanner/*
"""

import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from services.scanner_service import scanner_service


router = APIRouter()


class ScanRequest(BaseModel):
    """扫描请求"""
    market: str = "hs300"  # hs300, zz500, sz50, sse, szse, gem, star, all
    threshold: float = 80.0


class ScanResponse(BaseModel):
    """扫描响应"""
    scan_id: str
    market: str
    threshold: float
    status: str


class ScanStatus(BaseModel):
    """扫描状态"""
    scan_id: str
    status: str  # queued, running, completed, failed
    total: int
    completed: int
    progress: float
    high_score_count: int


class ScanResult(BaseModel):
    """扫描结果项"""
    rank: int
    ts_code: str
    name: str
    composite_score: float
    fundamental_score: float
    technical_score: float
    capital_score: float
    direction: str
    target_low: float | None
    target_high: float | None
    risk_level: str


# 市场范围映射
MARKET_NAMES = {
    "hs300": "沪深300",
    "zz500": "中证500",
    "sz50": "上证50",
    "sse": "上证主板",
    "szse": "深证主板",
    "gem": "创业板",
    "star": "科创板",
    "all": "全部A股",
}


@router.post("", response_model=ScanResponse)
async def create_scan(
    request: ScanRequest,
    background_tasks: BackgroundTasks,
):
    """
    启动批量扫描任务
    
    - market: 市场范围（hs300, zz500, sz50, sse, szse, gem, star, all）
    - threshold: 综合评分阈值
    """
    if request.market not in MARKET_NAMES:
        raise HTTPException(status_code=400, detail=f"无效的市场范围: {request.market}")
    
    scan_id = await scanner_service.create_scan(
        market=request.market,
        threshold=request.threshold,
    )
    
    # 后台启动扫描
    background_tasks.add_task(scanner_service.run_scan, scan_id)
    
    return ScanResponse(
        scan_id=scan_id,
        market=request.market,
        threshold=request.threshold,
        status="queued",
    )


@router.get("/{scan_id}", response_model=ScanStatus)
async def get_scan_status(scan_id: str):
    """
    查询扫描任务状态
    """
    status = await scanner_service.get_status(scan_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"扫描任务 {scan_id} 不存在")
    return status


@router.get("/{scan_id}/stream")
async def stream_scan(scan_id: str):
    """
    SSE 实时推送扫描进度
    """
    status = await scanner_service.get_status(scan_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"扫描任务 {scan_id} 不存在")
    
    async def event_generator():
        last_completed = -1
        
        while True:
            status = await scanner_service.get_status(scan_id)
            if not status:
                yield {"event": "error", "data": {"message": "任务不存在"}}
                break
            
            if status["completed"] > last_completed:
                yield {
                    "event": "progress",
                    "data": {
                        "completed": status["completed"],
                        "total": status["total"],
                        "progress": status["progress"],
                        "high_score_count": status["high_score_count"],
                    }
                }
                last_completed = status["completed"]
            
            if status["status"] == "completed":
                results = await scanner_service.get_results(scan_id)
                yield {"event": "complete", "data": {"results": results}}
                break
            
            if status["status"] == "failed":
                yield {"event": "error", "data": {"message": "扫描失败"}}
                break
            
            await asyncio.sleep(1)
    
    return EventSourceResponse(event_generator())


@router.get("/{scan_id}/results")
async def get_scan_results(
    scan_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    获取扫描结果列表
    """
    status = await scanner_service.get_status(scan_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"扫描任务 {scan_id} 不存在")
    
    results = await scanner_service.get_results(scan_id, limit=limit, offset=offset)
    return {
        "scan_id": scan_id,
        "status": status["status"],
        "total": status["high_score_count"],
        "results": results,
    }
