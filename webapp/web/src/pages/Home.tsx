import { useNavigate } from 'react-router-dom'
import { TrendingUp, Clock } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { StockSearch } from '@/components/StockSearch'

// 热门股票（示例数据）
const hotStocks = [
  { ts_code: '600519.SH', name: '贵州茅台', score: 85 },
  { ts_code: '000001.SZ', name: '平安银行', score: 72 },
  { ts_code: '300750.SZ', name: '宁德时代', score: 68 },
  { ts_code: '002475.SZ', name: '立讯精密', score: 78 },
]

export function Home() {
  const navigate = useNavigate()

  const handleStockSelect = (tsCode: string) => {
    navigate(`/analysis/${tsCode}`)
  }

  return (
    <div className="space-y-8">
      {/* 搜索区域 */}
      <div className="flex flex-col items-center py-12">
        <h1 className="mb-6 text-3xl font-bold text-gray-900">
          A股专业深度分析
        </h1>
        <p className="mb-8 text-gray-500">
          输入股票代码或名称，获取多维度量化分析报告
        </p>
        <div className="w-full max-w-xl">
          <StockSearch onSelect={handleStockSelect} />
        </div>
      </div>

      {/* 热门分析 */}
      <section>
        <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-gray-900">
          <TrendingUp className="h-5 w-5 text-red-500" />
          热门分析
        </h2>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {hotStocks.map((stock) => (
            <Card
              key={stock.ts_code}
              className="cursor-pointer transition-shadow hover:shadow-md"
              onClick={() => handleStockSelect(stock.ts_code)}
            >
              <CardContent className="p-4">
                <div className="text-sm text-gray-500">{stock.ts_code.split('.')[0]}</div>
                <div className="font-medium">{stock.name}</div>
                <div className={`mt-2 text-lg font-bold ${
                  stock.score >= 70 ? 'text-red-600' : 
                  stock.score >= 50 ? 'text-orange-500' : 'text-green-600'
                }`}>
                  {stock.score}分
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* 最近分析 */}
      <section>
        <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-gray-900">
          <Clock className="h-5 w-5 text-gray-500" />
          最近分析
        </h2>
        <Card>
          <CardContent className="p-6 text-center text-gray-500">
            暂无分析记录，输入股票代码开始分析
          </CardContent>
        </Card>
      </section>
    </div>
  )
}
