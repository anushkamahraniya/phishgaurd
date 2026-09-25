import React, { useEffect, useState } from 'react';
import { LayoutDashboard, Users, HelpCircle, Fish, ShieldCheck, RotateCcw, ScanSearch } from 'lucide-react';
import Dashboard from './pages/Dashboard.jsx';
import Employees from './pages/Employees.jsx';
import Xai from './pages/Xai.jsx';
import Training from './pages/Training.jsx';
import Check from './pages/Check.jsx';
import { api } from './api.js';

const NAV = [
  { id: 'check', label: 'Is it a scam?', Icon: ScanSearch },
  { id: 'overview', label: 'Overview', Icon: LayoutDashboard },
  { id: 'people', label: 'People', Icon: Users },
  { id: 'why', label: 'Why at risk?', Icon: HelpCircle },
  { id: 'quiz', label: 'Spot the phish', Icon: Fish },
];

// The URL hash holds the page and person (#/why/EMP-147), so a refresh keeps your place.
function readHash() {
  const [, tab, id] = window.location.hash.split('/');
  return { tab: NAV.some((n) => n.id === tab) ? tab : 'check', id: id || 'EMP-101' };
}

export default function App() {
  const [{ tab, id: empId }, setRoute] = useState(readHash);
  const [version, setVersion] = useState(0); // bump after anything that changes server state
  const [resetting, setResetting] = useState(false);

  useEffect(() => {
    const on = () => setRoute(readHash());
    window.addEventListener('hashchange', on);
    return () => window.removeEventListener('hashchange', on);
  }, []);

  const go = (t, id = empId) => { window.location.hash = `/${t}/${id}`; window.scrollTo(0, 0); };
  const setEmpId = (id) => go(tab, id);
  const changed = () => setVersion((v) => v + 1);

  const reset = async () => {
    if (!window.confirm('Reset all demo data to the start?')) return;
    setResetting(true);
    try { await api.reset(); changed(); } finally { setResetting(false); }
  };

  const props = { version, changed, go, empId, setEmpId };

  return (
    <div className="min-h-screen flex flex-col md:flex-row">
      <aside className="md:w-56 bg-ink text-white p-4 flex md:flex-col gap-4 md:justify-between shrink-0 md:sticky md:top-0 md:h-screen overflow-x-auto">
        <div className="flex md:flex-col gap-4 md:gap-6 items-center md:items-stretch">
          <h1 className="flex items-center gap-2 font-bold text-lg px-2 md:pt-2 whitespace-nowrap">
            <ShieldCheck className="w-6 h-6" aria-hidden /> PhishGuard
          </h1>
          <nav className="flex md:flex-col gap-1" aria-label="Pages">
            {NAV.map((n) => (
              <button key={n.id} onClick={() => go(n.id)} aria-current={tab === n.id ? 'page' : undefined}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium whitespace-nowrap transition ${
                  tab === n.id ? 'bg-white text-ink' : 'text-white/70 hover:text-white hover:bg-white/10'}`}>
                <n.Icon className="w-4 h-4" aria-hidden /> {n.label}
              </button>
            ))}
          </nav>
        </div>
        <button onClick={reset} disabled={resetting}
          className="hidden md:flex items-center gap-2 px-3 py-2 text-xs text-white/50 hover:text-white disabled:opacity-50">
          <RotateCcw className={`w-3.5 h-3.5 ${resetting ? 'animate-spin' : ''}`} aria-hidden /> Reset demo data
        </button>
      </aside>

      <main className="flex-1 min-w-0 p-4 md:p-8 max-w-6xl">
        {tab === 'check' && <Check />}
        {tab === 'overview' && <Dashboard {...props} />}
        {tab === 'people' && <Employees {...props} />}
        {tab === 'why' && <Xai {...props} />}
        {tab === 'quiz' && <Training {...props} />}
      </main>
    </div>
  );
}
