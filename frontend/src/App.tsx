import React, { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { TopBar, MainNav, HeroCarousel, SiteFooter, SiteLogo, NrscBanner } from './components/shell';
import { FlareAlertTicker, FlareDetailModal } from './components/flare-alerts';
import type { FlareAlert } from './types';

function App() {
  const location = useLocation();
  const showHero = location.pathname === '/';
  const [selectedAlert, setSelectedAlert] = useState<FlareAlert | null>(null);

  return (
    <div className="min-h-screen bg-space-black text-space-light flex flex-col">
      <TopBar />
      <NrscBanner />
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <SiteLogo className="h-10 w-auto" />
              <div className="w-10 h-10 bg-gradient-to-br from-space-blue to-space-purple rounded-lg flex items-center justify-center">
                <span className="font-bold text-xs text-white">L1</span>
              </div>
              <div>
                <h1 className="text-lg sm:text-xl font-bold">Solar Flare Prediction System</h1>
                <p className="text-xs text-space-gray hidden sm:block">ISRO Aditya-L1 Mission Dashboard</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="hidden sm:flex items-center space-x-2 text-sm text-space-gray">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                <span>NOAA GOES-18 Live</span>
              </div>
              <div className="w-8 h-8 bg-space-blue rounded-full flex items-center justify-center">
                <span className="text-xs font-bold text-white">OP</span>
              </div>
            </div>
          </div>
        </div>
      </header>
      <MainNav />
      <FlareAlertTicker onSelect={setSelectedAlert} />
      {showHero && <HeroCarousel />}

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex-1 w-full">
        <main className="min-w-0">
          <Outlet />
        </main>
      </div>

      <SiteFooter />
      {selectedAlert && <FlareDetailModal alert={selectedAlert} onClose={() => setSelectedAlert(null)} />}
    </div>
  );
}

export default App;
