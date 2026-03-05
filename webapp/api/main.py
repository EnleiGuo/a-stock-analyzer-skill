"""
A股深度分析系统 - Web API 服务
FastAPI 后端入口
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers import stocks, analysis, reports, scanner
from services.stock_service import stock_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print(f"🚀 A股分析 API 启动 | 环境: {settings.ENV}")
    # 预加载股票列表缓存
    print("📦 预加载股票列表缓存...")
    await stock_service.preload_cache()
    print("✅ 股票列表缓存已就绪")
    yield
    # 关闭时
    print("👋 A股分析 API 关闭")

app = FastAPI(
    title="A股深度分析系统 API",
    description="基于 Tushare 数据的多维度股票分析服务",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(stocks.router, prefix="/api/stocks", tags=["股票查询"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["分析任务"])
app.include_router(reports.router, prefix="/api/reports", tags=["报告管理"])
app.include_router(scanner.router, prefix="/api/scanner", tags=["批量扫描"])


@app.get("/api/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "ok",
        "service": "a-stock-analyzer-api",
        "version": "1.0.0",
    }


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "A股深度分析系统 API",
        "docs": "/docs",
        "health": "/api/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
