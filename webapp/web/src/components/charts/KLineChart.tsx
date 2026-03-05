import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import type { ChartDataPoint } from '@/types/analysis'

interface KLineChartProps {
  data: ChartDataPoint[]
  maData?: {
    ma5?: number[]
    ma10?: number[]
    ma20?: number[]
    ma60?: number[]
  }
  height?: number
}

export function KLineChart({ data, maData, height = 400 }: KLineChartProps) {
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

  // 准备数据
  const dates = data.map(d => d.trade_date.slice(5)) // MM-DD format
  const ohlcData = data.map(d => [d.open, d.close, d.low, d.high])
  const volumes = data.map(d => d.vol)

  // 计算涨跌颜色
  const volumeColors = data.map(d => 
    d.close >= d.open ? '#ef4444' : '#22c55e'
  )

  const option: EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      },
      formatter: (params: unknown) => {
        const paramArray = params as Array<{
          axisValue: string
          seriesName: string
          value: number | number[]
          color: string
        }>
        if (!paramArray || paramArray.length === 0) return ''
        
        const date = paramArray[0].axisValue
        let html = `<div class="font-medium mb-1">${date}</div>`
        
        paramArray.forEach(item => {
          if (item.seriesName === 'K线') {
            const values = item.value as number[]
            const open = values[0]
            const close = values[1]
            const low = values[2]
            const high = values[3]
            const change = ((close - open) / open * 100).toFixed(2)
            const color = close >= open ? '#ef4444' : '#22c55e'
            html += `
              <div>开盘: ${open.toFixed(2)}</div>
              <div>收盘: <span style="color:${color}">${close.toFixed(2)}</span></div>
              <div>最高: ${high.toFixed(2)}</div>
              <div>最低: ${low.toFixed(2)}</div>
              <div>涨跌: <span style="color:${color}">${change}%</span></div>
            `
          } else if (item.seriesName.startsWith('MA')) {
            const value = item.value as number
            if (value) {
              html += `<div style="color:${item.color}">${item.seriesName}: ${value.toFixed(2)}</div>`
            }
          }
        })
        
        return html
      }
    },
    legend: {
      data: ['MA5', 'MA10', 'MA20', 'MA60'].filter((_, i) => {
        const keys = ['ma5', 'ma10', 'ma20', 'ma60'] as const
        return maData?.[keys[i]]?.length
      }),
      top: 10,
      textStyle: { fontSize: 11 }
    },
    grid: [
      { left: '8%', right: '3%', top: '12%', height: '55%' },
      { left: '8%', right: '3%', top: '72%', height: '18%' }
    ],
    xAxis: [
      {
        type: 'category',
        data: dates,
        boundaryGap: true,
        axisLine: { lineStyle: { color: '#e5e7eb' } },
        axisLabel: { fontSize: 10, color: '#6b7280' },
        splitLine: { show: false }
      },
      {
        type: 'category',
        gridIndex: 1,
        data: dates,
        boundaryGap: true,
        axisLine: { lineStyle: { color: '#e5e7eb' } },
        axisLabel: { show: false },
        splitLine: { show: false }
      }
    ],
    yAxis: [
      {
        type: 'value',
        scale: true,
        splitLine: { lineStyle: { color: '#f3f4f6', type: 'dashed' } },
        axisLabel: { fontSize: 10, color: '#6b7280' }
      },
      {
        type: 'value',
        gridIndex: 1,
        scale: true,
        splitLine: { show: false },
        axisLabel: { show: false }
      }
    ],
    dataZoom: [
      {
        type: 'inside',
        xAxisIndex: [0, 1],
        start: Math.max(0, 100 - (60 / data.length) * 100),
        end: 100
      },
      {
        type: 'slider',
        xAxisIndex: [0, 1],
        bottom: 5,
        height: 20,
        start: Math.max(0, 100 - (60 / data.length) * 100),
        end: 100
      }
    ],
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        data: ohlcData,
        itemStyle: {
          color: '#ef4444',      // 涨 - 红色填充
          color0: '#22c55e',     // 跌 - 绿色填充  
          borderColor: '#ef4444',
          borderColor0: '#22c55e'
        }
      },
      {
        name: '成交量',
        type: 'bar',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: volumes.map((v, i) => ({
          value: v,
          itemStyle: { color: volumeColors[i] }
        }))
      },
      ...(maData?.ma5?.length ? [{
        name: 'MA5',
        type: 'line' as const,
        data: maData.ma5,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 1, color: '#f59e0b' }
      }] : []),
      ...(maData?.ma10?.length ? [{
        name: 'MA10',
        type: 'line' as const,
        data: maData.ma10,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 1, color: '#3b82f6' }
      }] : []),
      ...(maData?.ma20?.length ? [{
        name: 'MA20',
        type: 'line' as const,
        data: maData.ma20,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 1, color: '#8b5cf6' }
      }] : []),
      ...(maData?.ma60?.length ? [{
        name: 'MA60',
        type: 'line' as const,
        data: maData.ma60,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 1, color: '#06b6d4' }
      }] : [])
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
