"""
配置管理
"""

import os
import sys
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""
    
    # 环境
    ENV: str = "development"
    DEBUG: bool = True
    
    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",  # Vite 开发服务器
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]
    
    # Tushare API
    TUSHARE_TOKEN: str = "TUSHARE_TOKEN_PLACEHOLDER"
    
    # 豆包 AI API
    DOUBAO_API_KEY: str = "DOUBAO_API_KEY_PLACEHOLDER"
    DOUBAO_ENDPOINT: str = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    DOUBAO_MODEL: str = "doubao-seed-2-0-pro-260215"
    
    # 路径配置
    BASE_DIR: Path = Path(__file__).parent.parent.parent  # a-stock-analyzer/
    SCRIPTS_DIR: Path = BASE_DIR / "scripts"
    DATA_DIR: Path = BASE_DIR / "data"
    REPORTS_DIR: Path = BASE_DIR / "webapp" / "reports"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# 将 scripts 目录添加到 Python 路径，以便导入分析引擎
sys.path.insert(0, str(settings.SCRIPTS_DIR))

# 确保报告目录存在
settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
