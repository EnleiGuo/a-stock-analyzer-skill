import { useEffect, useState, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Share2, Save, TrendingUp, TrendingDown, Minus, Copy, Check, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { KLineChart, MACDChart, RSIChart, KDJChart } from '@/components/charts'
import { AnalysisProgress } from '@/components/AnalysisProgress'
import { DataCard } from '@/components/DataCard'
import type { AnalysisResult } from '@/types/analysis'
import { upsertAnalysis, updateProgress, removeAnalysis, addCompletedAnalysis } from '@/lib/analysisTracker'

export function Analysis() {
  const { tsCode } = useParams<{ tsCode: string }>()
  const [_taskId, setTaskId] = useState<string | null>(null)
  const [progress, setProgress] = useState(0)
  const [progressMessage, setProgressMessage] = useState('准备分析...')
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [shareUrl, setShareUrl] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [reportId, setReportId] = useState<string | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    if (!tsCode) return

    const startAnalysis = async () => {
      try {
        // 创建分析任务
        const res = await fetch('/api/analysis', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ts_code: tsCode }),
        })
        
        if (!res.ok) throw new Error('创建分析任务失败')
        
        const data = await res.json()
        setTaskId(data.task_id)

        // 记录分析任务状态
        upsertAnalysis({
          taskId: data.task_id,
          tsCode: tsCode,
          progress: 0,
          message: '准备分析...',
          startedAt: new Date().toISOString(),
        })

        // SSE 监听进度（使用 addEventListener 处理命名事件）
        const eventSource = new EventSource(`/api/analysis/${data.task_id}/stream`)
        eventSourceRef.current = eventSource
        
        // 进度更新事件
        eventSource.addEventListener('progress', (event: MessageEvent) => {
          try {
            const progressData = JSON.parse(event.data)
            setProgress(progressData.progress)
            setProgressMessage(progressData.step)
            // 更新进度状态
            updateProgress(tsCode, progressData.progress, progressData.step)
          } catch (e) {
            console.error('Failed to parse progress:', e)
          }
        })

        // 完成事件 - 自动保存到报告
        eventSource.addEventListener('complete', async (event: MessageEvent) => {
          try {
            const resultData = JSON.parse(event.data)
            setResult(resultData)
            setProgress(100)
            eventSource.close()
            // 分析完成，移除进行中状态
            removeAnalysis(tsCode)
            
            // 自动保存到报告历史
            try {
              const saveRes = await fetch('/api/reports', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  ts_code: resultData.ts_code,
                  name: resultData.stock_info?.名称 || tsCode,
                  data: resultData
                }),
              })
              if (saveRes.ok) {
                const saveData = await saveRes.json()
                setReportId(saveData.id)
                setShareUrl(`${window.location.origin}/share/${saveData.id}`)
                // 添加到已完成列表（未读）
                addCompletedAnalysis({
                  tsCode: resultData.ts_code,
                  stockName: resultData.stock_info?.名称 || tsCode,
                  reportId: saveData.id,
                  score: resultData.composite?.score || 0,
                })
              }
            } catch (saveErr) {
              console.error('Auto-save failed:', saveErr)
            }
          } catch (e) {
            console.error('Failed to parse complete:', e)
            setError('解析结果失败')
            eventSource.close()
          }
        })

        // 错误事件 (服务端发送的命名 error 事件)
        eventSource.addEventListener('error', (event: MessageEvent) => {
          if (event.data) {
            try {
              const errorData = JSON.parse(event.data)
              setError(errorData.message || '分析失败')
            } catch {
              setError('分析失败')
            }
          }
          eventSource.close()
          // 分析失败，移除进行中状态
          removeAnalysis(tsCode)
        })

        // 连接错误 (onerror 处理连接问题)
        eventSource.onerror = () => {
          // 检查是否正常关闭（已完成或已出错）
          if (!result && !error) {
            setError('连接中断，请刷新重试')
          }
          eventSource.close()
        }

      } catch (err) {
        setError(err instanceof Error ? err.message : '分析失败')
      }
    }

    startAnalysis()

    // 清理函数
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
    }
  }, [tsCode])

  // 手动保存报告（如果自动保存失败）
  const handleSave = async () => {
    if (!result) return
    setSaving(true)
    try {
      const res = await fetch('/api/reports', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ts_code: result.ts_code,
          name: result.stock_info.名称,
          data: result
        }),
      })
      if (!res.ok) throw new Error('保存失败')
      const data = await res.json()
      setReportId(data.id)
      setShareUrl(`${window.location.origin}/share/${data.id}`)
    } catch (err) {
      console.error('Save failed:', err)
    } finally {
      setSaving(false)
    }
  }

  // 复制分享链接
  const handleCopyShare = () => {
    if (shareUrl) {
      navigator.clipboard.writeText(shareUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  // 加载中
  if (!result && !error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Link to="/">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="mr-1 h-4 w-4" />
              返回
            </Button>
          </Link>
        </div>

        <AnalysisProgress 
          progress={progress} 
          message={progressMessage} 
          tsCode={tsCode || ''} 
        />
      </div>
    )
  }

  // 错误
  if (error) {
    return (
      <div className="space-y-6">
        <Link to="/">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="mr-1 h-4 w-4" />
            返回
          </Button>
        </Link>
        <Card className="border-red-200 bg-red-50">
          <CardContent className="py-8 text-center text-red-600">
            {error}
          </CardContent>
        </Card>
      </div>
    )
  }

  // 结果展示
  const { stock_info, composite, prediction, fundamental, technical, capital, chart_data, news } = result!

  const getScoreColor = (score: number) => {
    if (score >= 65) return 'text-red-500'
    if (score >= 40) return 'text-orange-500'
    return 'text-green-500'
  }

  const getDirectionIcon = (direction: string) => {
    if (direction.includes('多') || direction.includes('涨')) {
      return <TrendingUp className="h-5 w-5 text-red-600" />
    }
    if (direction.includes('空') || direction.includes('跌')) {
      return <TrendingDown className="h-5 w-5 text-green-600" />
    }
    return <Minus className="h-5 w-5 text-gray-500" />
  }

  // 基本面子维度配置
  const fundamentalDimensions = [
    { key: 'profitability', title: '盈利能力', icon: '💰' },
    { key: 'growth', title: '成长能力', icon: '📈' },
    { key: 'valuation', title: '估值水平', icon: '🏷️' },
    { key: 'solvency', title: '偿债能力', icon: '🛡️' },
    { key: 'cashflow', title: '现金流质量', icon: '💵' },
    { key: 'efficiency', title: '运营效率', icon: '⚙️' },
    { key: 'forecast', title: '业绩预告', icon: '📢' },
    { key: 'mainbz', title: '主营业务构成', icon: '🏭' },
    { key: 'analyst', title: '券商盈利预测', icon: '🔬' },
    { key: 'balance_detail', title: '资产负债增强', icon: '📑' },
  ]

  // 技术面子维度配置
  // flat=true 表示数据直接是对象，而不是 {score, data} 结构
  const technicalDimensions = [
    { key: 'trend', title: '趋势分析', icon: '📊', flat: true },
    { key: 'momentum', title: '动量指标', icon: '🚀', flat: true },
    { key: 'volume', title: '量能分析', icon: '📶', flat: true },
    { key: 'volatility', title: '波动与支撑阻力', icon: '🌊', flat: true },
    { key: 'chip_data', title: '筹码胜率分布', icon: '🎯', flat: false },
    { key: 'nineturn', title: '神奇九转指标', icon: '🔢', flat: false },
  ]

  // 资金面子维度配置
  const capitalDimensions = [
    { key: 'money_flow', title: '主力资金流向', icon: '💹', flat: false },
    { key: 'margin', title: '融资融券', icon: '📋', flat: false },
    { key: 'holders', title: '股东结构', icon: '👥', flat: false },
    { key: 'block_trade', title: '大宗交易', icon: '🏢', flat: false },
    { key: 'holdertrade', title: '股东增减持', icon: '📊', flat: false },
    { key: 'share_float', title: '限售解禁', icon: '🔓', flat: false },
    { key: 'pledge', title: '股权质押', icon: '⛓️', flat: false },
    { key: 'hk_hold', title: '北向资金', icon: '🌏', flat: false },
    { key: 'survey', title: '机构调研', icon: '🔍', flat: false },
  ]

  // 渲染维度数据卡片
  const renderDimensionCards = (
    dimensions: { key: string; title: string; icon: string; flat?: boolean }[],
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    data: any
  ) => {
    return dimensions
      .filter(dim => {
        const section = data[dim.key]
        if (!section) return false
        // flat 维度：直接是数据对象，只要有内容就显示
        if (dim.flat) return Object.keys(section).length > 0
        // nested 维度：需要有 data 或 score
        return section.data || section.score !== undefined
      })
      .map(dim => {
        const section = data[dim.key]
        // flat 维度：section 本身就是 data，不显示评分
        if (dim.flat) {
          return (
            <DataCard
              key={dim.key}
              title={dim.title}
              icon={dim.icon}
              data={section as Record<string, unknown>}
            />
          )
        }
        // nested 维度：有 score 和 data 子属性
        return (
          <DataCard
            key={dim.key}
            title={dim.title}
            icon={dim.icon}
            score={section.score as number | undefined}
            comment={section.comment as string | undefined}
            data={section.data as Record<string, unknown> | undefined}
          />
        )
      })
  }

  return (
    <div className="space-y-6">
      {/* 头部 */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-2 sm:gap-4">
          <Link to="/">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="mr-1 h-4 w-4" />
              返回
            </Button>
          </Link>
          <div>
            <div className="text-sm text-gray-500">{stock_info.代码}</div>
            <div className="text-xl font-bold">{stock_info.名称}</div>
          </div>
          <Badge variant="outline">{stock_info.行业}</Badge>
          {stock_info.概念?.slice(0, 3).map((c, i) => (
            <Badge key={i} variant="secondary" className="text-xs">{c}</Badge>
          ))}
        </div>
        <div className="flex flex-wrap gap-2">
          {shareUrl ? (
            <Button variant="outline" size="sm" onClick={handleCopyShare}>
              {copied ? <Check className="mr-1 h-4 w-4" /> : <Copy className="mr-1 h-4 w-4" />}
              {copied ? '已复制' : '复制链接'}
            </Button>
          ) : (
            <Button variant="outline" size="sm" onClick={handleSave} disabled={saving}>
              {saving ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <Save className="mr-1 h-4 w-4" />}
              {saving ? '保存中...' : '保存'}
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={() => {
            const url = `${window.location.origin}/analysis/${result!.ts_code}`
            navigator.clipboard.writeText(url)
          }}>
            <Share2 className="mr-1 h-4 w-4" />
            分享
          </Button>
        </div>
      </div>

      {/* 评分概览 - 4列网格 */}
      <div className="grid gap-4 md:grid-cols-4">
        {/* 综合评分 */}
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <div className={`text-5xl font-bold ${getScoreColor(composite.score)}`}>
                {composite.score}
              </div>
              <div className="mt-2 text-lg font-medium">{composite.rating}</div>
              <div className="mt-1 text-sm text-gray-500">综合评分</div>
            </div>
            <div className="mt-4 grid grid-cols-3 gap-2 text-center text-sm">
              <div>
                <div className="text-gray-500">基本面</div>
                <div className={`font-bold ${getScoreColor(composite.fundamental_score)}`}>
                  {composite.fundamental_score}
                </div>
              </div>
              <div>
                <div className="text-gray-500">技术面</div>
                <div className={`font-bold ${getScoreColor(composite.technical_score)}`}>
                  {composite.technical_score}
                </div>
              </div>
              <div>
                <div className="text-gray-500">资金面</div>
                <div className={`font-bold ${getScoreColor(composite.capital_score)}`}>
                  {composite.capital_score}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 预测方向 */}
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="flex items-center justify-center gap-2">
                {getDirectionIcon(prediction.direction)}
                <span className="text-2xl font-bold">{prediction.direction}</span>
              </div>
              <div className="mt-2">
                <Badge variant="outline" className="text-lg px-3 py-1">
                  {prediction.probability_up.toFixed(0)}% 上涨概率
                </Badge>
              </div>
              <div className="mt-3 text-sm text-gray-500">未来一周预测</div>
            </div>
          </CardContent>
        </Card>

        {/* 目标区间 */}
        <Card>
          <CardContent className="pt-6">
            <div className="grid grid-cols-3 gap-2 text-center">
              <div>
                <div className="text-red-500 font-bold text-lg">
                  {prediction.target_high?.toFixed(2) || 'N/A'}
                </div>
                <div className="text-xs text-gray-500">目标上沿</div>
              </div>
              <div>
                <div className="text-blue-500 font-bold text-lg">
                  {prediction.current_price?.toFixed(2) || 'N/A'}
                </div>
                <div className="text-xs text-gray-500">当前价格</div>
              </div>
              <div>
                <div className="text-green-500 font-bold text-lg">
                  {prediction.target_low?.toFixed(2) || 'N/A'}
                </div>
                <div className="text-xs text-gray-500">目标下沿</div>
              </div>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2 text-center text-sm">
              <div className="bg-green-50 rounded p-2">
                <div className="text-green-600 font-medium">{prediction.key_support?.toFixed(2) || 'N/A'}</div>
                <div className="text-xs text-gray-500">关键支撑</div>
              </div>
              <div className="bg-red-50 rounded p-2">
                <div className="text-red-600 font-medium">{prediction.key_resistance?.toFixed(2) || 'N/A'}</div>
                <div className="text-xs text-gray-500">关键阻力</div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 风险指标 */}
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-gray-500">风险等级</span>
                <Badge variant={
                  prediction.risk_level === '高风险' ? 'destructive' :
                  prediction.risk_level === '中等风险' ? 'secondary' : 'outline'
                }>
                  {prediction.risk_level}
                </Badge>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-500">风险收益比</span>
                <span className="font-bold text-blue-600">
                  {prediction.risk_reward ? `1:${prediction.risk_reward.toFixed(2)}` : 'N/A'}
                </span>
              </div>
              {prediction.signal_stats && (
                <>
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-red-500">看多强度</span>
                    <span className="font-medium">{prediction.signal_stats['看多信号强度'] || 0}</span>
                  </div>
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-green-500">看空强度</span>
                    <span className="font-medium">{prediction.signal_stats['看空信号强度'] || 0}</span>
                  </div>
                </>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 催化剂与风险 */}
      {((prediction.catalysts && prediction.catalysts.length > 0) || (prediction.risks && prediction.risks.length > 0)) && (
        <div className="grid gap-4 md:grid-cols-2">
          {prediction.catalysts && prediction.catalysts.length > 0 && (
            <Card className="border-l-4 border-l-red-500">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-red-600">📈 看多催化剂</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-1 text-sm">
                  {prediction.catalysts.map((c, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-red-500">✅</span>
                      <span>{c}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
          {prediction.risks && prediction.risks.length > 0 && (
            <Card className="border-l-4 border-l-green-500">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-green-600">📉 主要风险</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-1 text-sm">
                  {prediction.risks.map((r, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-orange-500">⚠️</span>
                      <span>{r}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* 预测摘要 */}
      {prediction.summary && (
        <Card className="border-l-4 border-l-blue-500 bg-blue-50/50">
          <CardContent className="py-4">
            <p className="text-sm text-gray-700">{prediction.summary}</p>
          </CardContent>
        </Card>
      )}

      {/* K线图表 */}
      {chart_data?.daily && chart_data.daily.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">K线走势</CardTitle>
          </CardHeader>
          <CardContent>
            <KLineChart 
              data={chart_data.daily} 
              maData={{
                ma5: chart_data.ma5,
                ma10: chart_data.ma10,
                ma20: chart_data.ma20,
                ma60: chart_data.ma60
              }}
              height={400}
            />
          </CardContent>
        </Card>
      )}

      {/* 技术指标图表 */}
      {chart_data?.factor && chart_data.factor.length > 0 && (
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">MACD</CardTitle>
            </CardHeader>
            <CardContent className="p-2">
              <MACDChart data={chart_data.factor} height={180} />
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">RSI</CardTitle>
            </CardHeader>
            <CardContent className="p-2">
              <RSIChart data={chart_data.factor} height={180} />
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">KDJ</CardTitle>
            </CardHeader>
            <CardContent className="p-2">
              <KDJChart data={chart_data.factor} height={180} />
            </CardContent>
          </Card>
        </div>
      )}

      {/* 技术信号 */}
      {technical.signals && technical.signals.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">技术信号（共 {technical.signals.length} 个）</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {technical.signals.map(([signal, type], i) => (
                <Badge 
                  key={i} 
                  variant={
                    type.includes('bull') || type.includes('多') ? 'default' :
                    type.includes('bear') || type.includes('空') ? 'destructive' : 'secondary'
                  }
                  className={
                    type.includes('bull') || type.includes('多') ? 'bg-red-500' :
                    type.includes('bear') || type.includes('空') ? 'bg-green-600' : ''
                  }
                >
                  {type.includes('strong') ? '⬆⬆' : type.includes('bull') ? '⬆' : 
                   type === 'weak_bull' ? '↑' : type === 'weak_bear' ? '↓' :
                   type.includes('bear') && type.includes('strong') ? '⬇⬇' : 
                   type.includes('bear') ? '⬇' : '•'} {signal}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 详细分析 Tabs */}
      <Tabs defaultValue="fundamental">
        <TabsList variant="grid" className="grid grid-cols-2 sm:grid-cols-4 h-auto gap-1">
          <TabsTrigger value="fundamental">基本面分析</TabsTrigger>
          <TabsTrigger value="technical">技术面分析</TabsTrigger>
          <TabsTrigger value="capital">资金面分析</TabsTrigger>
          <TabsTrigger value="news">消息面分析</TabsTrigger>
        </TabsList>
        
        <TabsContent value="fundamental">
          <div className="space-y-4">
            {/* Summary */}
            {fundamental.summary && (
              <Card className="border-l-4 border-l-blue-500">
                <CardContent className="py-4">
                  <div 
                    className="prose prose-sm max-w-none text-gray-700"
                    dangerouslySetInnerHTML={{ __html: fundamental.summary }}
                  />
                </CardContent>
              </Card>
            )}
            
            {/* Score overview */}
            <div className="flex items-center justify-between px-4 py-3 bg-gray-50 rounded-lg">
              <span className="text-gray-500 font-medium">基本面综合评分</span>
              <span className={`text-3xl font-bold ${getScoreColor(fundamental.score)}`}>
                {fundamental.score}
              </span>
            </div>

            {/* Sub-dimension cards */}
            <div className="grid gap-4 md:grid-cols-2">
              {renderDimensionCards(fundamentalDimensions, fundamental)}
            </div>
          </div>
        </TabsContent>

        <TabsContent value="technical">
          <div className="space-y-4">
            {/* Summary */}
            {technical.summary && (
              <Card className="border-l-4 border-l-purple-500">
                <CardContent className="py-4">
                  <div 
                    className="prose prose-sm max-w-none text-gray-700"
                    dangerouslySetInnerHTML={{ __html: technical.summary }}
                  />
                </CardContent>
              </Card>
            )}
            
            {/* Score overview */}
            <div className="flex items-center justify-between px-4 py-3 bg-gray-50 rounded-lg">
              <span className="text-gray-500 font-medium">技术面综合评分</span>
              <span className={`text-3xl font-bold ${getScoreColor(technical.score)}`}>
                {technical.score}
              </span>
            </div>

            {/* Divergence signals */}
            {technical.divergence && technical.divergence.length > 0 && (
              <Card className="border-orange-200 bg-orange-50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-orange-600">🔄 背离信号</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {technical.divergence.map((d, i) => (
                      <Badge key={i} variant="outline" className="text-orange-600 border-orange-300">
                        {d.type}: {d.desc}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Sub-dimension cards */}
            <div className="grid gap-4 md:grid-cols-2">
              {renderDimensionCards(technicalDimensions, technical)}
            </div>
          </div>
        </TabsContent>

        <TabsContent value="capital">
          <div className="space-y-4">
            {/* Summary */}
            {capital.summary && (
              <Card className="border-l-4 border-l-amber-500">
                <CardContent className="py-4">
                  <div 
                    className="prose prose-sm max-w-none text-gray-700"
                    dangerouslySetInnerHTML={{ __html: capital.summary }}
                  />
                </CardContent>
              </Card>
            )}
            
            {/* Score overview */}
            <div className="flex items-center justify-between px-4 py-3 bg-gray-50 rounded-lg">
              <span className="text-gray-500 font-medium">资金面综合评分</span>
              <span className={`text-3xl font-bold ${getScoreColor(capital.score)}`}>
                {capital.score}
              </span>
            </div>

            {/* Sub-dimension cards */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {renderDimensionCards(capitalDimensions, capital)}
            </div>
          </div>
        </TabsContent>

        <TabsContent value="news">
          <div className="space-y-4">
            {/* AI Summary or structured analysis */}
            {news?.ai_summary ? (
              <Card className="border-l-4 border-l-indigo-500">
                <CardContent className="py-4">
                  <div 
                    className="prose prose-sm max-w-none text-gray-700"
                    dangerouslySetInnerHTML={{ __html: news.ai_summary }}
                  />
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4 md:grid-cols-3">
                {/* 宏观层 */}
                {news?.macro && (
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm flex items-center justify-between">
                        <span>🌍 宏观层</span>
                        <Badge variant={
                          news.macro.rating?.includes('利好') ? 'default' :
                          news.macro.rating?.includes('利空') ? 'destructive' : 'secondary'
                        } className={news.macro.rating?.includes('利好') ? 'bg-red-500' : news.macro.rating?.includes('利空') ? 'bg-green-600' : ''}>
                          {news.macro.rating || '中性'}
                        </Badge>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      {news.macro.key_events && news.macro.key_events.length > 0 && (
                        <div className="text-xs text-gray-500 mb-2">
                          关键事件: {news.macro.key_events.slice(0, 3).join('、')}
                        </div>
                      )}
                      {news.macro.analysis && (
                        <p className="text-sm text-gray-700">{news.macro.analysis}</p>
                      )}
                    </CardContent>
                  </Card>
                )}
                
                {/* 行业层 */}
                {news?.industry && (
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm flex items-center justify-between">
                        <span>🏭 行业层</span>
                        <Badge variant={
                          news.industry.rating?.includes('利好') ? 'default' :
                          news.industry.rating?.includes('利空') ? 'destructive' : 'secondary'
                        } className={news.industry.rating?.includes('利好') ? 'bg-red-500' : news.industry.rating?.includes('利空') ? 'bg-green-600' : ''}>
                          {news.industry.rating || '中性'}
                        </Badge>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      {news.industry.key_events && news.industry.key_events.length > 0 && (
                        <div className="text-xs text-gray-500 mb-2">
                          关键事件: {news.industry.key_events.slice(0, 3).join('、')}
                        </div>
                      )}
                      {news.industry.analysis && (
                        <p className="text-sm text-gray-700">{news.industry.analysis}</p>
                      )}
                    </CardContent>
                  </Card>
                )}
                
                {/* 公司层 */}
                {news?.company && (
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm flex items-center justify-between">
                        <span>🏢 公司层</span>
                        <Badge variant={
                          news.company.rating?.includes('利好') ? 'default' :
                          news.company.rating?.includes('利空') ? 'destructive' : 'secondary'
                        } className={news.company.rating?.includes('利好') ? 'bg-red-500' : news.company.rating?.includes('利空') ? 'bg-green-600' : ''}>
                          {news.company.rating || '中性'}
                        </Badge>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      {news.company.key_events && news.company.key_events.length > 0 && (
                        <div className="text-xs text-gray-500 mb-2">
                          关键事件: {news.company.key_events.slice(0, 3).join('、')}
                        </div>
                      )}
                      {news.company.analysis && (
                        <p className="text-sm text-gray-700">{news.company.analysis}</p>
                      )}
                    </CardContent>
                  </Card>
                )}
              </div>
            )}

            {/* 公司相关新闻 */}
            {news?.raw_articles?.company && news.raw_articles.company.length > 0 && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">📰 公司相关新闻</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {news.raw_articles.company.slice(0, 5).map((article, i) => (
                      <div key={i} className="flex items-center justify-between text-sm border-b border-gray-100 pb-2 last:border-0">
                        <div className="flex-1">
                          <span className="text-gray-400 mr-2">[{article.source || '未知'}]</span>
                          <span>{article.title}</span>
                        </div>
                        <Badge 
                          variant="outline" 
                          className={
                            article.sentiment === 1 ? 'text-red-500 border-red-300' :
                            article.sentiment === -1 ? 'text-green-500 border-green-300' : 'text-gray-500'
                          }
                        >
                          {article.sentiment === 1 ? '利好' : article.sentiment === -1 ? '利空' : '中性'}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* 散户情绪 */}
            {news?.sentiment && (
              <Card className="border-l-4 border-l-purple-500">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">💬 散户情绪分析</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-4 md:grid-cols-2 mb-4">
                    {/* 东财股吧 */}
                    {news.sentiment.eastmoney_guba && (
                      <div className="p-3 bg-gray-50 rounded-lg">
                        <div className="text-sm font-medium mb-2">东财股吧</div>
                        <div className="grid grid-cols-3 gap-2 text-center text-sm">
                          <div>
                            <div className="text-gray-500">情绪分</div>
                            <div className={`font-bold ${(news.sentiment.eastmoney_guba.sentiment_score || 0) > 0 ? 'text-red-500' : 'text-green-500'}`}>
                              {((news.sentiment.eastmoney_guba.sentiment_score || 0) * 100).toFixed(0)}%
                            </div>
                          </div>
                          <div>
                            <div className="text-gray-500">看多比</div>
                            <div className="font-bold text-red-500">{news.sentiment.eastmoney_guba.bull_ratio || 0}%</div>
                          </div>
                          <div>
                            <div className="text-gray-500">帖子数</div>
                            <div className="font-bold">{news.sentiment.eastmoney_guba.post_count || 0}</div>
                          </div>
                        </div>
                      </div>
                    )}
                    
                    {/* 雪球 */}
                    {news.sentiment.xueqiu && (
                      <div className="p-3 bg-gray-50 rounded-lg">
                        <div className="text-sm font-medium mb-2">雪球</div>
                        <div className="grid grid-cols-3 gap-2 text-center text-sm">
                          <div>
                            <div className="text-gray-500">情绪分</div>
                            <div className={`font-bold ${(news.sentiment.xueqiu.sentiment_score || 0) > 0 ? 'text-red-500' : 'text-green-500'}`}>
                              {((news.sentiment.xueqiu.sentiment_score || 0) * 100).toFixed(0)}%
                            </div>
                          </div>
                          <div>
                            <div className="text-gray-500">看多比</div>
                            <div className="font-bold text-red-500">{news.sentiment.xueqiu.bull_ratio || 0}%</div>
                          </div>
                          <div>
                            <div className="text-gray-500">帖子数</div>
                            <div className="font-bold">{news.sentiment.xueqiu.post_count || 0}</div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                  
                  {news.sentiment.overall_sentiment && (
                    <div className="text-sm text-gray-700 bg-purple-50 p-3 rounded-lg">
                      <strong>综合情绪:</strong> {news.sentiment.overall_sentiment}
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* 综合消息面 */}
            {news?.overall_impact && (
              <div className="text-sm text-gray-700 bg-indigo-50 p-4 rounded-lg border-l-4 border-l-indigo-500">
                <strong>综合消息面:</strong> {news.overall_impact}
              </div>
            )}

            {/* 无数据提示 */}
            {!news && (
              <div className="text-center text-gray-500 py-8">
                暂无消息面数据
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>

      {/* 免责声明 */}
      <Card className="border-yellow-300 bg-yellow-50">
        <CardContent className="py-4">
          <p className="text-sm text-yellow-800">
            <strong>⚠️ 免责声明：</strong>
            本报告由程序自动生成，仅供研究参考，<strong>不构成任何投资建议</strong>。股市有风险，投资需谨慎。
            所有分析基于历史数据与量化模型，过往表现不代表未来收益。预测区间仅为统计估计，实际走势可能因突发事件、
            政策变化、市场情绪等多种不可控因素而显著偏离。请投资者独立判断，自行承担投资风险。
          </p>
        </CardContent>
      </Card>

      {/* Footer */}
      <div className="text-center text-sm text-gray-400 pb-4">
        A股专业深度分析系统 v2.0 · 数据来源：Tushare Pro · 分析日期: {result!.analyze_date}
        {reportId && (
          <span className="ml-2">
            | <Link to="/reports" className="text-blue-500 hover:underline">查看报告历史</Link>
          </span>
        )}
      </div>
    </div>
  )
}
