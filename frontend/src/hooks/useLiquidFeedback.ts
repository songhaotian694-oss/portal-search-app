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

    function move(event: PointerEvent) {
      if (!finePointer.matches || reducedMotion.matches) return
      const element = surface(event.target)
      if (!element) return
      const bounds = element.getBoundingClientRect()
      element.style.setProperty('--liquid-x', `${event.clientX - bounds.left}px`)
      element.style.setProperty('--liquid-y', `${event.clientY - bounds.top}px`)
    }

    function down(event: PointerEvent) {
      if (event.button !== 0) return
      pressed = surface(event.target)
      pressed?.classList.add('liquid-pressed')
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
      void element.offsetWidth
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
    document.addEventListener('click', confirm)
    return () => {
      document.removeEventListener('pointermove', move)
      document.removeEventListener('pointerdown', down)
      document.removeEventListener('pointerup', release)
      document.removeEventListener('pointercancel', release)
      document.removeEventListener('click', confirm)
      timers.forEach(timer => window.clearTimeout(timer))
    }
  }, [])
}
