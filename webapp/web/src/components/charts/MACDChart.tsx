import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import type { FactorDataPoint } from '@/types/analysis'

interface MACDChartProps {
  data: FactorDataPoint[]
  height?: number
}

export function MACDChart({ data, height = 150 }: MACDChartProps) {
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
  const difData = data.map(d => d.macd_dif ?? null)
  const deaData = data.map(d => d.macd_dea ?? null)
  const macdData = data.map(d => {
    const val = d.macd ?? null
    if (val === null) return null
    return {
      value: val,
      itemStyle: {
        color: val >= 0 ? '#ef4444' : '#22c55e'
      }
    }
  })

  const option: EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params: unknown) => {
        const paramArray = params as Array<{
          axisValue: string
          seriesName: string
          value: number | { value: number }
          color: string
        }>
        if (!paramArray || paramArray.length === 0) return ''
        
        let html = `<div class="font-medium mb-1">${paramArray[0].axisValue}</div>`
        paramArray.forEach(item => {
          const val = typeof item.value === 'object' ? item.value?.value : item.value
          if (val !== null && val !== undefined) {
            html += `<div style="color:${item.color}">${item.seriesName}: ${val.toFixed(3)}</div>`
          }
        })
        return html
      }
    },
    legend: {
      data: ['DIF', 'DEA', 'MACD'],
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
      scale: true,
      splitLine: { lineStyle: { color: '#f3f4f6', type: 'dashed' } },
      axisLabel: { fontSize: 10, color: '#6b7280' }
    },
    series: [
      {
        name: 'DIF',
        type: 'line',
        data: difData,
        symbol: 'none',
        lineStyle: { width: 1.5, color: '#3b82f6' }
      },
      {
        name: 'DEA',
        type: 'line',
        data: deaData,
        symbol: 'none',
        lineStyle: { width: 1.5, color: '#f59e0b' }
      },
      {
        name: 'MACD',
        type: 'bar',
        data: macdData,
        barWidth: '50%'
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
