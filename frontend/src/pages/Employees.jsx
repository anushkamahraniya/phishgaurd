import React, { useEffect, useState } from 'react';
import { Search, ChevronLeft, ChevronRight, Wand2 } from 'lucide-react';
import { api } from '../api.js';
import { PageTitle, Loading, ErrorNote, RiskPill, ModTag, btn } from '../components/ui.jsx';

const FILTERS = [
  ['All', 'Everyone'], ['Attention', 'Needs attention'], ['High', 'High risk'], ['Medium', 'Watch'], ['Low', 'Safe'],
];

export default function Employees({ version, changed, go }) {
  const [q, setQ] = useState('');
  const [level, setLevel] = useState('All');
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [assigning, setAssigning] = useState(false);
  const [toast, setToast] = useState(null);

  useEffect(() => { setPage(1); }, [q, level]);
  useEffect(() => {
    let live = true;
    const t = setTimeout(() => {
      api.employees({ search: q, level, page, size: 20 })
        .then((d) => { if (live) { setData(d); setErr(null); } }, (e) => live && setErr(e));
    }, 150);
    return () => { live = false; clearTimeout(t); };
  }, [q, level, page, version]);

  const assign = async () => {
    setAssigning(true);
    try {
      const r = await api.autoAssign();
      setToast(r.assigned ? `Training assigned to ${r.assigned} people.` : 'Everyone at risk already has training.');
      changed();
    } catch (e) { setErr(e); } finally { setAssigning(false); }
  };

  const pages = data ? Math.max(1, Math.ceil(data.total / data.size)) : 1;

  return (
    <div className="space-y-5">
      <PageTitle title="People" sub={data && `${data.total.toLocaleString()} shown`}>
        <button onClick={assign} disabled={assigning} className={btn.primary}>
          <Wand2 className="w-4 h-4" aria-hidden /> {assigning ? 'Assigning…' : 'Assign training to at-risk people'}
        </button>
      </PageTitle>

      {toast && <p className="p-3 rounded-lg bg-low-soft text-low text-sm font-medium animate-fade-in">{toast}</p>}

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative">
          <Search className="w-4 h-4 text-muted absolute left-3 top-2.5" aria-hidden />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by name…" aria-label="Search by name"
            className="pl-9 pr-3 py-2 bg-white border border-line rounded-lg text-sm focus:outline-none focus:border-ink w-60" />
        </div>
        {FILTERS.map(([v, l]) => (
          <button key={v} onClick={() => setLevel(v)} aria-pressed={level === v}
            className={`px-3 py-1.5 rounded-full text-sm border transition ${level === v ? 'bg-ink text-white border-ink' : 'bg-white border-line hover:bg-page'}`}>
            {l}
          </button>
        ))}
      </div>

      <ErrorNote error={err} />
      {!data ? <Loading /> : (
        <div className="bg-white border border-line rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left min-w-[720px]">
              <thead className="text-xs text-muted border-b border-line">
                <tr>{['Name', 'Risk', 'Weakest spot', 'Training', ''].map((h) => <th key={h} className="px-4 py-3 font-medium">{h}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-line">
                {data.rows.map((e) => (
                  <tr key={e.id} className="hover:bg-page/60">
                    <td className="px-4 py-3">
                      <p className="font-medium">{e.name}</p>
                      <p className="text-xs text-muted">{e.dept}{e.flagged && <span className="text-high font-semibold"> · Failed the quiz</span>}</p>
                    </td>
                    <td className="px-4 py-3"><RiskPill risk={e.risk} level={e.level} /></td>
                    <td className="px-4 py-3"><ModTag m={e.weakness} /></td>
                    <td className="px-4 py-3">
                      {!e.assigned_module ? <span className="text-muted">None</span>
                        : e.completed ? <span className="text-low font-medium">Done</span>
                        : <span className="text-mid-ink font-medium">To do</span>}
                    </td>
                    <td className="px-4 py-3 text-right whitespace-nowrap space-x-1.5">
                      <button onClick={() => go('why', e.id)} className={btn.ghost}>Why?</button>
                      <button onClick={() => go('quiz', e.id)} className={btn.ghost}>Train</button>
                    </td>
                  </tr>
                ))}
                {!data.rows.length && <tr><td colSpan={5} className="p-8 text-center text-muted">No one matches.</td></tr>}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-between px-4 py-3 border-t border-line text-sm text-muted">
            <span className="tabular">Page {page} of {pages}</span>
            <div className="flex gap-2">
              <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)} className={btn.ghost} aria-label="Previous page"><ChevronLeft className="w-4 h-4" /></button>
              <button disabled={page >= pages} onClick={() => setPage((p) => p + 1)} className={btn.ghost} aria-label="Next page"><ChevronRight className="w-4 h-4" /></button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
