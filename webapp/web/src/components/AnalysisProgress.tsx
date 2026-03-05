import { Progress } from '@/components/ui/progress'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { 
  Database, 
  BarChart3, 
  TrendingUp, 
  Wallet, 
  Brain,
  CheckCircle2,
  Loader2
} from 'lucide-react'

interface AnalysisProgressProps {
  progress: number
  message: string
  tsCode: string
}

const STEPS = [
  { key: 'basic', label: '基本信息', icon: Database, threshold: 5 },
  { key: 'daily', label: '行情数据', icon: BarChart3, threshold: 25 },
  { key: 'fundamental', label: '基本面分析', icon: TrendingUp, threshold: 50 },
  { key: 'technical', label: '技术面分析', icon: BarChart3, threshold: 70 },
  { key: 'capital', label: '资金面分析', icon: Wallet, threshold: 85 },
  { key: 'ai', label: 'AI 摘要', icon: Brain, threshold: 95 },
]

export function AnalysisProgress({ progress, message, tsCode }: AnalysisProgressProps) {
  return (
    <Card className="overflow-hidden">
      <CardContent className="p-0">
        {/* Header */}
        <div className="bg-gradient-to-r from-red-500 to-orange-500 p-6 text-white">
          <div className="flex items-center gap-3">
            <Loader2 className="h-8 w-8 animate-spin" />
            <div>
              <h2 className="text-xl font-bold">正在分析 {tsCode}</h2>
              <p className="text-white/80 text-sm mt-1">{message}</p>
            </div>
          </div>
          <div className="mt-6">
            <div className="flex justify-between text-sm mb-2">
              <span>分析进度</span>
              <span>{progress}%</span>
            </div>
            <Progress value={progress} className="h-2 bg-white/20" />
          </div>
        </div>

        {/* Steps */}
        <div className="p-6">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {STEPS.map((step, index) => {
              const isComplete = progress >= step.threshold
              const isCurrent = !isComplete && (index === 0 || progress >= STEPS[index - 1].threshold)
              const Icon = step.icon

              return (
                <div
                  key={step.key}
                  className={cn(
                    'flex flex-col items-center gap-2 p-3 rounded-lg transition-all',
                    isComplete && 'bg-green-50',
                    isCurrent && 'bg-orange-50 animate-pulse',
                    !isComplete && !isCurrent && 'opacity-40'
                  )}
                >
                  <div className={cn(
                    'w-10 h-10 rounded-full flex items-center justify-center',
                    isComplete && 'bg-green-500 text-white',
                    isCurrent && 'bg-orange-500 text-white',
                    !isComplete && !isCurrent && 'bg-gray-200 text-gray-400'
                  )}>
                    {isComplete ? (
                      <CheckCircle2 className="h-5 w-5" />
                    ) : isCurrent ? (
                      <Loader2 className="h-5 w-5 animate-spin" />
                    ) : (
                      <Icon className="h-5 w-5" />
                    )}
                  </div>
                  <span className={cn(
                    'text-xs font-medium text-center',
                    isComplete && 'text-green-700',
                    isCurrent && 'text-orange-700',
                    !isComplete && !isCurrent && 'text-gray-400'
                  )}>
                    {step.label}
                  </span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Tips */}
        <div className="px-6 pb-6">
          <div className="text-xs text-gray-400 text-center">
            分析过程大约需要 1-2 分钟，请耐心等待...
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
