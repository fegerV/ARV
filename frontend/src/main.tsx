import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { VertexThemeProvider } from './providers/ThemeProvider'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <VertexThemeProvider>
        <App />
      </VertexThemeProvider>
    </BrowserRouter>
  </React.StrictMode>
);
