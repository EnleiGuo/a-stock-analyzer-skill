import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface DataCardProps {
  title: string
  icon?: string
  score?: number
  comment?: string
  data?: Record<string, unknown>
  className?: string
}

// Format value for display
function formatValue(value: unknown): string {
  if (value === null || value === undefined) return 'N/A'
  if (typeof value === 'boolean') return value ? '✅ 是' : '❌ 否'
  if (Array.isArray(value)) {
    return value.map(item => {
      if (typeof item === 'object' && item !== null) {
        const obj = item as Record<string, unknown>
        const name = obj['名称'] || obj['name'] || ''
        const parts = name ? [String(name)] : []
        for (const [k, v] of Object.entries(obj)) {
          if (k === '名称' || k === 'name') continue
          parts.push(`${k}${v}`)
        }
        return parts.join('，') || JSON.stringify(item)
      }
      return String(item)
    }).join(' → ')
  }
  if (typeof value === 'number') {
    return value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
  }
  return String(value)
}

// Get score color (A-stock convention: red=bullish/high, green=bearish/low)
function getScoreColor(score: number): string {
  if (score >= 65) return 'text-red-500'
  if (score >= 40) return 'text-orange-500'
  return 'text-green-500'
}

export function DataCard({ title, icon, score, comment, data, className }: DataCardProps) {
  const hasData = data && Object.keys(data).length > 0

  return (
    <Card className={cn('h-full w-full min-w-0', className)}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">
            {icon && <span className="mr-1">{icon}</span>}
            {title}
          </CardTitle>
          {score !== undefined && (
            <span className={cn('text-lg font-bold', getScoreColor(score))}>
              {score}分
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        {comment && (
          <div className="text-xs text-muted-foreground bg-muted/50 border-l-2 border-blue-500 px-2 py-1 rounded-r mb-2">
            {comment}
          </div>
        )}
        {hasData ? (
          <div className="space-y-1">
            {Object.entries(data).map(([key, value]) => (
              <div key={key} className="flex justify-between text-xs border-b border-gray-100 py-1 last:border-0">
                <span className="text-muted-foreground">{key}</span>
                <span className="font-medium text-right max-w-[55%] break-words" title={formatValue(value)}>
                  {formatValue(value)}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground italic">暂无数据</p>
        )}
      </CardContent>
    </Card>
  )
}

// Smaller variant for grid layouts
export function DataCardCompact({ title, icon, score, comment, data }: DataCardProps) {
  const hasData = data && Object.keys(data).length > 0

  return (
    <div className="bg-white rounded-lg border p-3 h-full">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium">
          {icon && <span className="mr-1">{icon}</span>}
          {title}
        </span>
        {score !== undefined && (
          <span className={cn('text-base font-bold', getScoreColor(score))}>
            {score}
          </span>
        )}
      </div>
      {comment && (
        <p className="text-xs text-muted-foreground mb-2 line-clamp-2">{comment}</p>
      )}
      {hasData && (
        <div className="space-y-0.5">
          {Object.entries(data).slice(0, 5).map(([key, value]) => (
            <div key={key} className="flex justify-between text-xs">
              <span className="text-muted-foreground truncate max-w-[45%]">{key}</span>
              <span className="font-medium truncate max-w-[50%]">{formatValue(value)}</span>
            </div>
          ))}
          {Object.keys(data).length > 5 && (
            <p className="text-xs text-muted-foreground">...还有 {Object.keys(data).length - 5} 项</p>
          )}
        </div>
      )}
    </div>
  )
}
