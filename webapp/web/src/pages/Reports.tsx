import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { FileText, Trash2, ExternalLink, Clock } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface ReportSummary {
  id: string
  title: string
  ts_code: string
  stock_name: string
  score: number
  created_at: string
}

export function Reports() {
  const [reports, setReports] = useState<ReportSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    fetchReports()
  }, [])

  const fetchReports = async () => {
    try {
      const res = await fetch('/api/reports')
      if (res.ok) {
        const data = await res.json()
        setReports(data.reports || [])
      }
    } catch (error) {
      console.error('获取报告列表失败:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const deleteReport = async (reportId: string) => {
    if (!confirm('确定要删除这份报告吗？')) return

    try {
      const res = await fetch(`/api/reports/${reportId}`, { method: 'DELETE' })
      if (res.ok) {
        setReports((prev) => prev.filter((r) => r.id !== reportId))
      }
    } catch (error) {
      console.error('删除报告失败:', error)
    }
  }

  // copyShareLink 可以在后续版本中添加到 UI

  const getScoreColor = (score: number) => {
    if (score >= 70) return 'text-red-600'
    if (score >= 50) return 'text-orange-500'
    return 'text-green-600'
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <FileText className="h-6 w-6 text-gray-700" />
        <h1 className="text-xl font-bold">分析报告</h1>
      </div>

      {isLoading ? (
        <Card>
          <CardContent className="py-8 text-center text-gray-500">
            加载中...
          </CardContent>
        </Card>
      ) : reports.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <FileText className="mx-auto mb-4 h-12 w-12 text-gray-300" />
            <p className="text-gray-500">暂无保存的报告</p>
            <Link to="/" className="mt-4 inline-block">
              <Button variant="outline">开始分析</Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {reports.map((report) => (
            <Card key={report.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="text-sm text-gray-500">
                      {report.ts_code.split('.')[0]}
                    </div>
                    <div className="font-medium">{report.stock_name}</div>
                  </div>
                  <div className={cn('text-2xl font-bold', getScoreColor(report.score))}>
                    {report.score}
                  </div>
                </div>

                <div className="mt-4 flex items-center gap-1 text-xs text-gray-400">
                  <Clock className="h-3 w-3" />
                  {formatDate(report.created_at)}
                </div>

                <div className="mt-4 flex gap-2">
                  <Link to={`/r/${report.id}`} className="flex-1">
                    <Button variant="outline" size="sm" className="w-full">
                      <ExternalLink className="mr-1 h-3 w-3" />
                      查看
                    </Button>
                  </Link>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => deleteReport(report.id)}
                    className="text-red-500 hover:bg-red-50 hover:text-red-600"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
