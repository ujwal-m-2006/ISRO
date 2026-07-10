import React from 'react'
import { Routes, Route } from 'react-router-dom'

// Pages
import { Dashboard, LiveData } from '../pages'

function Router() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/live-data" element={<LiveData />} />
      <Route path="/nowcasting" element={<div className="p-6">Nowcasting Page</div>} />
      <Route path="/forecasting" element={<div className="p-6">Forecasting Page</div>} />
      <Route path="/historical" element={<div className="p-6">Historical Analysis Page</div>} />
      <Route path="/analytics" element={<div className="p-6">Solar Analytics Page</div>} />
      <Route path="/model-performance" element={<div className="p-6">AI Model Performance Page</div>} />
      <Route path="/alerts" element={<div className="p-6">Alerts Page</div>} />
      <Route path="/settings" element={<div className="p-6">Settings Page</div>} />
      <Route path="/about" element={<div className="p-6">About Page</div>} />
    </Routes>
  )
}

export default Router