# A股深度分析系统 - 前端 Web 应用设计文档

> 创建日期: 2026-02-24
> 状态: 已批准

## 1. 概述

为现有的 A 股专业深度分析系统 v2.0 添加 Web 前端界面，实现以下核心功能：

- **快速查询股票** - 输入代码/名称即时搜索
- **生成股票分析** - 调用后端分析引擎，实时展示进度
- **保存预览报告** - 分析结果可保存为报告
- **分享报告** - 通过唯一链接分享给他人
- **股票扫描** - 批量扫描指定市场，筛选高分股票

## 2. 目标用户

**对外展示/SaaS 产品** - 需要专业的用户界面和良好的用户体验。

## 3. 技术栈选型

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| 后端 API | FastAPI + Python | 与现有分析引擎无缝集成 |
| 前端框架 | Vite + React 18 + TypeScript | 现代化开发体验 |
| UI 组件库 | shadcn/ui + Tailwind CSS | 现代简约风格，高度可定制 |
| 图表库 | ECharts | 专业金融图表，原生支持 K 线图 |
| 状态管理 | Zustand | 轻量级，TypeScript 友好 |
| 数据获取 | TanStack Query | 缓存、重试、后台更新 |
| 进度推送 | SSE (Server-Sent Events) | 简单可靠的实时推送 |

## 4. 架构设计

### 4.1 整体架构

采用 **单仓库全栈（Monorepo）** 架构：

```
a-stock-analyzer/
├── api/                          # FastAPI 后端服务
│   ├── main.py                   # 入口，CORS/中间件配置
│   ├── config.py                 # 环境变量/配置
│   ├── routers/
│   │   ├── stocks.py             # /api/stocks/* 股票查询
│   │   ├── analysis.py           # /api/analysis/* 分析任务
│   │   ├── reports.py            # /api/reports/* 报告管理
│   │   └── scanner.py            # /api/scanner/* 批量扫描
│   ├── services/
│   │   ├── analyzer.py           # 封装 scripts/stock_analyzer.py
│   │   ├── scanner.py            # 封装 scripts/scan_hs300.py
│   │   └── report_store.py       # 报告存储（JSON 文件）
│   ├── models/                   # Pydantic 数据模型
│   └── tasks/                    # 后台任务（扫描队列）
│
├── web/                          # Vite + React 前端
│   ├── src/
│   │   ├── components/           # UI 组件
│   │   │   ├── ui/               # shadcn/ui 基础组件
│   │   │   ├── charts/           # ECharts 图表组件
│   │   │   └── analysis/         # 分析结果展示组件
│   │   ├── pages/
│   │   │   ├── Home.tsx          # 首页（搜索入口）
│   │   │   ├── Analysis.tsx      # 分析结果页
│   │   │   ├── Scanner.tsx       # 扫描任务页
│   │   │   └── Report.tsx        # 分享报告页
│   │   ├── hooks/                # 自定义 Hooks
│   │   ├── services/             # API 调用
│   │   └── stores/               # 状态管理（Zustand）
│   ├── package.json
│   └── vite.config.ts
│
├── scripts/                      # 现有分析引擎（保持不变）
│   ├── stock_analyzer.py
│   ├── generate_report.py
│   └── scan_hs300.py
│
├── data/                         # 分析数据存储
├── reports/                      # 生成的报告存储
└── docker-compose.yml            # 本地开发/部署配置
```

### 4.2 处理模式

- **单股分析**: 实时同步处理（30-60秒），通过 SSE 推送进度
- **批量扫描**: 后台异步处理，支持进度查询和结果推送

## 5. API 设计

### 5.1 股票查询 `/api/stocks`

```
GET  /api/stocks/search?q=茅台          # 模糊搜索（名称/代码）
GET  /api/stocks/{ts_code}              # 获取基本信息
GET  /api/stocks/{ts_code}/quote        # 实时行情摘要
```

### 5.2 分析任务 `/api/analysis`

```
POST /api/analysis                      # 提交分析任务
     Body: { "ts_code": "600519.SH", "options": { "no_ai": false } }
     Response: { "task_id": "uuid", "status": "processing" }

GET  /api/analysis/{task_id}            # 查询任务状态/结果
     Response: {
       "status": "completed|processing|failed",
       "progress": 80,
       "result": { ... 完整分析数据 ... }
     }

GET  /api/analysis/{task_id}/stream     # SSE 实时进度推送
```

### 5.3 报告管理 `/api/reports`

```
GET  /api/reports                       # 列出所有报告
GET  /api/reports/{report_id}           # 获取报告详情
POST /api/reports                       # 保存分析结果为报告
     Body: { "analysis_task_id": "uuid", "title": "自定义标题" }
     Response: { "report_id": "uuid", "share_url": "/r/abc123" }

DELETE /api/reports/{report_id}         # 删除报告
```

### 5.4 批量扫描 `/api/scanner`

```
POST /api/scanner                       # 启动扫描任务
     Body: { 
       "market": "hs300|zz500|sz50|sse|szse|gem|star|all",
       "threshold": 80 
     }
     Response: { "scan_id": "uuid", "status": "queued" }

GET  /api/scanner/{scan_id}             # 查询扫描状态
GET  /api/scanner/{scan_id}/stream      # SSE 实时进度
GET  /api/scanner/{scan_id}/results     # 获取扫描结果列表
```

## 6. 前端页面设计

### 6.1 页面路由

| 页面 | 路由 | 功能 |
|------|------|------|
| 首页 | `/` | 搜索框 + 热门股票 + 最近分析 |
| 分析结果页 | `/analysis/:ts_code` | 完整分析报告展示 |
| 扫描任务页 | `/scanner` | 市场选择 + 扫描进度 + 结果列表 |
| 分享报告页 | `/r/:report_id` | 公开分享链接 |
| 历史报告 | `/reports` | 已保存报告列表管理 |

### 6.2 首页布局

```
┌─────────────────────────────────────────────────────────────┐
│  🏠 A股深度分析                              [扫描] [报告]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│           🔍 输入股票代码或名称快速分析                      │
│           [___________________________] [分析]              │
│                                                             │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  📈 热门分析                                                │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ 600519  │ │ 000001  │ │ 300750  │ │ 002475  │           │
│  │ 贵州茅台 │ │ 平安银行 │ │宁德时代 │ │立讯精密 │           │
│  │  85分   │ │  72分   │ │  68分   │ │  78分   │           │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
│                                                             │
│  📋 最近分析                                                │
│  ├─ 300548 博彦科技  82分  偏多  10分钟前                   │
│  ├─ 002471 中超控股  65分  中性  1小时前                    │
│  └─ ...                                                     │
└─────────────────────────────────────────────────────────────┘
```

### 6.3 分析结果页

- 顶部：综合评分（星级 + 数字）+ 未来一周预测
- 中部：Tab 切换（基本面/技术面/资金面）+ K 线图
- 底部：各维度详细分析卡片 + AI 摘要
- 操作：保存报告、分享链接

### 6.4 扫描任务页

- 市场范围选择（沪深300/中证500/上证50/全A股等）
- 评分阈值设置
- 实时扫描进度条
- 结果表格（排名、代码、名称、各维度评分、预测方向）

## 7. 数据流设计

### 7.1 单股分析流程

```
用户输入 → POST /api/analysis → 后端开始分析
    ↓
前端 SSE 连接 → 接收进度事件 → 更新进度条
    ↓
分析完成 → 返回结果 → 渲染分析报告
```

### 7.2 批量扫描流程

```
用户选择市场 → POST /api/scanner → 任务入队
    ↓
后台异步处理 → 更新任务状态
    ↓
前端轮询/SSE → 显示进度 → 逐步展示结果
```

## 8. 存储设计

### 8.1 报告存储

MVP 阶段使用 JSON 文件存储：

```
reports/
├── abc123.json       # 报告 ID 作为文件名
├── def456.json
└── ...
```

报告结构：
```json
{
  "id": "abc123",
  "title": "贵州茅台 分析报告",
  "created_at": "2026-02-24T20:00:00Z",
  "data": { ... 完整分析数据 ... }
}
```

### 8.2 后期升级路径

- SQLite（单机持久化）
- PostgreSQL（多实例部署）
- Redis（扫描任务队列）

## 9. 部署方案

### 9.1 开发环境

```bash
# 后端
cd api && uvicorn main:app --reload --port 8000

# 前端
cd web && pnpm dev  # 代理到 :8000
```

### 9.2 生产部署

使用 Docker Compose 单机部署：

```yaml
services:
  api:
    build: ./api
    ports: ["8000:8000"]
    volumes:
      - ./scripts:/app/scripts:ro
      - ./data:/app/data
      - ./reports:/app/reports

  web:
    build: ./web
    ports: ["80:80"]
    depends_on: [api]
```

## 10. 用户认证

**MVP 阶段暂不实现用户系统**，所有功能开放访问。

后期可添加：
- 邮箱/密码 + JWT
- 微信/手机号一键登录
- 付费功能权限控制

## 11. 分享功能

使用 UUID 唯一链接：
- 报告 ID 使用 nanoid 生成（如 `abc123def4`）
- 分享 URL 格式：`https://example.com/r/abc123def4`
- 无需登录即可访问分享链接

## 12. 依赖清单

### 后端 (api/requirements.txt)

```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
sse-starlette>=1.8.0
nanoid>=2.0.0
python-multipart
pydantic>=2.0.0
```

### 前端 (web/package.json)

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-router-dom": "^6.x",
    "@tanstack/react-query": "^5.x",
    "zustand": "^4.x",
    "echarts": "^5.x",
    "echarts-for-react": "^3.x",
    "tailwindcss": "^3.x",
    "lucide-react": "^0.x",
    "nanoid": "^5.x",
    "clsx": "^2.x",
    "tailwind-merge": "^2.x"
  }
}
```

## 13. 设计决策记录

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 架构模式 | 单仓库全栈 | MVP 快速交付，后期易分离 |
| 处理模式 | 混合（同步+异步） | 单股实时体验好，批量避免阻塞 |
| 后端框架 | FastAPI | 与 Python 分析引擎无缝集成 |
| UI 框架 | shadcn/ui | 现代简约，打包体积小 |
| 图表库 | ECharts | 金融图表功能最强 |
| 进度推送 | SSE | 简单可靠，兼容性好 |
| 认证 | 暂无 | MVP 简化，后期迭代 |
| 存储 | JSON 文件 | MVP 简化，后期可升级数据库 |

---

**文档状态**: 已批准，准备进入实施阶段
