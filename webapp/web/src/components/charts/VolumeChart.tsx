import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import type { ChartDataPoint } from '@/types/analysis'

interface VolumeChartProps {
  data: ChartDataPoint[]
  height?: number
}

export function VolumeChart({ data, height = 150 }: VolumeChartProps) {
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
  const volumes = data.map((d) => {
    const isUp = d.close >= d.open
    return {
      value: d.vol,
      itemStyle: {
        color: isUp ? '#ef4444' : '#22c55e'
      }
    }
  })

  const option: EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: unknown) => {
        const paramArray = params as Array<{
          axisValue: string
          value: number
        }>
        if (!paramArray || paramArray.length === 0) return ''
        const item = paramArray[0]
        const vol = item.value
        const volStr = vol >= 100000000 
          ? (vol / 100000000).toFixed(2) + '亿'
          : vol >= 10000 
            ? (vol / 10000).toFixed(2) + '万'
            : vol.toString()
        return `${item.axisValue}<br/>成交量: ${volStr}`
      }
    },
    grid: {
      left: '8%',
      right: '3%',
      top: '10%',
      bottom: '15%'
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: '#e5e7eb' } },
      axisLabel: { fontSize: 10, color: '#6b7280' }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#f3f4f6', type: 'dashed' } },
      axisLabel: { 
        fontSize: 10, 
        color: '#6b7280',
        formatter: (value: number) => {
          if (value >= 100000000) return (value / 100000000).toFixed(1) + '亿'
          if (value >= 10000) return (value / 10000).toFixed(0) + '万'
          return value.toString()
        }
      }
    },
    series: [{
      type: 'bar',
      data: volumes,
      barWidth: '60%'
    }]
  }

  return (
    <ReactECharts 
      option={option} 
      style={{ height, width: '100%' }}
      notMerge={true}
    />
  )
}
