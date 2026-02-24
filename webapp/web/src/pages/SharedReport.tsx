import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { TrendingUp, TrendingDown, Minus, Home } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

interface ReportData {
  id: string
  title: string
  ts_code: string
  stock_name: string
  created_at: string
  data: {
    stock_info: {
      ts_code: string
      name: string
      industry: string
    }
    composite: {
      score: number
      rating: string
      fundamental_score: number
      technical_score: number
      capital_score: number
    }
    prediction: {
      direction: string
      target_low: number
      target_high: number
      risk_level: string
    }
    fundamental: {
      score: number
      summary?: string
    }
    technical: {
      score: number
      summary?: string
    }
    capital: {
      score: number
      summary?: string
    }
  }
}

export function SharedReport() {
  const { reportId } = useParams<{ reportId: string }>()
  const [report, setReport] = useState<ReportData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (!reportId) return

    fetch(`/api/reports/${reportId}`)
      .then((res) => {
        if (!res.ok) throw new Error('报告不存在')
        return res.json()
      })
      .then((data) => setReport(data))
      .catch((err) => setError(err.message))
      .finally(() => setIsLoading(false))
  }, [reportId])

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="text-gray-500">加载中...</div>
      </div>
    )
  }

  if (error || !report) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50">
        <div className="text-red-500 mb-4">{error || '报告不存在'}</div>
        <Link to="/">
          <Button>
            <Home className="mr-2 h-4 w-4" />
            返回首页
          </Button>
        </Link>
      </div>
    )
  }

  const { data } = report
  const { composite, prediction, fundamental, technical, capital } = data

  const getScoreColor = (score: number) => {
    if (score >= 70) return 'text-red-600'
    if (score >= 50) return 'text-orange-500'
    return 'text-green-600'
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

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="mx-auto max-w-4xl px-4">
        {/* 头部 */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <div className="text-sm text-gray-500">{report.ts_code}</div>
            <h1 className="text-2xl font-bold">{report.title}</h1>
            <div className="mt-1 text-sm text-gray-400">
              {new Date(report.created_at).toLocaleString('zh-CN')}
            </div>
          </div>
          <Link to="/">
            <Button variant="outline" size="sm">
              <Home className="mr-1 h-4 w-4" />
              首页
            </Button>
          </Link>
        </div>

        {/* 评分和预测 */}
        <div className="mb-6 grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">综合评分</CardTitle>
            </CardHeader>
            <CardContent>
              <div className={`text-5xl font-bold ${getScoreColor(composite.score)}`}>
                {composite.score}
              </div>
              <div className="mt-2 text-lg">{composite.rating}</div>
              <div className="mt-4 grid grid-cols-3 gap-4 text-sm">
                <div>
                  <div className="text-gray-500">基本面</div>
                  <div className={`font-medium ${getScoreColor(composite.fundamental_score)}`}>
                    {composite.fundamental_score}
                  </div>
                </div>
                <div>
                  <div className="text-gray-500">技术面</div>
                  <div className={`font-medium ${getScoreColor(composite.technical_score)}`}>
                    {composite.technical_score}
                  </div>
                </div>
                <div>
                  <div className="text-gray-500">资金面</div>
                  <div className={`font-medium ${getScoreColor(composite.capital_score)}`}>
                    {composite.capital_score}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">预测</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                {getDirectionIcon(prediction.direction)}
                <span className="text-2xl font-bold">{prediction.direction}</span>
              </div>
              <div className="mt-4 space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">目标区间</span>
                  <span className="font-medium">
                    {prediction.target_low?.toFixed(2)} - {prediction.target_high?.toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">风险等级</span>
                  <Badge variant={prediction.risk_level === '高风险' ? 'destructive' : 'outline'}>
                    {prediction.risk_level}
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 详细分析 */}
        <Tabs defaultValue="fundamental">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="fundamental">基本面</TabsTrigger>
            <TabsTrigger value="technical">技术面</TabsTrigger>
            <TabsTrigger value="capital">资金面</TabsTrigger>
          </TabsList>

          <TabsContent value="fundamental">
            <Card>
              <CardContent className="pt-6">
                {fundamental.summary ? (
                  <div
                    className="prose prose-sm max-w-none"
                    dangerouslySetInnerHTML={{ __html: fundamental.summary }}
                  />
                ) : (
                  <div className="text-gray-500">暂无详细分析</div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="technical">
            <Card>
              <CardContent className="pt-6">
                {technical.summary ? (
                  <div
                    className="prose prose-sm max-w-none"
                    dangerouslySetInnerHTML={{ __html: technical.summary }}
                  />
                ) : (
                  <div className="text-gray-500">暂无详细分析</div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="capital">
            <Card>
              <CardContent className="pt-6">
                {capital.summary ? (
                  <div
                    className="prose prose-sm max-w-none"
                    dangerouslySetInnerHTML={{ __html: capital.summary }}
                  />
                ) : (
                  <div className="text-gray-500">暂无详细分析</div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* 免责声明 */}
        <div className="mt-8 text-center text-xs text-gray-400">
          本报告仅供学习研究，不构成投资建议。股市有风险，投资需谨慎。
        </div>
      </div>
    </div>
  )
}
