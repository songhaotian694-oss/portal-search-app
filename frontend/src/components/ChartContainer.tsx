import { useEffect, useRef } from 'react'
import * as echarts from 'echarts/core'
import { BarChart, SankeyChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsOption } from 'echarts'

echarts.use([BarChart, SankeyChart, GridComponent, TooltipComponent, CanvasRenderer])

export function ChartContainer({ option, height = 440, onClick }: { option: EChartsOption; height?: number; onClick?: (name: string) => void }) {
  const container = useRef<HTMLDivElement>(null)
  const callback = useRef(onClick)
  useEffect(() => { callback.current = onClick }, [onClick])
  useEffect(() => {
    if (!container.current) return
    const chart = echarts.init(container.current, undefined, { renderer: 'canvas' })
    const observer = new ResizeObserver(() => chart.resize())
    observer.observe(container.current)
    chart.on('click', params => { if (params.name) callback.current?.(params.name) })
    return () => { observer.disconnect(); chart.dispose() }
  }, [])
  useEffect(() => {
    const chart = container.current && echarts.getInstanceByDom(container.current)
    chart?.setOption(option, true)
  }, [option])
  return <div ref={container} className="chart-canvas" role="img" aria-label="交互式数据关系图，点击节点可筛选记录" style={{ height }} />
}
