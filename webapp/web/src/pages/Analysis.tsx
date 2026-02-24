import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Share2, Save, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

interface AnalysisResult {
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
    probability: number
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

export function Analysis() {
  const { tsCode } = useParams<{ tsCode: string }>()
  const [_taskId, setTaskId] = useState<string | null>(null)
  const [progress, setProgress] = useState(0)
  const [progressMessage, setProgressMessage] = useState('准备分析...')
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [error, setError] = useState<string | null>(null)

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

        // SSE 监听进度
        const eventSource = new EventSource(`/api/analysis/${data.task_id}/stream`)
        
        eventSource.onmessage = (event) => {
          const eventData = JSON.parse(event.data)
          
          if (eventData.event === 'progress') {
            setProgress(eventData.data.progress)
            setProgressMessage(eventData.data.step)
          } else if (eventData.event === 'complete') {
            setResult(eventData.data)
            setProgress(100)
            eventSource.close()
          } else if (eventData.event === 'error') {
            setError(eventData.data.message)
            eventSource.close()
          }
        }

        eventSource.onerror = () => {
          setError('连接中断，请刷新重试')
          eventSource.close()
        }

      } catch (err) {
        setError(err instanceof Error ? err.message : '分析失败')
      }
    }

    startAnalysis()
  }, [tsCode])

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
          <div className="text-lg font-medium">正在分析 {tsCode}...</div>
        </div>

        <Card>
          <CardContent className="py-12">
            <div className="mx-auto max-w-md space-y-4">
              <Progress value={progress} className="h-2" />
              <div className="text-center text-sm text-gray-500">
                {progressMessage} ({progress}%)
              </div>
            </div>
          </CardContent>
        </Card>
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
  const { stock_info, composite, prediction, fundamental, technical, capital } = result!

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
    <div className="space-y-6">
      {/* 头部 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link to="/">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="mr-1 h-4 w-4" />
              返回
            </Button>
          </Link>
          <div>
            <div className="text-sm text-gray-500">{stock_info.ts_code}</div>
            <div className="text-xl font-bold">{stock_info.name}</div>
          </div>
          <Badge variant="outline">{stock_info.industry}</Badge>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm">
            <Save className="mr-1 h-4 w-4" />
            保存
          </Button>
          <Button variant="outline" size="sm">
            <Share2 className="mr-1 h-4 w-4" />
            分享
          </Button>
        </div>
      </div>

      {/* 评分和预测 */}
      <div className="grid gap-4 md:grid-cols-2">
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
            <CardTitle className="text-base">未来一周预测</CardTitle>
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
                <Badge variant={
                  prediction.risk_level === '高风险' ? 'destructive' :
                  prediction.risk_level === '中等风险' ? 'secondary' : 'outline'
                }>
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
          <TabsTrigger value="fundamental">基本面分析</TabsTrigger>
          <TabsTrigger value="technical">技术面分析</TabsTrigger>
          <TabsTrigger value="capital">资金面分析</TabsTrigger>
        </TabsList>
        
        <TabsContent value="fundamental">
          <Card>
            <CardContent className="pt-6">
              <div className="mb-4 flex items-center justify-between">
                <span className="text-gray-500">基本面评分</span>
                <span className={`text-2xl font-bold ${getScoreColor(fundamental.score)}`}>
                  {fundamental.score}
                </span>
              </div>
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
              <div className="mb-4 flex items-center justify-between">
                <span className="text-gray-500">技术面评分</span>
                <span className={`text-2xl font-bold ${getScoreColor(technical.score)}`}>
                  {technical.score}
                </span>
              </div>
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
              <div className="mb-4 flex items-center justify-between">
                <span className="text-gray-500">资金面评分</span>
                <span className={`text-2xl font-bold ${getScoreColor(capital.score)}`}>
                  {capital.score}
                </span>
              </div>
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
    </div>
  )
}
