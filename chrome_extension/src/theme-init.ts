// Follow the OS color scheme. MV3 forbids inline <script>, so this runs as a module import.
const media = window.matchMedia('(prefers-color-scheme: dark)')

function apply() {
  const theme = media.matches ? 'dark' : 'light'
  const root = document.documentElement
  root.classList.remove('light', 'dark')
  root.classList.add(theme)
  root.setAttribute('data-theme', theme)
}

apply()
media.addEventListener('change', apply)
