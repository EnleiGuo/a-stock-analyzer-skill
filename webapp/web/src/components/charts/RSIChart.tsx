import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import type { FactorDataPoint } from '@/types/analysis'

interface RSIChartProps {
  data: FactorDataPoint[]
  height?: number
}

export function RSIChart({ data, height = 150 }: RSIChartProps) {
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
  const rsi6Data = data.map(d => d.rsi_6 ?? null)
  const rsi12Data = data.map(d => d.rsi_12 ?? null)

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
          if (item.value !== null && item.value !== undefined) {
            html += `<div style="color:${item.color}">${item.seriesName}: ${item.value.toFixed(2)}</div>`
          }
        })
        return html
      }
    },
    legend: {
      data: ['RSI(6)', 'RSI(12)'],
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
        name: 'RSI(6)',
        type: 'line',
        data: rsi6Data,
        symbol: 'none',
        lineStyle: { width: 1.5, color: '#8b5cf6' }
      },
      {
        name: 'RSI(12)',
        type: 'line',
        data: rsi12Data,
        symbol: 'none',
        lineStyle: { width: 1.5, color: '#06b6d4' }
      },
      // 超买线 70
      {
        name: '超买',
        type: 'line',
        data: dates.map(() => 70),
        symbol: 'none',
        lineStyle: { width: 1, color: '#fca5a5', type: 'dashed' },
        silent: true
      },
      // 超卖线 30
      {
        name: '超卖',
        type: 'line',
        data: dates.map(() => 30),
        symbol: 'none',
        lineStyle: { width: 1, color: '#86efac', type: 'dashed' },
        silent: true
      }
    ],
    // 标注超买超卖区域
    visualMap: {
      show: false,
      pieces: [
        { gt: 70, color: '#fef2f2' },
        { lte: 70, gt: 30, color: 'transparent' },
        { lte: 30, color: '#f0fdf4' }
      ],
      outOfRange: { color: 'transparent' }
    }
  }

  return (
    <ReactECharts 
      option={option} 
      style={{ height, width: '100%' }}
      notMerge={true}
    />
  )
}
