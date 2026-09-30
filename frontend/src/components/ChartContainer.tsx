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
  const latestOption = useRef(option)
  latestOption.current = option
  useEffect(() => { callback.current = onClick }, [onClick])
  useEffect(() => {
    if (!container.current) return
    let chart: ReturnType<typeof echarts.init> | undefined
    let observer: ResizeObserver | undefined
    let resizeFrame = 0
    let paintFrame = 0
    // Let the destination page and navigation paint before allocating canvas
    // and computing the first chart layout.
    const firstFrame = requestAnimationFrame(() => {
      paintFrame = requestAnimationFrame(() => {
        if (!container.current) return
        chart = echarts.init(container.current, undefined, { renderer: 'canvas' })
        chart.setOption(latestOption.current, true)
        observer = new ResizeObserver(() => {
          cancelAnimationFrame(resizeFrame)
          resizeFrame = requestAnimationFrame(() => chart?.resize())
        })
        observer.observe(container.current)
        chart.on('click', params => { if (params.name) callback.current?.(params.name) })
      })
    })
    return () => {
      cancelAnimationFrame(firstFrame)
      cancelAnimationFrame(paintFrame)
      cancelAnimationFrame(resizeFrame)
      observer?.disconnect()
      chart?.dispose()
    }
  }, [])
  useEffect(() => {
    const chart = container.current && echarts.getInstanceByDom(container.current)
    chart?.setOption(option, true)
  }, [option])
  return <div ref={container} className="chart-canvas" role="img" aria-label="交互式数据关系图，点击节点可筛选记录" style={{ height }} />
}
