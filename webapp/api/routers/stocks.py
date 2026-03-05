"""
股票查询路由
/api/stocks/*
"""
from __future__ import annotations

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from services.stock_service import stock_service


router = APIRouter()


class StockInfo(BaseModel):
    """股票基本信息"""
    ts_code: str
    name: str
    industry: str | None = None
    market: str | None = None
    list_date: str | None = None


class SearchResult(BaseModel):
    """搜索结果"""
    results: list[StockInfo]
    total: int


@router.get("/search", response_model=SearchResult)
async def search_stocks(
    q: str = Query(..., min_length=1, description="搜索关键词（代码或名称）"),
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
):
    """
    搜索股票
    
    支持按代码或名称模糊匹配
    """
    results = await stock_service.search(q, limit)
    return SearchResult(results=results, total=len(results))


@router.get("/{ts_code}", response_model=StockInfo)
async def get_stock_info(ts_code: str):
    """
    获取股票基本信息
    
    - ts_code: 股票代码（如 600519.SH）
    """
    info = await stock_service.get_info(ts_code)
    if not info:
        raise HTTPException(status_code=404, detail=f"股票 {ts_code} 不存在")
    return info


@router.get("/{ts_code}/quote")
async def get_stock_quote(ts_code: str):
    """
    获取股票实时行情摘要
    
    - ts_code: 股票代码
    """
    quote = await stock_service.get_quote(ts_code)
    if not quote:
        raise HTTPException(status_code=404, detail=f"股票 {ts_code} 行情获取失败")
    return quote
