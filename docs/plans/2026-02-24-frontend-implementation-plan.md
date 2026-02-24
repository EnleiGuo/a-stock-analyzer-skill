# A股深度分析系统 - 前端 Web 应用实施计划

> 基于设计文档: 2026-02-24-frontend-web-app-design.md
> 创建日期: 2026-02-24

## 实施阶段概览

| 阶段 | 内容 | 预估时间 | 交付物 |
|------|------|----------|--------|
| Phase 1 | 项目初始化 + 基础架构 | 1-2 天 | 可运行的前后端骨架 |
| Phase 2 | 核心分析功能 | 2-3 天 | 单股分析完整流程 |
| Phase 3 | 报告管理 | 1-2 天 | 保存/分享/历史报告 |
| Phase 4 | 批量扫描 | 2-3 天 | 扫描任务完整流程 |
| Phase 5 | UI 优化 | 1-2 天 | 图表/响应式/主题 |
| Phase 6 | 部署 | 1 天 | Docker 部署方案 |

---

## Phase 1: 项目初始化 + 基础架构

### 1.1 后端 API 骨架

**目录结构：**
```
api/
├── main.py               # FastAPI 入口
├── config.py             # 配置管理
├── requirements.txt      # Python 依赖
├── routers/
│   └── __init__.py
├── services/
│   └── __init__.py
└── models/
    └── __init__.py
```

**任务清单：**
- [ ] 创建 api/ 目录结构
- [ ] 编写 main.py（FastAPI 入口 + CORS 配置）
- [ ] 编写 config.py（环境变量读取）
- [ ] 创建 requirements.txt
- [ ] 添加健康检查端点 GET /api/health
- [ ] 测试 uvicorn 启动

### 1.2 前端项目初始化

**目录结构：**
```
web/
├── src/
│   ├── App.tsx
│   ├── main.tsx
│   ├── components/
│   │   └── ui/           # shadcn/ui 组件
│   ├── pages/
│   │   └── Home.tsx
│   ├── hooks/
│   ├── services/
│   │   └── api.ts        # API 客户端
│   └── stores/
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── tsconfig.json
```

**任务清单：**
- [ ] 使用 `pnpm create vite web --template react-ts` 初始化
- [ ] 安装核心依赖（react-router-dom, @tanstack/react-query, zustand）
- [ ] 配置 Tailwind CSS
- [ ] 初始化 shadcn/ui（Button, Input, Card 等基础组件）
- [ ] 配置 Vite 代理到后端 :8000
- [ ] 创建基础路由结构
- [ ] 创建 API 客户端（fetch wrapper）
- [ ] 测试前后端联通

### 1.3 验收标准

- [ ] 后端 `uvicorn main:app --reload` 可启动
- [ ] 前端 `pnpm dev` 可启动
- [ ] 前端可成功调用后端 /api/health
- [ ] 首页显示基础 UI（Logo + 搜索框骨架）

---

## Phase 2: 核心分析功能

### 2.1 股票搜索 API

**文件：** `api/routers/stocks.py`

**任务清单：**
- [ ] 实现 GET /api/stocks/search?q={query}
  - 调用 Tushare stock_basic 接口
  - 支持代码和名称模糊匹配
  - 返回 [{ts_code, name, industry}]
- [ ] 实现 GET /api/stocks/{ts_code}
  - 返回股票基本信息

### 2.2 分析任务 API

**文件：** `api/routers/analysis.py`, `api/services/analyzer.py`

**任务清单：**
- [ ] 实现 POST /api/analysis
  - 接收 {ts_code, options}
  - 返回 {task_id, status: "processing"}
- [ ] 实现 GET /api/analysis/{task_id}
  - 返回任务状态和结果
- [ ] 实现 GET /api/analysis/{task_id}/stream (SSE)
  - 实时推送分析进度
  - 事件格式: {event: "progress", data: {step, progress}}
- [ ] 封装 analyzer.py service
  - 调用现有 scripts/stock_analyzer.py
  - 包装为异步 generator（yield 进度事件）

### 2.3 前端搜索组件

**文件：** `web/src/components/StockSearch.tsx`

**任务清单：**
- [ ] 搜索输入框（debounce 300ms）
- [ ] 下拉候选列表
- [ ] 选中后跳转到分析页
- [ ] 支持键盘导航（上下选择，回车确认）

### 2.4 前端分析结果页

**文件：** `web/src/pages/Analysis.tsx`

**任务清单：**
- [ ] 路由 /analysis/:ts_code
- [ ] 进度条组件（SSE 驱动）
- [ ] 综合评分卡片（星级 + 分数）
- [ ] 预测面板（方向、目标区间、风险等级）
- [ ] Tab 切换（基本面/技术面/资金面）
- [ ] 各维度详情卡片

### 2.5 验收标准

- [ ] 输入股票代码可搜索并选择
- [ ] 点击分析后显示实时进度
- [ ] 分析完成后展示完整结果
- [ ] 页面刷新后可重新加载结果

---

## Phase 3: 报告管理

### 3.1 报告存储 Service

**文件：** `api/services/report_store.py`

**任务清单：**
- [ ] save_report(analysis_data, title) → report_id
- [ ] get_report(report_id) → report_data | None
- [ ] list_reports() → [report_summary]
- [ ] delete_report(report_id) → bool
- [ ] 使用 nanoid 生成短 ID

### 3.2 报告 API

**文件：** `api/routers/reports.py`

**任务清单：**
- [ ] POST /api/reports - 保存报告
- [ ] GET /api/reports - 列出报告
- [ ] GET /api/reports/{report_id} - 获取报告
- [ ] DELETE /api/reports/{report_id} - 删除报告

### 3.3 前端报告功能

**任务清单：**
- [ ] 分析结果页添加「保存报告」按钮
- [ ] 分析结果页添加「分享链接」按钮（复制 URL）
- [ ] 创建 /reports 页面（报告列表）
- [ ] 创建 /r/:report_id 页面（分享报告视图）

### 3.4 验收标准

- [ ] 可保存分析结果为报告
- [ ] 可通过 /r/xxx 链接访问报告
- [ ] 可查看历史报告列表
- [ ] 可删除报告

---

## Phase 4: 批量扫描

### 4.1 扫描任务 Service

**文件：** `api/services/scanner.py`, `api/tasks/scanner.py`

**任务清单：**
- [ ] 扫描任务队列（内存实现）
- [ ] 后台任务执行（asyncio）
- [ ] 任务状态管理（queued/running/completed/failed）
- [ ] 封装现有 scan_hs300.py 逻辑

### 4.2 扫描 API

**文件：** `api/routers/scanner.py`

**任务清单：**
- [ ] POST /api/scanner - 启动扫描
  - 接收 {market, threshold}
  - 返回 {scan_id, status}
- [ ] GET /api/scanner/{scan_id} - 查询状态
- [ ] GET /api/scanner/{scan_id}/stream - SSE 进度
- [ ] GET /api/scanner/{scan_id}/results - 获取结果

### 4.3 前端扫描页面

**文件：** `web/src/pages/Scanner.tsx`

**任务清单：**
- [ ] 市场范围选择（Radio Group）
- [ ] 评分阈值输入
- [ ] 开始扫描按钮
- [ ] 扫描进度条（SSE 驱动）
- [ ] 结果表格（排序、分页）
- [ ] 点击行跳转到分析详情

### 4.4 验收标准

- [ ] 可选择市场范围启动扫描
- [ ] 扫描过程显示实时进度
- [ ] 完成后显示符合条件的股票列表
- [ ] 可点击查看单股详情

---

## Phase 5: UI 优化

### 5.1 ECharts 图表

**文件：** `web/src/components/charts/`

**任务清单：**
- [ ] K 线图组件（价格 + 均线）
- [ ] 成交量图组件
- [ ] MACD 指标图
- [ ] RSI 指标图
- [ ] KDJ 指标图
- [ ] 图表联动（缩放、十字光标）

### 5.2 响应式布局

**任务清单：**
- [ ] 移动端适配（单列布局）
- [ ] 平板适配
- [ ] 图表响应式调整

### 5.3 主题与样式

**任务清单：**
- [ ] 深色/浅色主题切换
- [ ] A 股配色（红涨绿跌）
- [ ] 加载骨架屏
- [ ] 错误状态处理

### 5.4 验收标准

- [ ] 图表正确显示技术指标
- [ ] 移动端可正常使用
- [ ] 支持主题切换
- [ ] 无明显 UI 问题

---

## Phase 6: 部署

### 6.1 Docker 配置

**任务清单：**
- [ ] 创建 api/Dockerfile
- [ ] 创建 web/Dockerfile
- [ ] 创建 docker-compose.yml
- [ ] 配置 Nginx 反向代理（可选）
- [ ] 环境变量配置

### 6.2 生产优化

**任务清单：**
- [ ] 前端生产构建优化
- [ ] 后端 Gunicorn/Uvicorn workers
- [ ] 健康检查配置
- [ ] 日志配置

### 6.3 验收标准

- [ ] `docker-compose up` 可启动完整服务
- [ ] 生产环境可正常访问
- [ ] 性能满足基本需求

---

## 实施顺序建议

```
Phase 1 (Day 1-2)
    ├── 后端骨架
    └── 前端初始化
           ↓
Phase 2 (Day 3-5)
    ├── 股票搜索
    ├── 分析 API + SSE
    └── 分析结果页
           ↓
Phase 3 (Day 6-7)
    ├── 报告存储
    └── 分享功能
           ↓
Phase 4 (Day 8-10)
    ├── 扫描后台任务
    └── 扫描页面
           ↓
Phase 5 (Day 11-12)
    ├── ECharts 图表
    └── UI 优化
           ↓
Phase 6 (Day 13)
    └── Docker 部署
```

---

## 风险与依赖

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Tushare API 限流 | 扫描变慢 | 添加重试逻辑，降低并发 |
| SSE 兼容性 | 部分浏览器问题 | 降级为轮询 |
| 大批量扫描内存占用 | 服务崩溃 | 分批处理，限制并发数 |
| AI 摘要生成慢 | 分析时间过长 | 提供跳过 AI 选项 |

---

## 启动命令

```bash
# 开发环境
cd api && pip install -r requirements.txt && uvicorn main:app --reload --port 8000
cd web && pnpm install && pnpm dev

# 生产环境
docker-compose up -d
```

---

**文档状态**: 准备开始实施
