# 沪深300高分股扫描器设计

**日期**: 2026-02-23  
**状态**: 已批准  
**目标**: 创建独立脚本扫描沪深300成分股，筛选综合评分≥80的股票，不使用AI摘要和消息面分析。

---

## 1. 整体架构

```
scan_hs300.py
     │
     ├── 1. 获取沪深300成分股列表 (index_weight API)
     │
     ├── 2. 循环扫描 (tqdm 进度条)
     │   └── 对每只股票:
     │       ├── 调用现有数据采集函数
     │       ├── 调用三维分析函数 (fundamental/technical/capital)
     │       ├── 调用 compute_composite() 计算综合评分
     │       └── 跳过 analyze_news() 和 AI 摘要
     │
     ├── 3. 筛选 score ≥ threshold 的股票
     │
     └── 4. 输出
         ├── 终端表格 (tabulate)
         ├── CSV 文件
         └── JSON 文件
```

**文件位置**: `scripts/scan_hs300.py`

**依赖**:
- `tqdm` — 进度条
- `tabulate` — 终端表格美化
- 从 `stock_analyzer.py` import 核心函数

---

## 2. 核心函数复用

### 从 stock_analyzer.py import

| 函数 | 用途 |
|------|------|
| `fetch_stock_basic()` | 获取股票基本信息（名称、行业） |
| `fetch_daily_data()` | 日线行情 |
| `fetch_daily_basic()` | 每日指标（PE/PB 等） |
| `fetch_technical_factors()` | 技术因子（MACD/KDJ/RSI） |
| `fetch_financial_indicator()` | 财务指标（ROE/ROA） |
| `fetch_income()` | 利润表 |
| `fetch_moneyflow()` | 资金流向 |
| `fetch_margin()` | 融资融券 |
| `fetch_holders()` | 股东数据 |
| `analyze_fundamental()` | 基本面分析 → 评分 |
| `analyze_technical()` | 技术面分析 → 评分 |
| `analyze_capital()` | 资金面分析 → 评分 |
| `compute_composite()` | 综合评分计算 |
| `build_prediction()` | 预测方向/目标区间 |

### 跳过的函数

- `analyze_news()` — 消息面采集
- `call_doubao_*()` — AI 摘要
- `fetch_sentiment_*()` — 股吧/雪球情绪

### 新增函数

```python
def fetch_hs300_constituents() -> list[str]:
    """获取沪深300最新成分股代码列表"""
    
def analyze_single_stock(ts_code: str) -> dict | None:
    """分析单只股票，返回评分结果，失败返回 None"""
    
def format_results(results: list[dict]) -> tuple[str, str, str]:
    """格式化输出：返回 (终端表格, CSV内容, JSON内容)"""
```

---

## 3. 输出格式

### 终端表格

```
================================================================================
  沪深300扫描结果 — 综合评分 ≥ 80  |  扫描时间: 2026-02-23 15:30
  扫描股票: 300 只  |  符合条件: 12 只  |  耗时: 18分32秒
================================================================================

排名  代码        名称        综合评分  基本面  技术面  资金面  预测方向    目标区间         风险等级
----  ----------  ----------  --------  ------  ------  ------  ----------  ---------------  --------
1     600519.SH   贵州茅台    85.2      88      82      84      偏多        1750-1850        低风险
2     000858.SZ   五粮液      83.7      85      80      86      偏多震荡    145-158          中等风险
...
```

### CSV 文件

```csv
排名,代码,名称,综合评分,基本面,技术面,资金面,预测方向,目标价低,目标价高,风险等级
1,600519.SH,贵州茅台,85.2,88,82,84,偏多,1750,1850,低风险
```

### JSON 文件

```json
{
  "scan_time": "2026-02-23 15:30:00",
  "threshold": 80,
  "total_scanned": 300,
  "total_matched": 12,
  "duration_seconds": 1112,
  "results": [
    {
      "rank": 1,
      "ts_code": "600519.SH",
      "name": "贵州茅台",
      "composite_score": 85.2,
      "fundamental_score": 88,
      "technical_score": 82,
      "capital_score": 84,
      "prediction": {
        "direction": "偏多",
        "target_low": 1750,
        "target_high": 1850,
        "risk_level": "低风险"
      }
    }
  ]
}
```

---

## 4. 进度显示与错误处理

### 进度条

```
沪深300扫描中 |████████████░░░░░░░░| 156/300 [08:42<10:15, 3.2s/股] 当前: 000858.SZ 五粮液
```

### 错误处理策略

| 错误类型 | 处理方式 |
|----------|----------|
| API 超时 | 重试 2 次，间隔 3 秒，仍失败则跳过 |
| 数据缺失 | 记录警告，跳过该股票 |
| 网络异常 | 重试 2 次，仍失败则跳过 |
| API 限流 | 等待 5 秒后重试 |

### 跳过日志

```
⚠️  跳过 3 只股票（数据异常）:
    - 000001.SZ: API超时
    - 600000.SH: 财务数据缺失
    - 002415.SZ: 技术因子为空
```

### 中断保护

- 每分析完 10 只股票，自动保存中间结果到 `_hs300_partial.json`
- 脚本意外中断时，已分析的数据不丢失
- 正常完成后删除中间文件

---

## 5. 命令行参数

```bash
python scripts/scan_hs300.py [选项]
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--output` | 输出目录 | `./scan_results` |
| `--threshold` | 最低综合评分 | `80` |
| `--limit` | 最多扫描股票数（调试用） | `0`（全部） |
| `--no-save` | 不保存文件，仅终端显示 | `False` |

### 使用示例

```bash
# 标准扫描
python scripts/scan_hs300.py

# 自定义阈值和目录
python scripts/scan_hs300.py --threshold 75 --output ./my_results

# 调试模式：只扫前10只
python scripts/scan_hs300.py --limit 10

# 仅终端预览
python scripts/scan_hs300.py --no-save
```

### 输出文件命名

```
scan_results/
├── hs300_scan_20260223_153000.csv
├── hs300_scan_20260223_153000.json
└── (扫描中) _hs300_partial.json
```

---

## 6. 技术细节

### 沪深300成分股获取

```python
# Tushare API: index_weight
# index_code: 399300.SZ (沪深300)
# 取当月最新数据
```

### 预计性能

- 每只股票分析耗时: 3-4 秒
- 300只股票总耗时: 15-20 分钟
- API 调用次数: 约 10 次/股票 × 300 = 3000 次

### 依赖安装

```bash
pip install tqdm tabulate
```
