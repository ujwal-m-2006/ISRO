import React, { useEffect, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';

interface NavItem {
  name: string;
  path?: string;
  children?: { name: string; path: string }[];
}

export const NAV_ITEMS: NavItem[] = [
  { name: 'Home', path: '/' },
  {
    name: 'Live Data',
    children: [
      { name: 'Live Summary', path: '/live-data' },
      { name: 'Solar Wind', path: '/solar-wind' },
    ],
  },
  { name: 'Predictions', path: '/predictions' },
  { name: 'Trained Model', path: '/trained-model' },
  {
    name: 'Space Weather',
    children: [
      { name: 'Nowcasting', path: '/nowcasting' },
      { name: 'Forecasting', path: '/forecasting' },
      { name: 'CME Tracker', path: '/cme-tracker' },
      { name: 'Earth Impact', path: '/earth-impact' },
    ],
  },
  { name: 'Satellites', path: '/satellites' },
  {
    name: 'Analysis',
    children: [
      { name: 'Historical Analysis (NOAA)', path: '/historical' },
      { name: 'Full Mission Archive (PRADAN)', path: '/archive' },
      { name: 'Solar Analytics', path: '/analytics' },
      { name: 'AI Model Performance', path: '/model-performance' },
    ],
  },
  { name: 'Alerts', path: '/alerts' },
  {
    name: 'More',
    children: [
      { name: 'Settings', path: '/settings' },
      { name: 'About', path: '/about' },
    ],
  },
];

/** Original inline artwork — a generic institutional seal (laurel + star),
 * not a reproduction of the actual State Emblem of India, which is legally
 * protected against unauthorized use. Kept intentionally generic. */
export function SealMark({ className = 'h-5 w-5' }: { className?: string }) {
  return (
    <svg viewBox="0 0 48 48" className={className} fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="24" cy="24" r="21" stroke="#ff9933" strokeWidth="2" fill="#0b2a5b" />
      <circle cx="24" cy="24" r="15" stroke="#ffffff" strokeWidth="1" fill="none" opacity="0.5" />
      {Array.from({ length: 24 }).map((_, i) => {
        const angle = (i / 24) * Math.PI * 2;
        const x1 = 24 + Math.cos(angle) * 12;
        const y1 = 24 + Math.sin(angle) * 12;
        const x2 = 24 + Math.cos(angle) * 15;
        const y2 = 24 + Math.sin(angle) * 15;
        return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#ffffff" strokeWidth="1" opacity="0.6" />;
      })}
      <path d="M24 15 L26.2 20.6 L32 21.2 L27.6 25 L29 30.8 L24 27.6 L19 30.8 L20.4 25 L16 21.2 L21.8 20.6 Z" fill="#ff9933" />
    </svg>
  );
}

/** Original inline artwork — a satellite-orbit motif in ISRO's navy/saffron
 * palette, used as this dashboard's own logomark (not ISRO's actual logo). */
export function IsroLogoMark({ className = 'h-10 w-10' }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" className={className} xmlns="http://www.w3.org/2000/svg">
      <circle cx="32" cy="32" r="30" fill="#0b2a5b" />
      <ellipse cx="32" cy="32" rx="24" ry="9" stroke="#ff9933" strokeWidth="2" fill="none" transform="rotate(-20 32 32)" />
      <ellipse cx="32" cy="32" rx="24" ry="9" stroke="#66aaff" strokeWidth="1.5" fill="none" transform="rotate(35 32 32)" opacity="0.8" />
      <circle cx="32" cy="32" r="6" fill="#ffcc66" />
      <circle cx="14" cy="24" r="2.4" fill="#ff9933" />
    </svg>
  );
}

/** Prefers a real image file (drop it in frontend/public/); if the file is
 * missing or fails to load, renders the given inline-SVG fallback instead of
 * a broken-image icon. Swap in real assets any time with zero code changes
 * beyond the file itself. */
function FallbackImg({ src, alt, className, fallback }: { src: string; alt: string; className?: string; fallback: React.ReactNode }) {
  const [failed, setFailed] = useState(false);
  if (failed) return <>{fallback}</>;
  return <img src={src} alt={alt} className={className} onError={() => setFailed(true)} />;
}

/** The real NRSC header banner (nrsc/emblem/ISRO/golden-jubilee), if present
 * at frontend/public/nrsc-banner.png — hidden entirely if not supplied.
 * The Government of India emblem sits beside it at a large, clearly visible
 * size (frontend/public/gov-emblem.jpg). */
export function NrscBanner() {
  return (
    <div className="bg-white border-b border-slate-200 py-2">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-wrap items-center justify-center gap-4 sm:gap-6">
        <FallbackImg src="/gov-emblem.jpg" alt="Government of India Emblem" className="h-14 sm:h-16 md:h-20 w-auto shrink-0" fallback={<SealMark className="h-14 sm:h-16 md:h-20 w-14 sm:w-16 md:w-20 shrink-0" />} />
        <FallbackImg src="/nrsc-banner.png" alt="National Remote Sensing Centre — ISRO" className="h-10 sm:h-12 md:h-16 w-auto max-w-full" fallback={<></>} />
      </div>
    </div>
  );
}

export function TopBar() {
  const [lang, setLang] = useState<'EN' | 'HI'>('EN');
  return (
    <div className="bg-isro-navy-dark text-white text-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-8 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="hidden sm:inline">Government of India &middot; Department of Space &middot; ISRO</span>
          <span className="sm:hidden">Dept. of Space &middot; ISRO</span>
        </div>
        <div className="flex items-center gap-3">
          <button type="button" onClick={() => setLang('EN')} className={`px-1.5 ${lang === 'EN' ? 'font-bold underline' : 'opacity-70'}`}>EN</button>
          <button type="button" onClick={() => setLang('HI')} className={`px-1.5 ${lang === 'HI' ? 'font-bold underline' : 'opacity-70'}`}>हिं</button>
          <a href="https://www.isro.gov.in" target="_blank" rel="noreferrer" className="opacity-80 hover:opacity-100 hidden md:inline">isro.gov.in</a>
        </div>
      </div>
    </div>
  );
}

export function SiteLogo({ className }: { className?: string }) {
  return <FallbackImg src="/isro-logo.png" alt="ISRO" className={className ?? 'h-10 w-auto'} fallback={<IsroLogoMark className={className ?? 'h-10 w-10'} />} />;
}

function NavDropdown({ item }: { item: NavItem }) {
  const location = useLocation();
  const isChildActive = item.children?.some((c) => c.path === location.pathname);
  return (
    <div className="relative group">
      <button
        type="button"
        className={`px-3 py-4 text-sm font-semibold flex items-center gap-1 border-b-2 transition-colors ${
          isChildActive ? 'border-isro-saffron text-isro-saffron' : 'border-transparent text-white hover:text-isro-saffron'
        }`}
      >
        {item.name}
        <span className="text-[10px] mt-0.5">▾</span>
      </button>
      <div className="absolute left-0 top-full hidden group-hover:block bg-white text-space-light rounded-b-md shadow-lg border border-slate-200 min-w-[200px] z-20">
        {item.children!.map((child) => (
          <NavLink
            key={child.path}
            to={child.path}
            className={({ isActive }) =>
              `block px-4 py-2.5 text-sm hover:bg-isro-navy/10 ${isActive ? 'text-isro-navy font-semibold bg-isro-navy/5' : ''}`
            }
          >
            {child.name}
          </NavLink>
        ))}
      </div>
    </div>
  );
}

export function MainNav() {
  return (
    <nav className="bg-isro-navy shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-wrap items-center">
        {NAV_ITEMS.map((item) =>
          item.children ? (
            <NavDropdown key={item.name} item={item} />
          ) : (
            <NavLink
              key={item.path}
              to={item.path!}
              end={item.path === '/'}
              className={({ isActive }) =>
                `px-3 py-4 text-sm font-semibold border-b-2 transition-colors ${
                  isActive ? 'border-isro-saffron text-isro-saffron' : 'border-transparent text-white hover:text-isro-saffron'
                }`
              }
            >
              {item.name}
            </NavLink>
          ),
        )}
      </div>
    </nav>
  );
}

const HERO_SLIDES = [
  {
    title: 'Aditya-L1 — India’s First Solar Observatory Mission',
    subtitle: 'Monitoring the Sun from the L1 Lagrange point, 1.5 million km from Earth',
    from: '#0b2a5b',
    to: '#1a3d8f',
  },
  {
    title: 'Real-Time Space Weather Monitoring',
    subtitle: 'Live X-ray flux, solar wind, and coronal mass ejection tracking',
    from: '#7e22ce',
    to: '#c2410c',
  },
  {
    title: 'Protecting Earth from Solar Hazards',
    subtitle: 'Forecasting flares, geomagnetic storms, and radiation risk to power grids, satellites, and aviation',
    from: '#0f766e',
    to: '#1a3d8f',
  },
];

export function HeroCarousel() {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setIndex((i) => (i + 1) % HERO_SLIDES.length), 5000);
    return () => clearInterval(id);
  }, []);

  const slide = HERO_SLIDES[index];

  return (
    <div
      className="relative h-56 sm:h-64 overflow-hidden flex items-center transition-colors duration-700"
      style={{ background: `linear-gradient(120deg, ${slide.from}, ${slide.to})` }}
    >
      <svg className="absolute right-4 top-1/2 -translate-y-1/2 opacity-30" width="220" height="220" viewBox="0 0 220 220" fill="none">
        <circle cx="110" cy="110" r="55" fill="#ffcc66" />
        {Array.from({ length: 12 }).map((_, i) => {
          const angle = (i / 12) * Math.PI * 2;
          const x1 = 110 + Math.cos(angle) * 65;
          const y1 = 110 + Math.sin(angle) * 65;
          const x2 = 110 + Math.cos(angle) * 95;
          const y2 = 110 + Math.sin(angle) * 95;
          return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#ffcc66" strokeWidth="4" strokeLinecap="round" />;
        })}
      </svg>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 text-white">
        <h2 className="text-2xl sm:text-3xl font-bold max-w-xl drop-shadow">{slide.title}</h2>
        <p className="mt-2 text-sm sm:text-base text-white/85 max-w-lg">{slide.subtitle}</p>
      </div>
      <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-2">
        {HERO_SLIDES.map((_, i) => (
          <button
            key={i}
            type="button"
            aria-label={`Slide ${i + 1}`}
            onClick={() => setIndex(i)}
            className={`w-2 h-2 rounded-full transition-colors ${i === index ? 'bg-white' : 'bg-white/40'}`}
          />
        ))}
      </div>
    </div>
  );
}

export function SiteFooter() {
  const year = new Date().getFullYear();
  return (
    <footer className="bg-isro-navy-dark text-white/80 mt-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-8 text-sm">
        <div className="col-span-2 sm:col-span-3 lg:col-span-2">
          <div className="flex items-center gap-3 mb-3">
            <SiteLogo className="h-9 w-auto" />
            <p className="text-white font-bold text-base">Solar Flare Prediction System</p>
          </div>
          <p>ISRO Aditya-L1 Mission Dashboard — an independent monitoring tool built on public NOAA/NASA space weather data.</p>
        </div>
        <div>
          <p className="text-white font-semibold mb-2">Live Data</p>
          <ul className="space-y-1">
            <li><NavLink className="hover:text-isro-saffron" to="/live-data">Live Summary</NavLink></li>
            <li><NavLink className="hover:text-isro-saffron" to="/solar-wind">Solar Wind</NavLink></li>
            <li><NavLink className="hover:text-isro-saffron" to="/alerts">Alerts</NavLink></li>
          </ul>
        </div>
        <div>
          <p className="text-white font-semibold mb-2">Space Weather</p>
          <ul className="space-y-1">
            <li><NavLink className="hover:text-isro-saffron" to="/nowcasting">Nowcasting</NavLink></li>
            <li><NavLink className="hover:text-isro-saffron" to="/forecasting">Forecasting</NavLink></li>
            <li><NavLink className="hover:text-isro-saffron" to="/cme-tracker">CME Tracker</NavLink></li>
            <li><NavLink className="hover:text-isro-saffron" to="/earth-impact">Earth Impact</NavLink></li>
          </ul>
        </div>
        <div>
          <p className="text-white font-semibold mb-2">Analysis</p>
          <ul className="space-y-1">
            <li><NavLink className="hover:text-isro-saffron" to="/satellites">Satellite Roster</NavLink></li>
            <li><NavLink className="hover:text-isro-saffron" to="/archive">Full Mission Archive</NavLink></li>
            <li><NavLink className="hover:text-isro-saffron" to="/historical">Historical Analysis</NavLink></li>
            <li><NavLink className="hover:text-isro-saffron" to="/analytics">Solar Analytics</NavLink></li>
            <li><NavLink className="hover:text-isro-saffron" to="/model-performance">AI Model Performance</NavLink></li>
          </ul>
        </div>
        <div>
          <p className="text-white font-semibold mb-2">Data Sources</p>
          <ul className="space-y-1">
            <li><a className="hover:text-isro-saffron" href="https://www.swpc.noaa.gov/products/goes-x-ray-flux" target="_blank" rel="noreferrer">NOAA GOES-18 X-ray Flux</a></li>
            <li><a className="hover:text-isro-saffron" href="https://www.swpc.noaa.gov/products/real-time-solar-wind" target="_blank" rel="noreferrer">NOAA Real-Time Solar Wind</a></li>
            <li><a className="hover:text-isro-saffron" href="https://ccmc.gsfc.nasa.gov/donki/" target="_blank" rel="noreferrer">NASA DONKI (CME Catalogue)</a></li>
            <li><a className="hover:text-isro-saffron" href="https://pradan1.issdc.gov.in/al1/" target="_blank" rel="noreferrer">ISRO PRADAN (Aditya-L1 Archive)</a></li>
          </ul>
        </div>
      </div>
      <div className="border-t border-white/10 py-4">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-white/50">
          <span>&copy; {year} Solar Flare Prediction System &middot; Content last refreshed live from NOAA/NASA every 60s</span>
          <span>Built as an independent dashboard &middot; Not an official ISRO/Government of India website</span>
        </div>
      </div>
    </footer>
  );
}
