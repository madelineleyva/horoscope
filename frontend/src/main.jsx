import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import App from './App.jsx'
import Win98Horoscope from './Win98Horoscope.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/main" replace />} />
        <Route path="/main" element={<Win98Horoscope />} />
        <Route path="/classic" element={<App />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
)

