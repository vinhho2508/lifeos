import React from 'react'
import ReactDOM from 'react-dom/client'
import Settings from './Settings.tsx'
import '../src/theme-init'
import './popup.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Settings />
  </React.StrictMode>,
)
