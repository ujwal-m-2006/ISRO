import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import './index.css';
import App from './App';
import {
  Dashboard,
  LiveData,
  Nowcasting,
  Forecasting,
  HistoricalAnalysis,
  SolarAnalytics,
  ModelPerformance,
  Alerts,
  Settings,
  About,
  SolarWind,
  CMETracker,
  EarthImpact,
  Satellites,
  HistoricalArchive,
  Predictions,
  TrainedModel,
} from './pages';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<App />}>
            <Route index element={<Dashboard />} />
            <Route path="live-data" element={<LiveData />} />
            <Route path="nowcasting" element={<Nowcasting />} />
            <Route path="forecasting" element={<Forecasting />} />
            <Route path="historical" element={<HistoricalAnalysis />} />
            <Route path="analytics" element={<SolarAnalytics />} />
            <Route path="model-performance" element={<ModelPerformance />} />
            <Route path="alerts" element={<Alerts />} />
            <Route path="settings" element={<Settings />} />
            <Route path="about" element={<About />} />
            <Route path="solar-wind" element={<SolarWind />} />
            <Route path="cme-tracker" element={<CMETracker />} />
            <Route path="earth-impact" element={<EarthImpact />} />
            <Route path="satellites" element={<Satellites />} />
            <Route path="archive" element={<HistoricalArchive />} />
            <Route path="predictions" element={<Predictions />} />
            <Route path="trained-model" element={<TrainedModel />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  </React.StrictMode>,
);
