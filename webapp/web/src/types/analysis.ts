/**
 * 分析结果数据类型定义
 */

export interface StockInfo {
  名称: string
  代码: string
  行业: string
  市场: string
  概念: string[]
  上市日期: string
}

export interface CompositeScore {
  score: number
  rating: string
  fundamental_score: number
  technical_score: number
  capital_score: number
  comment: string
}

export interface DimensionScore {
  score: number
  data?: Record<string, unknown>
  comment?: string
  summary?: string
}

export interface FundamentalAnalysis {
  score: number
  profitability: DimensionScore
  growth: DimensionScore
  valuation: DimensionScore
  solvency: DimensionScore
  cashflow: DimensionScore
  efficiency: DimensionScore
  forecast?: DimensionScore
  analyst?: DimensionScore
  mainbz?: DimensionScore
  balance_detail?: DimensionScore
  summary?: string
  comment?: string
}

export interface TechnicalAnalysis {
  score: number
  trend: Record<string, unknown>
  momentum: Record<string, unknown>
  volume: Record<string, unknown>
  volatility: Record<string, unknown>
  signals: [string, string][]
  family_signals?: [string, string, string, number][]
  divergence?: { type: string; desc: string }[]
  chip_data?: Record<string, unknown>
  nineturn?: Record<string, unknown>
  summary?: string
  comment?: string
}

export interface CapitalAnalysis {
  score: number
  money_flow: DimensionScore
  margin: DimensionScore
  holders: DimensionScore
  block_trade: DimensionScore
  holdertrade?: DimensionScore
  share_float?: DimensionScore
  pledge?: DimensionScore
  hk_hold?: DimensionScore
  survey?: DimensionScore
  summary?: string
  comment?: string
}

export interface Prediction {
  direction: string
  probability_up: number
  target_low: number
  target_high: number
  current_price?: number
  key_support?: number
  key_resistance?: number
  risk_level: string
  risk_reward?: number
  signal_stats?: {
    '看多信号强度'?: number
    '看空信号强度'?: number
  }
  summary: string
  catalysts?: string[]
  risks?: string[]
}

export interface ChartDataPoint {
  trade_date: string
  open: number
  high: number
  low: number
  close: number
  vol: number
  amount: number
}

export interface FactorDataPoint {
  trade_date: string
  macd_dif?: number
  macd_dea?: number
  macd?: number
  kdj_k?: number
  kdj_d?: number
  kdj_j?: number
  rsi_6?: number
  rsi_12?: number
  boll_upper?: number
  boll_mid?: number
  boll_lower?: number
}

export interface ChartData {
  daily: ChartDataPoint[]
  factor?: FactorDataPoint[]
  ma5?: number[]
  ma10?: number[]
  ma20?: number[]
  ma60?: number[]
}

export interface NewsLayer {
  rating?: string
  score?: number
  analysis?: string
  key_events?: string[]
}

export interface NewsArticle {
  title: string
  source?: string
  pub_date?: string
  sentiment?: number  // 1=利好, -1=利空, 0=中性
}

export interface SentimentData {
  eastmoney_guba?: {
    sentiment_score?: number
    bull_ratio?: number
    post_count?: number
  }
  xueqiu?: {
    sentiment_score?: number
    bull_ratio?: number
    post_count?: number
  }
  overall_sentiment?: string
}

export interface NewsAnalysis {
  ai_summary?: string
  macro?: NewsLayer
  industry?: NewsLayer
  company?: NewsLayer
  raw_articles?: {
    macro?: NewsArticle[]
    industry?: NewsArticle[]
    company?: NewsArticle[]
  }
  sentiment?: SentimentData
  overall_impact?: string
}

export interface AnalysisResult {
  ts_code: string
  stock_info: StockInfo
  composite: CompositeScore
  fundamental: FundamentalAnalysis
  technical: TechnicalAnalysis
  capital: CapitalAnalysis
  prediction: Prediction
  chart_data: ChartData
  news?: NewsAnalysis
  analyze_date: string
}
