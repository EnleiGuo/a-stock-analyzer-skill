# A股深度分析系统 - Web 应用

基于 FastAPI + React 的 Web 前端界面，提供股票查询、分析、报告保存/分享、批量扫描等功能。

## 快速启动

```bash
# 一键启动（自动安装依赖）
./start.sh

# 或指定命令
./start.sh start     # 启动服务
./start.sh stop      # 停止服务
./start.sh restart   # 重启服务
./start.sh status    # 查看状态
./start.sh logs      # 查看日志
```

启动后访问:
- **前端**: http://localhost:4661
- **后端**: http://localhost:4662

## 项目结构

```
webapp/
├── start.sh                # 一键启动脚本
├── api/                    # FastAPI 后端
│   ├── main.py             # 入口
│   ├── config.py           # 配置
│   ├── routers/            # API 路由
│   ├── services/           # 业务逻辑
│   └── requirements.txt    # Python 依赖
├── web/                    # React 前端
│   ├── src/
│   │   ├── components/     # UI 组件
│   │   │   ├── charts/     # ECharts 图表组件
│   │   │   └── ui/         # shadcn/ui 组件
│   │   ├── pages/          # 页面
│   │   └── types/          # TypeScript 类型
│   └── package.json
├── reports/                # 保存的报告（JSON）
└── logs/                   # 运行日志
```

## 手动启动

如果不使用启动脚本，可以手动启动：

### 1. 安装依赖

```bash
# 后端
cd api
pip install -r requirements.txt

# 前端
cd web
npm install
```

### 2. 启动服务

**后端**（终端 1）：
```bash
cd api
uvicorn main:app --reload --port 4662
```

**前端**（终端 2）：
```bash
cd web
npm run dev
```

## 功能特性

- **股票搜索**：输入代码或名称快速搜索
- **深度分析**：调用分析引擎，实时 SSE 进度推送
- **K线图表**：ECharts K线 + 均线 + MACD/RSI/KDJ 指标
- **报告管理**：保存、分享、批量删除、导出 JSON
- **批量扫描**：选择市场范围，筛选高分股票，导出 CSV

## 技术栈

- **后端**：FastAPI + Python 3.10+
- **前端**：Vite + React 18 + TypeScript
- **UI**：shadcn/ui + Tailwind CSS v4
- **图表**：ECharts + echarts-for-react
- **状态**：Zustand + TanStack Query

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/health | 健康检查 |
| GET | /api/stocks/search | 股票搜索 |
| POST | /api/analysis | 创建分析任务 |
| GET | /api/analysis/{task_id}/stream | SSE 进度推送 |
| GET | /api/reports | 报告列表 |
| POST | /api/reports | 保存报告 |
| POST | /api/reports/batch-delete | 批量删除 |
| DELETE | /api/reports/{id} | 删除报告 |
| POST | /api/scanner | 启动扫描 |

## 配置

环境变量可在 `api/.env` 中配置：

```env
TUSHARE_TOKEN=xxx
DOUBAO_API_KEY=xxx
```

## 开发进度

- [x] Phase 1: 项目骨架
- [x] Phase 2: 核心分析功能 + ECharts 图表
- [x] Phase 3: 报告管理（批量操作、导出）
- [x] Phase 4: 批量扫描（排序、导出 CSV）
- [x] Phase 5: UI 优化（进度动画、响应式）
- [ ] Phase 6: Docker 部署
