import { useEffect } from 'react'

const selector = '[data-liquid]'

function surface(target: EventTarget | null): HTMLElement | null {
  return target instanceof Element ? target.closest<HTMLElement>(selector) : null
}

export function useLiquidFeedback() {
  useEffect(() => {
    const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)')
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)')
    const timers = new Map<HTMLElement, number>()
    let pressed: HTMLElement | null = null
    let moveFrame = 0
    let pointer: { element: HTMLElement; x: number; y: number } | null = null

    function move(event: PointerEvent) {
      if (!finePointer.matches || reducedMotion.matches) return
      const element = surface(event.target)
      if (!element) return
      pointer = { element, x: event.clientX, y: event.clientY }
      if (moveFrame) return
      moveFrame = requestAnimationFrame(() => {
        moveFrame = 0
        if (!pointer?.element.isConnected) return
        const { element, x, y } = pointer
        const bounds = element.getBoundingClientRect()
        element.style.setProperty('--liquid-x', `${x - bounds.left}px`)
        element.style.setProperty('--liquid-y', `${y - bounds.top}px`)
      })
    }

    function down(event: PointerEvent) {
      if (event.button !== 0) return
      release()
      pressed = surface(event.target)
      if (pressed?.matches(':disabled, [aria-disabled="true"]')) { pressed = null; return }
      move(event)
      pressed?.classList.add('liquid-pressed')
    }

    function leave(event: PointerEvent) {
      if (pressed && event.relatedTarget instanceof Node && pressed.contains(event.relatedTarget)) return
      if (surface(event.target) === pressed) release()
    }

    function release() {
      pressed?.classList.remove('liquid-pressed')
      pressed = null
    }

    function confirm(event: MouseEvent) {
      const element = surface(event.target)
      if (!element || element.matches(':disabled, [aria-disabled="true"]')) return
      window.clearTimeout(timers.get(element))
      element.classList.remove('liquid-confirmed')
      element.classList.add('liquid-confirmed')
      timers.set(element, window.setTimeout(() => {
        element.classList.remove('liquid-confirmed')
        timers.delete(element)
      }, reducedMotion.matches ? 180 : 520))
    }

    document.addEventListener('pointermove', move, { passive: true })
    document.addEventListener('pointerdown', down)
    document.addEventListener('pointerup', release)
    document.addEventListener('pointercancel', release)
    document.addEventListener('pointerout', leave)
    window.addEventListener('blur', release)
    document.addEventListener('click', confirm)
    return () => {
      document.removeEventListener('pointermove', move)
      document.removeEventListener('pointerdown', down)
      document.removeEventListener('pointerup', release)
      document.removeEventListener('pointercancel', release)
      document.removeEventListener('pointerout', leave)
      window.removeEventListener('blur', release)
      document.removeEventListener('click', confirm)
      timers.forEach(timer => window.clearTimeout(timer))
      timers.forEach((_, element) => element.classList.remove('liquid-confirmed'))
      cancelAnimationFrame(moveFrame)
      release()
    }
  }, [])
}
