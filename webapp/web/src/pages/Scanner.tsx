import { useState } from 'react'
import { ScanLine, Play, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

const MARKET_OPTIONS = [
  { value: 'hs300', label: '沪深300', description: '沪深两市市值最大的300只' },
  { value: 'zz500', label: '中证500', description: '排除沪深300后的500只中盘股' },
  { value: 'sz50', label: '上证50', description: '上交所规模最大的50只' },
  { value: 'gem', label: '创业板', description: '深交所创业板（300开头）' },
  { value: 'star', label: '科创板', description: '上交所科创板（688开头）' },
  { value: 'all', label: '全部A股', description: '沪深京三市全部股票' },
]

interface ScanResult {
  rank: number
  ts_code: string
  name: string
  composite_score: number
  fundamental_score: number
  technical_score: number
  capital_score: number
  direction: string
  risk_level: string
}

export function Scanner() {
  const [market, setMarket] = useState('hs300')
  const [threshold, setThreshold] = useState(80)
  const [isScanning, setIsScanning] = useState(false)
  const [progress, setProgress] = useState({ completed: 0, total: 0, percent: 0 })
  const [results, setResults] = useState<ScanResult[]>([])

  const startScan = async () => {
    setIsScanning(true)
    setResults([])
    setProgress({ completed: 0, total: 0, percent: 0 })

    try {
      const res = await fetch('/api/scanner', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ market, threshold }),
      })

      if (!res.ok) throw new Error('启动扫描失败')

      const data = await res.json()
      const scanId = data.scan_id

      // SSE 监听进度
      const eventSource = new EventSource(`/api/scanner/${scanId}/stream`)

      eventSource.onmessage = (event) => {
        const eventData = JSON.parse(event.data)

        if (eventData.event === 'progress') {
          setProgress({
            completed: eventData.data.completed,
            total: eventData.data.total,
            percent: eventData.data.progress,
          })
        } else if (eventData.event === 'complete') {
          setResults(eventData.data.results || [])
          setIsScanning(false)
          eventSource.close()
        } else if (eventData.event === 'error') {
          setIsScanning(false)
          eventSource.close()
        }
      }

      eventSource.onerror = () => {
        setIsScanning(false)
        eventSource.close()
      }
    } catch (error) {
      setIsScanning(false)
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 70) return 'text-red-600'
    if (score >= 50) return 'text-orange-500'
    return 'text-green-600'
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <ScanLine className="h-6 w-6 text-gray-700" />
        <h1 className="text-xl font-bold">股票扫描器</h1>
      </div>

      {/* 配置区 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">扫描配置</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="mb-2 block text-sm font-medium">选择市场范围</label>
            <div className="grid grid-cols-2 gap-2 md:grid-cols-3 lg:grid-cols-6">
              {MARKET_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  onClick={() => setMarket(option.value)}
                  disabled={isScanning}
                  className={cn(
                    'rounded-lg border p-3 text-left transition-colors',
                    market === option.value
                      ? 'border-red-500 bg-red-50'
                      : 'border-gray-200 hover:border-gray-300'
                  )}
                >
                  <div className="font-medium">{option.label}</div>
                  <div className="text-xs text-gray-500">{option.description}</div>
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium">综合评分阈值</label>
              <div className="flex items-center gap-2">
                <Input
                  type="number"
                  value={threshold}
                  onChange={(e) => setThreshold(Number(e.target.value))}
                  min={0}
                  max={100}
                  className="w-20"
                  disabled={isScanning}
                />
                <span className="text-gray-500">分</span>
              </div>
            </div>

            <Button
              onClick={startScan}
              disabled={isScanning}
              className="mt-6 bg-red-600 hover:bg-red-700"
            >
              {isScanning ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  扫描中...
                </>
              ) : (
                <>
                  <Play className="mr-2 h-4 w-4" />
                  开始扫描
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 进度 */}
      {isScanning && (
        <Card>
          <CardContent className="py-6">
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>扫描进度</span>
                <span>
                  {progress.completed} / {progress.total} ({progress.percent.toFixed(1)}%)
                </span>
              </div>
              <Progress value={progress.percent} className="h-2" />
            </div>
          </CardContent>
        </Card>
      )}

      {/* 结果 */}
      {results.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              扫描结果（共 {results.length} 只符合条件）
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left">
                    <th className="pb-2">排名</th>
                    <th className="pb-2">代码</th>
                    <th className="pb-2">名称</th>
                    <th className="pb-2">综合评分</th>
                    <th className="pb-2">基本面</th>
                    <th className="pb-2">技术面</th>
                    <th className="pb-2">资金面</th>
                    <th className="pb-2">预测方向</th>
                    <th className="pb-2">风险等级</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((stock) => (
                    <tr key={stock.ts_code} className="border-b hover:bg-gray-50">
                      <td className="py-2">{stock.rank}</td>
                      <td className="py-2 font-mono">{stock.ts_code.split('.')[0]}</td>
                      <td className="py-2 font-medium">{stock.name}</td>
                      <td className={cn('py-2 font-bold', getScoreColor(stock.composite_score))}>
                        {stock.composite_score}
                      </td>
                      <td className={cn('py-2', getScoreColor(stock.fundamental_score))}>
                        {stock.fundamental_score}
                      </td>
                      <td className={cn('py-2', getScoreColor(stock.technical_score))}>
                        {stock.technical_score}
                      </td>
                      <td className={cn('py-2', getScoreColor(stock.capital_score))}>
                        {stock.capital_score}
                      </td>
                      <td className="py-2">
                        <Badge variant={stock.direction.includes('多') ? 'default' : 'secondary'}>
                          {stock.direction}
                        </Badge>
                      </td>
                      <td className="py-2">
                        <Badge
                          variant={
                            stock.risk_level === '高风险'
                              ? 'destructive'
                              : stock.risk_level === '中等风险'
                              ? 'secondary'
                              : 'outline'
                          }
                        >
                          {stock.risk_level}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
