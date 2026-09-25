import React from 'react';
import { ChevronRight } from 'lucide-react';
import { api } from '../api.js';
import { Card, PageTitle, Loading, ErrorNote, useAsync, RiskPill, ModTag, timeAgo, btn } from '../components/ui.jsx';

function Stat({ label, value, sub, tone }) {
  return (
    <div className={`rounded-xl p-5 ${tone}`}>
      <p className="text-sm font-medium opacity-80">{label}</p>
      <p className="text-3xl font-bold mt-1 tabular">{value}</p>
      {sub && <p className="text-xs mt-1 opacity-70">{sub}</p>}
    </div>
  );
}

const ONE = { text: 'email', image: 'QR code', url: 'link', audio: 'phone call' };
const STATUS = {
  Clicked: ['fell for', 'text-high'],
  Reported: ['reported', 'text-low'],
  Ignored: ['ignored', 'text-muted'],
  'Passed training': ['passed training', 'text-low'],
  'Failed quiz': ['failed the quiz', 'text-high'],
};

export default function Dashboard({ version, go }) {
  const { data, error, loading } = useAsync(() => api.dashboard(), [version]);
  if (loading && !data) return <Loading />;
  if (error) return <ErrorNote error={error} />;
  const k = data.kpis;
  const byRate = [...data.modality].sort((a, b) => b.fail_rate - a.fail_rate);
  const maxRate = byRate[0].fail_rate || 1;

  return (
    <div className="space-y-6">
      <PageTitle title="Overview" sub={`${k.staff.toLocaleString()} people tested with safe, fake phishing messages`} />

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Stat label="High risk" value={k.high_risk} sub="Likely to fall for a real attack" tone="bg-high text-white" />
        <Stat label="Watch" value={k.medium_risk} sub="Could go either way" tone="bg-mid text-ink" />
        <Stat label="Safe" value={k.low_risk} sub="Spot most phishing" tone="bg-low text-white" />
      </div>

      <div className="grid lg:grid-cols-5 gap-6">
        <Card className="lg:col-span-3" title="Needs attention"
          action={<button onClick={() => go('people')} className="text-sm text-muted hover:text-ink flex items-center gap-1">See all <ChevronRight className="w-4 h-4" aria-hidden /></button>}>
          <ul className="divide-y divide-line">
            {data.attention.map((e) => (
              <li key={e.id} className="flex flex-wrap items-center gap-3 py-2.5">
                <div className="flex-1 min-w-[10rem]">
                  <p className="font-medium">{e.name}</p>
                  <p className="text-xs text-muted">{e.dept}{e.flagged && <span className="text-high font-semibold"> · Failed the quiz</span>}</p>
                </div>
                <RiskPill risk={e.risk} level={e.level} />
                <div className="flex gap-1.5">
                  <button onClick={() => go('why', e.id)} className={btn.ghost}>Why?</button>
                  <button onClick={() => go('quiz', e.id)} className={btn.ghost}>Train</button>
                </div>
              </li>
            ))}
          </ul>
        </Card>

        <Card className="lg:col-span-2" title="What fools people most">
          <ul className="space-y-4">
            {byRate.map((m) => (
              <li key={m.modality}>
                <div className="flex justify-between text-sm mb-1"><ModTag m={m.modality} /><span className="font-semibold tabular">{Math.round(m.fail_rate)}%</span></div>
                <div className="h-2.5 rounded-full bg-page overflow-hidden">
                  <div className="h-full rounded-full bg-ink" style={{ width: `${(m.fail_rate / maxRate) * 100}%` }} />
                </div>
              </li>
            ))}
          </ul>
          <p className="text-xs text-muted mt-4">Share of fake messages that got clicked.</p>
        </Card>
      </div>

      <Card title="Recent activity">
        <ul className="space-y-2 text-sm">
          {data.activity.slice(0, 6).map((e) => {
            const [verb, tone] = STATUS[e.status] || [e.status.toLowerCase(), 'text-muted'];
            const what = ONE[e.modality] ? ` a fake ${ONE[e.modality]}` : '';
            return (
              <li key={e.id} className="flex justify-between gap-3">
                <span><button onClick={() => go('why', e.emp_id)} className="font-medium hover:underline">{e.emp}</button> <span className={tone}>{verb}</span>{what}</span>
                <span className="text-muted whitespace-nowrap">{timeAgo(e.at)}</span>
              </li>
            );
          })}
        </ul>
      </Card>
    </div>
  );
}
