import React, { useEffect, useRef, useState } from 'react';
import { Play, Square, Paperclip, PhoneIncoming, Lock, LockOpen, HardDrive } from 'lucide-react';

function splitSender(s = '') {
  const m = s.match(/^(.*?)\s*<(.+)>$/);
  return m ? { name: m[1], addr: m[2] } : { name: s, addr: '' };
}

function EmailPreview({ sender, subject, body, cta }) {
  const { name, addr } = splitSender(sender);
  return (
    <div className="bg-white border border-line rounded-xl p-4 space-y-3 text-left">
      <p className="font-semibold">{subject}</p>
      <div className="flex items-center gap-3 text-sm">
        <span className="w-8 h-8 rounded-full bg-page grid place-items-center font-semibold shrink-0">{(name || '?').trim()[0]}</span>
        <p className="min-w-0 truncate">{name} <span className="text-muted">&lt;{addr}&gt;</span></p>
      </div>
      <div className="text-sm leading-relaxed space-y-2">
        {(body || '').split('\n').map((p, i) => <p key={i}>{p}</p>)}
      </div>
      {cta && <span className="inline-block px-4 py-2 bg-[#2563eb] text-white rounded text-xs font-semibold">{cta}</span>}
    </div>
  );
}

function ImageAttachment({ kind = 'qr-invoice', caption }) {
  return (
    <figure className="border border-dashed border-line rounded-xl p-3 bg-page">
      {kind === 'quota' ? (
        <div className="rounded-md bg-white p-4 max-w-xs mx-auto shadow-sm">
          <div className="flex items-center gap-2 text-sm font-semibold"><HardDrive className="w-4 h-4 text-[#2563eb]" aria-hidden /> Mailbox storage</div>
          <p className="text-xs text-muted mt-1">99.8 GB of 100 GB used</p>
          <div className="h-2 rounded-full bg-line mt-2 overflow-hidden"><div className="h-full bg-high" style={{ width: '99.8%' }} /></div>
          <span className="inline-block mt-3 px-3 py-1.5 bg-[#2563eb] text-white text-xs font-semibold rounded">Expand quota</span>
        </div>
      ) : (
        <div className="rounded-md bg-white p-4 max-w-xs mx-auto shadow-sm grid grid-cols-[1fr_auto] gap-3 items-center">
          <div>
            <p className="text-[10px] font-mono uppercase text-muted">Invoice #88294</p>
            <p className="text-lg font-bold">€4,812.00</p>
            <p className="text-xs font-semibold text-high">OVERDUE, pay within 24 h</p>
            <p className="text-[10px] text-muted mt-2">Scan to pay</p>
          </div>
          <img src="/api/sim/qr.png?c=preview" alt="QR code" className="w-24 h-24" />
        </div>
      )}
      <figcaption className="text-xs text-muted mt-2 flex items-center gap-1.5"><Paperclip className="w-3 h-3" aria-hidden /> {caption || 'Image attachment'}</figcaption>
    </figure>
  );
}

function UrlCard({ url }) {
  let parts = null;
  try {
    const u = new URL(url);
    parts = { scheme: u.protocol.replace(':', ''), host: u.hostname, rest: u.pathname + u.search };
  } catch { /* shown raw below */ }
  return (
    <div className="flex items-center gap-2 bg-white border border-line rounded-xl px-3 py-3 font-mono text-sm break-all">
      {parts?.scheme === 'https' ? <Lock className="w-4 h-4 text-muted shrink-0" aria-label="Secure" /> : <LockOpen className="w-4 h-4 text-mid-ink shrink-0" aria-label="Not secure" />}
      {parts ? (
        <span><span className="text-muted">{parts.scheme}://</span><strong>{parts.host}</strong><span className="text-muted">{parts.rest}</span></span>
      ) : url}
    </div>
  );
}

function useSpeech() {
  const [playing, setPlaying] = useState(false);
  const supported = typeof window !== 'undefined' && 'speechSynthesis' in window;
  useEffect(() => () => supported && window.speechSynthesis.cancel(), [supported]);
  const play = (text) => {
    if (!supported) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    const voices = window.speechSynthesis.getVoices();
    const v = voices.find((x) => /en-GB/i.test(x.lang)) || voices.find((x) => /^en/i.test(x.lang));
    if (v) u.voice = v;
    u.onend = () => setPlaying(false);
    u.onerror = () => setPlaying(false);
    setPlaying(true);
    window.speechSynthesis.speak(u);
  };
  const stop = () => { if (supported) window.speechSynthesis.cancel(); setPlaying(false); };
  return { playing, play, stop, supported };
}

function Voicemail({ script, caller }) {
  const { playing, play, stop, supported } = useSpeech();
  const bars = useRef(Array.from({ length: 32 }, (_, i) => 0.3 + Math.abs(Math.sin(i * 1.7)) * 0.7)).current;
  return (
    <div className="bg-white border border-line rounded-xl p-4 space-y-3">
      <p className="text-sm text-muted flex items-center gap-2"><PhoneIncoming className="w-4 h-4" aria-hidden /> Voicemail from <span className="text-ink font-medium">{caller}</span></p>
      <div className="flex items-center gap-3">
        <button type="button" onClick={() => (playing ? stop() : play(script))} disabled={!supported}
          aria-label={playing ? 'Stop' : 'Play voicemail'} className="p-2.5 bg-ink text-white rounded-full disabled:opacity-40 shrink-0">
          {playing ? <Square className="w-4 h-4 fill-white" /> : <Play className="w-4 h-4 fill-white" />}
        </button>
        <div className="flex items-center gap-[3px] h-6 flex-1" aria-hidden>
          {bars.map((h, i) => (
            <span key={i} className={`w-[3px] rounded-full ${playing ? 'bg-ink wave-bar' : 'bg-line'}`}
              style={{ height: `${h * 100}%`, animationDelay: `${(i % 9) * 0.08}s` }} />
          ))}
        </div>
      </div>
      <blockquote className="text-sm italic leading-relaxed text-muted">“{script}”</blockquote>
    </div>
  );
}

export function Artifact({ a }) {
  if (!a) return null;
  if (a.type === 'email') return <EmailPreview sender={a.sender} subject={a.subject} body={a.body} cta={a.cta} />;
  if (a.type === 'url') return <UrlCard url={a.url} />;
  if (a.type === 'image') return <ImageAttachment kind={a.image} caption={a.caption} />;
  if (a.type === 'call') return <Voicemail script={a.transcript} caller={a.caller} />;
  return null;
}
