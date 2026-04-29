import { FloatingIcon } from './floating-icon/FloatingIcon'

if (!customElements.get('lifeos-floating-icon')) {
  customElements.define('lifeos-floating-icon', FloatingIcon)
}

let currentIcon: FloatingIcon | null = null

function getSelectionCoords(): { x: number; y: number } {
  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0) {
    return { x: 0, y: 0 }
  }
  const range = selection.getRangeAt(0)
  const rect = range.getBoundingClientRect()
  return {
    x: rect.right + window.scrollX,
    y: rect.top + window.scrollY,
  }
}

function showIcon(text: string) {
  hideIcon()
  const coords = getSelectionCoords()
  currentIcon = document.createElement('lifeos-floating-icon') as FloatingIcon
  currentIcon.style.position = 'absolute'
  currentIcon.style.left = `${coords.x + 8}px`
  currentIcon.style.top = `${coords.y - 8}px`
  currentIcon.style.zIndex = '2147483647'

  currentIcon.addEventListener('click', () => {
    const selected = window.getSelection()?.toString().trim() || text
    chrome.storage.local.set({
      lifeos_selected: {
        text: selected,
        url: location.href,
        title: document.title,
      },
      lifeos_context_action: 'chat',
    })
    chrome.runtime.sendMessage({ type: 'OPEN_SIDE_PANEL' })
    hideIcon()
  })

  document.body.appendChild(currentIcon)
}

function hideIcon() {
  if (currentIcon && currentIcon.parentNode) {
    currentIcon.parentNode.removeChild(currentIcon)
    currentIcon = null
  }
}

document.addEventListener('mouseup', () => {
  const selection = window.getSelection()?.toString().trim()
  if (selection && selection.length > 0) {
    showIcon(selection)
  } else {
    hideIcon()
  }
})

document.addEventListener('mousedown', (e) => {
  if (currentIcon && !currentIcon.contains(e.target as Node)) {
    hideIcon()
  }
})
