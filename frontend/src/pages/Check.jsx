import React, { useRef, useState } from 'react';
import { ShieldAlert, AlertTriangle, ShieldCheck, HelpCircle, Upload, Loader2, X } from 'lucide-react';
import { api } from '../api.js';
import { PageTitle, ErrorNote, btn } from '../components/ui.jsx';

const LOOK = {
  fraud: { Icon: ShieldAlert, box: 'bg-high text-white' },
  careful: { Icon: AlertTriangle, box: 'bg-mid text-ink' },
  safe: { Icon: ShieldCheck, box: 'bg-low text-white' },
  unknown: { Icon: HelpCircle, box: 'bg-white border border-line text-ink' },
};

const EXAMPLES = [
  ['Scam text', 'URGENT: Your parcel is on hold. Pay the Rs 25 fee within 12 hours: http://indiapost-redelivery.top/pay'],
  ['Scam link', 'http://paypa1-account-verify.com/signin'],
  ['Normal text', 'Hey, are we still on for lunch tomorrow at 1? Let me know.'],
];

function Result({ r }) {
  const { Icon, box } = LOOK[r.verdict] || LOOK.unknown;
  return (
    <div className={`rounded-xl p-6 animate-fade-in ${box}`} role="status">
      <p className="flex items-center gap-3 text-2xl font-bold"><Icon className="w-8 h-8 shrink-0" aria-hidden /> {r.title}</p>
      <ul className="mt-4 space-y-1.5 text-[15px]">
        {r.reasons.map((x) => <li key={x} className="flex gap-2"><span aria-hidden>•</span><span className="break-all sm:break-normal">{x}</span></li>)}
      </ul>
    </div>
  );
}

export default function Check() {
  const [text, setText] = useState('');
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);
  const input = useRef();

  const run = async (fn) => {
    setBusy(true); setErr(null); setResult(null);
    try { setResult(await fn()); } catch (e) { setErr(e); } finally { setBusy(false); }
  };

  const pick = (f) => {
    if (!f) return;
    setFile(f); setText('');
    setPreview(f.type.startsWith('image/') ? URL.createObjectURL(f) : null);
    run(() => api.checkFile(f));
  };

  const clearFile = () => { setFile(null); setPreview(null); setResult(null); if (input.current) input.current.value = ''; };

  const checkText = (t = text) => {
    if (!t.trim()) return;
    clearFile(); setText(t);
    run(() => api.check(t));
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <PageTitle title="Is it a scam?" sub="Paste a link or message, or upload a QR code or screenshot." />

      <div className="bg-white border border-line rounded-xl p-5 space-y-3">
        <textarea value={text} onChange={(e) => setText(e.target.value)} rows={5} aria-label="Link or message to check"
          onKeyDown={(e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) checkText(); }}
          placeholder="Paste a link, email or text message here…"
          className="w-full p-3 rounded-lg border border-line text-[15px] focus:outline-none focus:border-ink resize-y" />
        <div className="flex flex-wrap items-center gap-2">
          <button onClick={() => checkText()} disabled={!text.trim() || busy} className={btn.primary}>Check</button>
          <span className="text-sm text-muted ml-1">Try:</span>
          {EXAMPLES.map(([label, t]) => (
            <button key={label} onClick={() => checkText(t)} className="px-3 py-1 rounded-full bg-page text-sm hover:bg-line">{label}</button>
          ))}
        </div>

        <div className="flex items-center gap-3 text-sm text-muted"><span className="flex-1 h-px bg-line" /> or <span className="flex-1 h-px bg-line" /></div>

        <label
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files[0]); }}
          className={`flex flex-col items-center justify-center gap-1 p-6 rounded-lg border-2 border-dashed cursor-pointer transition ${drag ? 'border-ink bg-page' : 'border-line hover:bg-page'}`}>
          <Upload className="w-6 h-6 text-muted" aria-hidden />
          <span className="font-medium">Upload a QR code or screenshot</span>
          <span className="text-xs text-muted">PNG or JPG</span>
          <input ref={input} type="file" accept="image/*" className="sr-only" onChange={(e) => pick(e.target.files[0])} />
        </label>

        {file && (
          <div className="flex items-center gap-3 p-3 rounded-lg bg-page">
            {preview && file.type.startsWith('image/') && <img src={preview} alt="" className="w-14 h-14 object-contain rounded bg-white" />}
            <span className="text-sm truncate flex-1">{file.name}</span>
            <button onClick={clearFile} aria-label="Remove file" className="p-1 rounded hover:bg-line"><X className="w-4 h-4" /></button>
          </div>
        )}
      </div>

      {busy && <p className="flex items-center gap-2 text-muted"><Loader2 className="w-4 h-4 animate-spin" aria-hidden /> Checking…</p>}
      <ErrorNote error={err} />
      {result && <Result r={result} />}
    </div>
  );
}
