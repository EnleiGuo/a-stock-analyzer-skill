import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { TrendingUp, Clock, ArrowRight, Loader2 } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { StockSearch } from '@/components/StockSearch'
import { Progress } from '@/components/ui/progress'
import { getActiveAnalyses, getUnreadCount, markAsRead, getCompletedAnalyses, type AnalysisTask, type CompletedAnalysis } from '@/lib/analysisTracker'
import { Badge } from '@/components/ui/badge'

interface ReportSummary {
  id: string
  ts_code: string
  stock_name: string
  score: number
  created_at: string
}

// 热门股票（示例数据）
const hotStocks = [
  { ts_code: '600519.SH', name: '贵州茅台' },
  { ts_code: '000001.SZ', name: '平安银行' },
  { ts_code: '300750.SZ', name: '宁德时代' },
  { ts_code: '002475.SZ', name: '立讯精密' },
  { ts_code: '601318.SH', name: '中国平安' },
  { ts_code: '000858.SZ', name: '五粮液' },
  { ts_code: '002594.SZ', name: '比亚迪' },
  { ts_code: '600036.SH', name: '招商银行' },
]

export function Home() {
  const navigate = useNavigate()
  const [recentReports, setRecentReports] = useState<ReportSummary[]>([])
  const [activeAnalyses, setActiveAnalyses] = useState<AnalysisTask[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [unreadCount, setUnreadCount] = useState(0)
  const [completedAnalyses, setCompletedAnalyses] = useState<CompletedAnalysis[]>([])

  useEffect(() => {
    fetchRecentReports()
    // 加载进行中的分析任务
    setActiveAnalyses(getActiveAnalyses())
    setUnreadCount(getUnreadCount())
    setCompletedAnalyses(getCompletedAnalyses())
    
    // 监听 storage 变化（其他标签页或同页面更新）
    const handleStorageChange = (e: StorageEvent | Event) => {
      setActiveAnalyses(getActiveAnalyses())
      const newUnread = getUnreadCount()
      setUnreadCount(newUnread)
      setCompletedAnalyses(getCompletedAnalyses())
      // 如果有新完成的分析，刷新报告列表
      if (e instanceof StorageEvent && e.key === 'completed_analyses' && newUnread > 0) {
        fetchRecentReports()
      }
    }
    window.addEventListener('storage', handleStorageChange)
    
    // 定时刷新进行中的任务状态和未读数量
    const interval = setInterval(() => {
      const prevActive = getActiveAnalyses()
      setActiveAnalyses(prevActive)
      const newUnread = getUnreadCount()
      // 如果未读数量增加，说明有新完成的分析
      if (newUnread > unreadCount) {
        fetchRecentReports()
      }
      setUnreadCount(newUnread)
      setCompletedAnalyses(getCompletedAnalyses())
    }, 1000)
    
    return () => {
      window.removeEventListener('storage', handleStorageChange)
      clearInterval(interval)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const fetchRecentReports = async () => {
    try {
      const res = await fetch('/api/reports?limit=6')
      if (res.ok) {
        const data = await res.json()
        setRecentReports(data.reports || [])
      }
    } catch (error) {
      console.error('获取最近报告失败:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleStockSelect = (tsCode: string) => {
    navigate(`/analysis/${tsCode}`)
  }

  const getScoreColor = (score: number) => {
    if (score >= 70) return 'text-red-600'
    if (score >= 50) return 'text-orange-500'
    return 'text-green-600'
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

    if (diffHours < 1) return '刚刚'
    if (diffHours < 24) return `${diffHours}小时前`
    if (diffDays < 7) return `${diffDays}天前`
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
  }

  const isReportUnread = (reportId: string) => {
    const completed = completedAnalyses.find(c => c.reportId === reportId)
    return completed ? !completed.read : false
  }

  return (
    <div className="space-y-6 sm:space-y-8">
      {/* 搜索区域 */}
      <div className="flex flex-col items-center py-8 sm:py-12">
        <h1 className="mb-4 sm:mb-6 text-2xl sm:text-3xl font-bold text-gray-900">
          A股专业深度分析
        </h1>
        <p className="mb-6 sm:mb-8 text-sm sm:text-base text-gray-500 text-center px-4">
          输入股票代码或名称，获取多维度量化分析报告
        </p>
        <div className="w-full max-w-xl">
          <StockSearch onSelect={handleStockSelect} />
        </div>
      </div>

      {/* 最近分析 */}
      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-gray-900">
            <Clock className="h-5 w-5 text-gray-500" />
            最近分析
            {unreadCount > 0 && (
              <Badge variant="destructive" className="ml-1 h-5 min-w-5 px-1.5 text-xs">
                {unreadCount > 9 ? '9+' : unreadCount}
              </Badge>
            )}
          </h2>
          {recentReports.length > 0 && (
            <Link to="/reports">
              <Button variant="ghost" size="sm">
                查看全部 <ArrowRight className="ml-1 h-4 w-4" />
              </Button>
            </Link>
          )}
        </div>
        
        {/* 进行中的分析 */}
        {activeAnalyses.length > 0 && (
          <div className="grid grid-cols-2 gap-2 sm:gap-4 sm:grid-cols-2 lg:grid-cols-3 mb-4">
            {activeAnalyses.map((task) => (
              <Link key={task.tsCode} to={`/analysis/${task.tsCode}`}>
                <Card className="cursor-pointer transition-all border-blue-200 bg-blue-50/50 hover:shadow-md">
                  <CardContent className="p-2.5 sm:p-4">
                    <div className="flex items-start justify-between gap-1">
                      <div className="text-xs text-gray-400">{task.tsCode.split('.')[0]}</div>
                      <div className="text-xs font-bold px-1.5 py-0.5 rounded bg-blue-100 text-blue-600">
                        {task.progress}%
                      </div>
                    </div>
                    <div className="text-sm font-medium truncate mt-0.5">{task.stockName || task.tsCode}</div>
                    <div className="mt-1.5 flex items-center gap-1 text-xs text-blue-600">
                      <Loader2 className="h-3 w-3 animate-spin" />
                      <span className="truncate">{task.message}</span>
                    </div>
                    <Progress value={task.progress} className="mt-1.5 h-1" />
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}

        {isLoading ? (
          <Card>
            <CardContent className="p-6 text-center text-gray-500">
              加载中...
            </CardContent>
          </Card>
        ) : recentReports.length === 0 && activeAnalyses.length === 0 ? (
          <Card>
            <CardContent className="p-6 text-center text-gray-500">
              暂无分析记录，输入股票代码开始分析
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-2 gap-2 sm:gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {recentReports.map((report) => (
              <Link key={report.id} to={`/r/${report.id}`} onClick={() => markAsRead(report.id)}>
                <Card className={`cursor-pointer transition-all hover:shadow-md hover:border-blue-200 ${isReportUnread(report.id) ? 'bg-gray-100' : ''}`}>
                  <CardContent className="p-2.5 sm:p-4">
                    <div className="flex items-start justify-between gap-1">
                      <div className="text-xs text-gray-400">{report.ts_code.split('.')[0]}</div>
                      <div className={`text-xs font-bold px-1.5 py-0.5 rounded ${getScoreColor(report.score)} ${report.score >= 70 ? 'bg-red-50' : report.score >= 50 ? 'bg-orange-50' : 'bg-green-50'}`}>
                        {report.score}
                      </div>
                    </div>
                    <div className="text-sm font-medium truncate mt-0.5">{report.stock_name}</div>
                    <div className="text-xs text-gray-400 mt-1">{formatDate(report.created_at)}</div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* 热门股票 */}
      <section>
        <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-gray-900">
          <TrendingUp className="h-5 w-5 text-red-500" />
          热门股票
        </h2>
        <div className="grid grid-cols-4 gap-2 sm:grid-cols-4 lg:grid-cols-8">
          {hotStocks.map((stock) => (
            <Card
              key={stock.ts_code}
              className="cursor-pointer transition-all hover:shadow-md hover:border-red-200"
              onClick={() => handleStockSelect(stock.ts_code)}
            >
              <CardContent className="p-2 sm:p-3 text-center">
                <div className="text-xs text-gray-400">{stock.ts_code.split('.')[0]}</div>
                <div className="font-medium text-sm truncate">{stock.name}</div>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* 功能入口 */}
      <section className="grid gap-3 sm:gap-4 sm:grid-cols-2">
        <Link to="/scanner">
          <Card className="cursor-pointer transition-all hover:shadow-md hover:border-purple-200 h-full">
            <CardContent className="p-4 sm:p-6">
              <h3 className="font-semibold text-base sm:text-lg mb-1 sm:mb-2">📊 批量扫描</h3>
              <p className="text-xs sm:text-sm text-gray-500">
                扫描沪深300、中证500等指数成分股，筛选高分股票
              </p>
            </CardContent>
          </Card>
        </Link>
        <Link to="/reports">
          <Card className="cursor-pointer transition-all hover:shadow-md hover:border-blue-200 h-full">
            <CardContent className="p-4 sm:p-6">
              <h3 className="font-semibold text-base sm:text-lg mb-1 sm:mb-2">📁 分析报告</h3>
              <p className="text-xs sm:text-sm text-gray-500">
                查看已保存的分析报告，管理和分享你的研究成果
              </p>
            </CardContent>
          </Card>
        </Link>
      </section>
    </div>
  )
}
