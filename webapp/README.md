# A股深度分析系统 - Web 应用

基于 FastAPI + React 的 Web 前端界面，提供股票查询、分析、报告保存/分享、批量扫描等功能。

## 项目结构

```
webapp/
├── api/                    # FastAPI 后端
│   ├── main.py             # 入口
│   ├── config.py           # 配置
│   ├── routers/            # API 路由
│   ├── services/           # 业务逻辑
│   └── requirements.txt    # Python 依赖
├── web/                    # React 前端
│   ├── src/
│   │   ├── components/     # UI 组件
│   │   ├── pages/          # 页面
│   │   └── ...
│   └── package.json
└── reports/                # 保存的报告（JSON）
```

## 快速开始

### 1. 安装后端依赖

```bash
cd api
pip install -r requirements.txt
```

### 2. 安装前端依赖

```bash
cd web
npm install
```

### 3. 启动开发服务器

**后端**（终端 1）：
```bash
cd api
uvicorn main:app --reload --port 8000
```

**前端**（终端 2）：
```bash
cd web
npm run dev
```

访问 http://localhost:5173 即可使用。

## 功能特性

- **股票搜索**：输入代码或名称快速搜索
- **深度分析**：调用分析引擎，实时显示进度
- **报告管理**：保存分析结果，生成分享链接
- **批量扫描**：选择市场范围，筛选高分股票

## 技术栈

- **后端**：FastAPI + Python
- **前端**：Vite + React 18 + TypeScript
- **UI**：shadcn/ui + Tailwind CSS
- **图表**：ECharts（待实现）
- **状态**：Zustand + TanStack Query

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/health | 健康检查 |
| GET | /api/stocks/search | 股票搜索 |
| POST | /api/analysis | 创建分析任务 |
| GET | /api/analysis/{task_id}/stream | SSE 进度推送 |
| GET | /api/reports | 报告列表 |
| POST | /api/scanner | 启动扫描 |

## 配置

环境变量可在 `api/.env` 中配置：

```env
TUSHARE_TOKEN=xxx
DOUBAO_API_KEY=xxx
```

## 开发计划

- [x] Phase 1: 项目骨架
- [ ] Phase 2: 核心分析功能
- [ ] Phase 3: 报告管理
- [ ] Phase 4: 批量扫描
- [ ] Phase 5: UI 优化（ECharts 图表）
- [ ] Phase 6: Docker 部署
