const ICON_SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/></svg>`

export class FloatingIcon extends HTMLElement {
  constructor() {
    super()
    const shadow = this.attachShadow({ mode: 'closed' })

    const wrapper = document.createElement('div')
    wrapper.innerHTML = ICON_SVG
    wrapper.style.cssText = `
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background-color: #111827;
      color: #ffffff;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      box-shadow: 0 4px 12px rgba(0,0,0,0.25);
      transition: transform 0.15s ease, box-shadow 0.15s ease;
      pointer-events: auto;
    `

    wrapper.addEventListener('mouseenter', () => {
      wrapper.style.transform = 'scale(1.1)'
      wrapper.style.boxShadow = '0 6px 16px rgba(0,0,0,0.35)'
    })
    wrapper.addEventListener('mouseleave', () => {
      wrapper.style.transform = 'scale(1)'
      wrapper.style.boxShadow = '0 4px 12px rgba(0,0,0,0.25)'
    })

    shadow.appendChild(wrapper)
  }
}
