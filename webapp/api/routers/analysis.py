"""
分析任务路由
/api/analysis/*
"""

import asyncio
import json
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from services.analyzer_service import analyzer_service


router = APIRouter()


class AnalysisRequest(BaseModel):
    """分析请求"""
    ts_code: str
    options: Optional[dict] = None


class AnalysisResponse(BaseModel):
    """分析响应"""
    task_id: str
    ts_code: str
    status: str  # queued, processing, completed, failed


class AnalysisResult(BaseModel):
    """分析结果"""
    task_id: str
    status: str
    progress: int
    message: str | None = None
    result: dict | None = None


@router.post("", response_model=AnalysisResponse)
async def create_analysis(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
):
    """
    提交分析任务
    
    - ts_code: 股票代码（如 600519 或 600519.SH）
    - options: 可选配置（如 {"no_ai": true} 跳过 AI 摘要）
    """
    task_id = await analyzer_service.create_task(
        ts_code=request.ts_code,
        options=request.options or {},
    )
    
    # 后台启动分析
    background_tasks.add_task(analyzer_service.run_analysis, task_id)
    
    return AnalysisResponse(
        task_id=task_id,
        ts_code=request.ts_code,
        status="processing",
    )


@router.get("/{task_id}", response_model=AnalysisResult)
async def get_analysis(task_id: str):
    """
    查询分析任务状态和结果
    """
    task = await analyzer_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    
    return AnalysisResult(
        task_id=task_id,
        status=task["status"],
        progress=task.get("progress", 0),
        message=task.get("message"),
        result=task.get("result"),
    )


@router.get("/{task_id}/stream")
async def stream_analysis(task_id: str):
    """
    SSE 实时推送分析进度
    
    事件格式:
    - progress: {"step": "获取数据", "progress": 30}
    - complete: {"result": {...}}
    - error: {"message": "错误信息"}
    """
    task = await analyzer_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    
    async def event_generator():
        """生成 SSE 事件流"""
        last_progress = -1
        
        while True:
            task = await analyzer_service.get_task(task_id)
            if not task:
                yield {
                    "event": "error",
                    "data": json.dumps({"message": "任务不存在"}, ensure_ascii=False)
                }
                break
            
            current_progress = task.get("progress", 0)
            
            # 进度更新
            if current_progress > last_progress:
                yield {
                    "event": "progress",
                    "data": json.dumps({
                        "step": task.get("message", "处理中"),
                        "progress": current_progress,
                    }, ensure_ascii=False)
                }
                last_progress = current_progress
            
            # 完成
            if task["status"] == "completed":
                yield {
                    "event": "complete",
                    "data": json.dumps(task.get("result", {}), ensure_ascii=False, default=str)
                }
                break
            
            # 失败
            if task["status"] == "failed":
                yield {
                    "event": "error",
                    "data": json.dumps({"message": task.get("message", "分析失败")}, ensure_ascii=False)
                }
                break
            
            await asyncio.sleep(0.5)
    
    return EventSourceResponse(event_generator())
