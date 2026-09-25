import React, { useEffect, useRef, useState } from 'react';
import { Mail, Image as ImageIcon, Link as LinkIcon, Phone, Loader2, Search } from 'lucide-react';
import { api } from '../api.js';

export const MODALITIES = ['text', 'image', 'url', 'audio'];
export const MOD = {
  text: { label: 'Emails', Icon: Mail },
  image: { label: 'Images & QR codes', Icon: ImageIcon },
  url: { label: 'Links', Icon: LinkIcon },
  audio: { label: 'Phone calls', Icon: Phone },
};

// Scores come from a probability, so 99.9 would round up to a misleading "100".
export const pct = (v) => Math.floor(v);

export const LEVEL = {
  High: { label: 'High risk', text: 'text-high', pill: 'bg-high-soft text-high', dot: 'bg-high', hex: '#C04C36' },
  Medium: { label: 'Watch', text: 'text-mid-ink', pill: 'bg-mid-soft text-mid-ink', dot: 'bg-mid', hex: '#E6A65D' },
  Low: { label: 'Safe', text: 'text-low', pill: 'bg-low-soft text-low', dot: 'bg-low', hex: '#40814B' },
};
export const levelOf = (v) => (v >= 60 ? 'High' : v >= 30 ? 'Medium' : 'Low');

export function RiskPill({ risk, level }) {
  const l = LEVEL[level || levelOf(risk)];
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold whitespace-nowrap ${l.pill}`}>
      <i className={`w-1.5 h-1.5 rounded-full ${l.dot}`} /> {l.label}
      {risk !== undefined && <span className="tabular opacity-80">{pct(risk)}%</span>}
    </span>
  );
}

export function ModTag({ m }) {
  const d = MOD[m] || MOD.text;
  return <span className="inline-flex items-center gap-1.5"><d.Icon className="w-3.5 h-3.5 text-muted" aria-hidden />{d.label}</span>;
}

export function Card({ title, action, children, className = '' }) {
  return (
    <section className={`bg-white border border-line rounded-xl p-5 ${className}`}>
      {(title || action) && (
        <header className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <h3 className="text-base font-semibold">{title}</h3>
          {action}
        </header>
      )}
      {children}
    </section>
  );
}

export function PageTitle({ title, sub, children }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">{title}</h2>
        {sub && <p className="text-sm text-muted mt-1">{sub}</p>}
      </div>
      {children}
    </div>
  );
}

export const btn = {
  primary: 'px-4 py-2 rounded-lg bg-ink text-white text-sm font-semibold hover:bg-ink/90 disabled:opacity-40 inline-flex items-center gap-2',
  ghost: 'px-3 py-1.5 rounded-lg border border-line bg-white text-sm font-medium hover:bg-page disabled:opacity-40 inline-flex items-center gap-1.5',
};

export function Loading({ label = 'Loading' }) {
  return (
    <div className="flex items-center gap-2 text-sm text-muted py-10 justify-center">
      <Loader2 className="w-4 h-4 animate-spin" aria-hidden /> {label}…
    </div>
  );
}

export function ErrorNote({ error }) {
  if (!error) return null;
  const offline = error instanceof TypeError; // fetch itself failed: the server isn't reachable
  return (
    <div className="p-3 rounded-lg bg-high-soft text-high text-sm">
      {offline ? 'Can’t reach the server. Run start.bat, then refresh.' : String(error.message || error)}
    </div>
  );
}

export function useAsync(fn, deps) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  useEffect(() => {
    let live = true;
    setState((s) => ({ ...s, loading: true }));
    fn().then(
      (data) => live && setState({ data, error: null, loading: false }),
      (error) => live && setState({ data: null, error, loading: false }),
    );
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return state;
}

export function timeAgo(ts) {
  const s = Math.max(0, Date.now() / 1000 - ts);
  if (s < 60) return 'just now';
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return `${Math.floor(s / 86400)} d ago`;
}

/** Search box that finds a person by name (or ID) and calls onPick(id). */
export function PersonPicker({ onPick, placeholder = 'Search a person by name…' }) {
  const [q, setQ] = useState('');
  const [hits, setHits] = useState([]);
  const [open, setOpen] = useState(false);
  const box = useRef();

  useEffect(() => {
    if (!q.trim()) { setHits([]); return; }
    let live = true;
    const t = setTimeout(() => api.employees({ search: q.trim(), size: 6 }).then((d) => live && setHits(d.rows), () => {}), 150);
    return () => { live = false; clearTimeout(t); };
  }, [q]);

  useEffect(() => {
    const close = (e) => { if (box.current && !box.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, []);

  const pick = (id) => { onPick(id); setQ(''); setOpen(false); };

  return (
    <div ref={box} className="relative w-full sm:w-72">
      <Search className="w-4 h-4 text-muted absolute left-3 top-2.5" aria-hidden />
      <input value={q} onChange={(e) => { setQ(e.target.value); setOpen(true); }} onFocus={() => setOpen(true)}
        onKeyDown={(e) => { if (e.key === 'Enter' && hits[0]) pick(hits[0].id); if (e.key === 'Escape') setOpen(false); }}
        placeholder={placeholder} aria-label="Find a person"
        className="w-full pl-9 pr-3 py-2 bg-white border border-line rounded-lg text-sm focus:outline-none focus:border-ink" />
      {open && q.trim() && (
        <ul className="absolute z-20 mt-1 w-full bg-white border border-line rounded-lg shadow-lg overflow-hidden">
          {hits.length ? hits.map((h) => (
            <li key={h.id}>
              <button onClick={() => pick(h.id)} className="w-full flex items-center justify-between gap-2 px-3 py-2 text-sm text-left hover:bg-page">
                <span className="truncate">{h.name} <span className="text-muted text-xs">· {h.dept}</span></span>
                <RiskPill risk={h.risk} level={h.level} />
              </button>
            </li>
          )) : <li className="px-3 py-2 text-sm text-muted">No one found</li>}
        </ul>
      )}
    </div>
  );
}

// ------------------------------------------------ plain-English names
const COURSES = {
  'URL Typosquatting & SSL Spoofing': 'Spotting fake links',
  'Urgency & Pretext Email Scams': 'Spotting scam emails',
  'QR Code & Visual Brand Spoofing': 'Fake QR codes and images',
  'Deepfake Voice & Vishing Defense': 'Scam phone calls',
  'Pause Before You Click': 'Pause before you click',
  'Report It: Using the Phish Alert Button': 'How to report phishing',
  'Security Awareness Refresher': 'Security refresher',
  'Set Up Multi-Factor Authentication': 'Turn on two-step login',
};
export const courseName = (m) => COURSES[m] || m;

/** Rewords the model's what-if suggestions. */
export function planStep(change) {
  if (change.startsWith('Complete')) return 'Finish one training course';
  if (change.startsWith('Report')) return 'Report more suspicious messages';
  if (change.startsWith('Take')) return 'Slow down before clicking';
  if (change.startsWith('Enable MFA')) return 'Turn on two-step login';
  const m = change.match(/^Halve the (\w+) failure rate/);
  if (m) return `Fall for half as many fake ${{ Text: 'emails', Image: 'QR codes', URL: 'links', Audio: 'calls' }[m[1]] || 'messages'}`;
  return change;
}

// ------------------------------------------------ plain-English risk reasons
const REASONS = {
  url_fail_rate: ['Clicks fake links', 'Spots fake links', '%'],
  text_fail_rate: ['Falls for scam emails', 'Spots scam emails', '%'],
  image_fail_rate: ['Trusts fake images and QR codes', 'Spots fake images and QR codes', '%'],
  audio_fail_rate: ['Trusts scam phone calls', 'Spots scam phone calls', '%'],
  avg_response_sec: ['Clicks very quickly', 'Takes time before clicking', 's'],
  report_rate: ['Rarely reports suspicious messages', 'Reports suspicious messages', '%r'],
  training_completed: ['Has done little training', 'Has done training', 'n'],
  days_since_training: ['Training is out of date', 'Trained recently', 'd'],
  mfa_enabled: ['No two-step login', 'Uses two-step login', ''],
  after_hours_pct: ['Often reads mail late at night', 'Reads mail in work hours', '%h'],
  seniority: ['Senior role, a bigger target', 'Junior role, a smaller target', ''],
  tenure_years: ['New to the company', 'Long time at the company', 'y'],
};

function detail(c, u) {
  const v = Math.round(c.value);
  return {
    '%': `fell for ${v}% of tests`, s: `in ${v} seconds on average`, '%r': `reports ${v}% of them`,
    n: `${v} course${v === 1 ? '' : 's'} done`, d: `${v} days ago`, '%h': `${v}% after hours`, y: `${Math.round(c.value * 10) / 10} years`,
  }[u] || '';
}

/** Turns one model contribution into { text, detail, up, points }. */
export function reason(c) {
  const [bad, good, u] = REASONS[c.feature] || [c.label, c.label, ''];
  const up = c.shap > 0;
  return { text: up ? bad : good, detail: detail(c, u), up, points: Math.abs(c.shap) };
}
