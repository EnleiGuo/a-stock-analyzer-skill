import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import type { FactorDataPoint } from '@/types/analysis'

interface KDJChartProps {
  data: FactorDataPoint[]
  height?: number
}

export function KDJChart({ data, height = 150 }: KDJChartProps) {
  if (!data || data.length === 0) {
    return (
      <div 
        className="flex items-center justify-center text-gray-500 bg-gray-50 rounded"
        style={{ height }}
      >
        暂无数据
      </div>
    )
  }

  const dates = data.map(d => d.trade_date.slice(5))
  const kData = data.map(d => d.kdj_k ?? null)
  const dData = data.map(d => d.kdj_d ?? null)
  const jData = data.map(d => d.kdj_j ?? null)

  const option: EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params: unknown) => {
        const paramArray = params as Array<{
          axisValue: string
          seriesName: string
          value: number
          color: string
        }>
        if (!paramArray || paramArray.length === 0) return ''
        
        let html = `<div class="font-medium mb-1">${paramArray[0].axisValue}</div>`
        paramArray.forEach(item => {
          if (item.value !== null && item.value !== undefined && !['超买', '超卖'].includes(item.seriesName)) {
            html += `<div style="color:${item.color}">${item.seriesName}: ${item.value.toFixed(2)}</div>`
          }
        })
        return html
      }
    },
    legend: {
      data: ['K', 'D', 'J'],
      top: 5,
      textStyle: { fontSize: 11 }
    },
    grid: {
      left: '8%',
      right: '3%',
      top: '25%',
      bottom: '10%'
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: '#e5e7eb' } },
      axisLabel: { fontSize: 10, color: '#6b7280' }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      splitLine: { lineStyle: { color: '#f3f4f6', type: 'dashed' } },
      axisLabel: { fontSize: 10, color: '#6b7280' }
    },
    series: [
      {
        name: 'K',
        type: 'line',
        data: kData,
        symbol: 'none',
        lineStyle: { width: 1.5, color: '#3b82f6' }
      },
      {
        name: 'D',
        type: 'line',
        data: dData,
        symbol: 'none',
        lineStyle: { width: 1.5, color: '#f59e0b' }
      },
      {
        name: 'J',
        type: 'line',
        data: jData,
        symbol: 'none',
        lineStyle: { width: 1.5, color: '#8b5cf6' }
      },
      // 超买线 80
      {
        name: '超买',
        type: 'line',
        data: dates.map(() => 80),
        symbol: 'none',
        lineStyle: { width: 1, color: '#fca5a5', type: 'dashed' },
        silent: true
      },
      // 超卖线 20
      {
        name: '超卖',
        type: 'line',
        data: dates.map(() => 20),
        symbol: 'none',
        lineStyle: { width: 1, color: '#86efac', type: 'dashed' },
        silent: true
      }
    ]
  }

  return (
    <ReactECharts 
      option={option} 
      style={{ height, width: '100%' }}
      notMerge={true}
    />
  )
}
