import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { 
  FileText, Trash2, ExternalLink, Clock, Download, Copy, Check,
  CheckSquare, Square, MoreHorizontal, Search
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { cn } from '@/lib/utils'

interface ReportSummary {
  id: string
  title: string
  ts_code: string
  stock_name: string
  score: number
  created_at: string
}

type SortOption = 'date_desc' | 'date_asc' | 'score_desc' | 'score_asc' | 'name_asc'

export function Reports() {
  const [reports, setReports] = useState<ReportSummary[]>([])
  const [filteredReports, setFilteredReports] = useState<ReportSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState<SortOption>('date_desc')
  const [copiedId, setCopiedId] = useState<string | null>(null)

  useEffect(() => {
    fetchReports()
  }, [])

  useEffect(() => {
    let result = [...reports]
    
    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      result = result.filter(r => 
        r.stock_name.toLowerCase().includes(query) ||
        r.ts_code.toLowerCase().includes(query) ||
        r.title.toLowerCase().includes(query)
      )
    }
    
    // Sort
    result.sort((a, b) => {
      switch (sortBy) {
        case 'date_desc':
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        case 'date_asc':
          return new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        case 'score_desc':
          return b.score - a.score
        case 'score_asc':
          return a.score - b.score
        case 'name_asc':
          return a.stock_name.localeCompare(b.stock_name)
        default:
          return 0
      }
    })
    
    setFilteredReports(result)
  }, [reports, searchQuery, sortBy])

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
        setSelectedIds((prev) => {
          const next = new Set(prev)
          next.delete(reportId)
          return next
        })
      }
    } catch (error) {
      console.error('删除报告失败:', error)
    }
  }

  const deleteSelected = async () => {
    if (selectedIds.size === 0) return
    if (!confirm(`确定要删除选中的 ${selectedIds.size} 份报告吗？`)) return

    try {
      const res = await fetch('/api/reports/batch-delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: Array.from(selectedIds) }),
      })
      if (res.ok) {
        setReports((prev) => prev.filter((r) => !selectedIds.has(r.id)))
        setSelectedIds(new Set())
      }
    } catch (error) {
      console.error('批量删除失败:', error)
    }
  }

  const exportReport = async (reportId: string) => {
    try {
      const res = await fetch(`/api/reports/${reportId}`)
      if (res.ok) {
        const data = await res.json()
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${data.stock_name}_${data.ts_code.split('.')[0]}_report.json`
        a.click()
        URL.revokeObjectURL(url)
      }
    } catch (error) {
      console.error('导出失败:', error)
    }
  }

  const copyShareLink = (reportId: string) => {
    const url = `${window.location.origin}/r/${reportId}`
    navigator.clipboard.writeText(url)
    setCopiedId(reportId)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const toggleSelect = (reportId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(reportId)) {
        next.delete(reportId)
      } else {
        next.add(reportId)
      }
      return next
    })
  }

  const toggleSelectAll = () => {
    if (selectedIds.size === filteredReports.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(filteredReports.map((r) => r.id)))
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 70) return 'text-red-600'
    if (score >= 50) return 'text-orange-500'
    return 'text-green-600'
  }

  const getScoreBg = (score: number) => {
    if (score >= 70) return 'bg-red-50'
    if (score >= 50) return 'bg-orange-50'
    return 'bg-green-50'
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
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="h-6 w-6 text-gray-700" />
          <h1 className="text-xl font-bold">分析报告</h1>
          {reports.length > 0 && (
            <Badge variant="secondary">{reports.length}</Badge>
          )}
        </div>
      </div>

      {/* Toolbar */}
      {reports.length > 0 && (
        <div className="flex flex-wrap items-center gap-4">
          {/* Search */}
          <div className="relative flex-1 min-w-[200px] max-w-sm">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <Input
              placeholder="搜索股票名称或代码..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>

          {/* Sort */}
          <Select value={sortBy} onValueChange={(v) => setSortBy(v as SortOption)}>
            <SelectTrigger className="w-[140px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="date_desc">最新优先</SelectItem>
              <SelectItem value="date_asc">最早优先</SelectItem>
              <SelectItem value="score_desc">评分最高</SelectItem>
              <SelectItem value="score_asc">评分最低</SelectItem>
              <SelectItem value="name_asc">名称排序</SelectItem>
            </SelectContent>
          </Select>

          {/* Batch actions */}
          {selectedIds.size > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500">
                已选 {selectedIds.size} 项
              </span>
              <Button
                variant="destructive"
                size="sm"
                onClick={deleteSelected}
              >
                <Trash2 className="mr-1 h-4 w-4" />
                删除选中
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Content */}
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
      ) : filteredReports.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center text-gray-500">
            没有匹配的报告
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Select All */}
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <button
              onClick={toggleSelectAll}
              className="flex items-center gap-1 hover:text-gray-700"
            >
              {selectedIds.size === filteredReports.length ? (
                <CheckSquare className="h-4 w-4 text-blue-500" />
              ) : (
                <Square className="h-4 w-4" />
              )}
              全选
            </button>
          </div>

          {/* Grid */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filteredReports.map((report) => (
              <Card
                key={report.id}
                className={cn(
                  'hover:shadow-md transition-all',
                  selectedIds.has(report.id) && 'ring-2 ring-blue-500'
                )}
              >
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    {/* Checkbox */}
                    <button
                      onClick={() => toggleSelect(report.id)}
                      className="mt-1 flex-shrink-0"
                    >
                      {selectedIds.has(report.id) ? (
                        <CheckSquare className="h-5 w-5 text-blue-500" />
                      ) : (
                        <Square className="h-5 w-5 text-gray-300 hover:text-gray-400" />
                      )}
                    </button>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="text-sm text-gray-500">
                            {report.ts_code.split('.')[0]}
                          </div>
                          <div className="font-medium truncate">{report.stock_name}</div>
                        </div>
                        <div className={cn(
                          'text-2xl font-bold px-2 py-1 rounded',
                          getScoreColor(report.score),
                          getScoreBg(report.score)
                        )}>
                          {report.score}
                        </div>
                      </div>

                      <div className="mt-3 flex items-center gap-1 text-xs text-gray-400">
                        <Clock className="h-3 w-3" />
                        {formatDate(report.created_at)}
                      </div>

                      <div className="mt-4 flex items-center gap-2">
                        <Link to={`/r/${report.id}`} className="flex-1">
                          <Button variant="outline" size="sm" className="w-full">
                            <ExternalLink className="mr-1 h-3 w-3" />
                            查看
                          </Button>
                        </Link>
                        
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => copyShareLink(report.id)}
                        >
                          {copiedId === report.id ? (
                            <Check className="h-4 w-4 text-green-500" />
                          ) : (
                            <Copy className="h-4 w-4" />
                          )}
                        </Button>

                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => exportReport(report.id)}>
                              <Download className="mr-2 h-4 w-4" />
                              导出 JSON
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              onClick={() => deleteReport(report.id)}
                              className="text-red-600"
                            >
                              <Trash2 className="mr-2 h-4 w-4" />
                              删除
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
