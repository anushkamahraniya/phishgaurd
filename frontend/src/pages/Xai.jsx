import React from 'react';
import { ArrowUp, ArrowDown, GraduationCap } from 'lucide-react';
import { api } from '../api.js';
import {
  Card, PageTitle, Loading, ErrorNote, useAsync, RiskPill, ModTag, PersonPicker, reason, pct, LEVEL, levelOf,
  courseName, planStep, btn,
} from '../components/ui.jsx';

function Reason({ r }) {
  const Icon = r.up ? ArrowUp : ArrowDown;
  return (
    <li className="flex items-start gap-3">
      <span className={`mt-0.5 p-1 rounded-full ${r.up ? 'bg-high-soft text-high' : 'bg-low-soft text-low'}`}><Icon className="w-3.5 h-3.5" aria-hidden /></span>
      <span className="flex-1">
        <span className="font-medium">{r.text}</span>
        {r.detail && <span className="block text-xs text-muted">{r.detail}</span>}
      </span>
    </li>
  );
}

export default function Xai({ version, empId, setEmpId, go }) {
  const ex = useAsync(() => api.explain(empId), [empId, version]);
  const e = ex.data;
  const reasons = e ? e.contributions.map(reason) : [];
  const bad = reasons.filter((r) => r.up && r.points >= 0.5).slice(0, 3);
  const good = reasons.filter((r) => !r.up && r.points >= 0.5).slice(0, 2);
  const steps = e ? e.counterfactuals.filter((c) => c.delta < -0.5).slice(0, 3) : [];
  const first = e?.employee.name.split(' ')[0];

  return (
    <div className="space-y-6">
      <PageTitle title="Why at risk?" sub="Pick a person to see what’s behind their score">
        <PersonPicker onPick={setEmpId} />
      </PageTitle>

      {ex.loading && !e && <Loading />}
      <ErrorNote error={ex.error} />
      {e && (
        <>
          <div className="bg-white border border-line rounded-xl p-5 flex flex-wrap items-center gap-5">
            <div className={`text-5xl font-bold tabular ${LEVEL[e.level].text}`}>{pct(e.risk)}%</div>
            <div className="flex-1 min-w-[12rem]">
              <p className="text-lg font-semibold">{e.employee.name}</p>
              <p className="text-sm text-muted">{e.employee.dept}</p>
            </div>
            <RiskPill level={e.level} />
          </div>

          <div className="grid md:grid-cols-3 gap-5">
            <Card title="What is happening?">
              <p className="text-sm leading-relaxed">
                {first} would likely fall for <strong>{pct(e.risk)} in 100</strong> phishing messages.
              </p>
              <p className="text-sm text-muted mt-3">Weakest spot</p>
              <p className="font-medium mt-0.5"><ModTag m={e.employee.weakness} /></p>
              {e.employee.flagged && <p className="mt-3 p-2 rounded-lg bg-high-soft text-high text-sm font-medium">Fell for a phish in the quiz</p>}
            </Card>

            <Card title="Why?">
              <ul className="space-y-3 text-sm">
                {bad.map((r) => <Reason key={r.text} r={r} />)}
                {good.map((r) => <Reason key={r.text} r={r} />)}
                {!bad.length && !good.length && <li className="text-muted">Nothing stands out.</li>}
              </ul>
            </Card>

            <Card title="What should we do next?">
              <p className="text-sm text-muted">Best course</p>
              <p className="font-semibold mt-0.5">{courseName(e.recommendation.module)}</p>
              {steps.length > 0 && (
                <ul className="mt-4 space-y-2 text-sm">
                  {steps.map((s) => (
                    <li key={s.change} className="flex justify-between gap-2">
                      <span>{planStep(s.change)}</span>
                      <span className={`${LEVEL[levelOf(s.risk)].text} font-semibold tabular whitespace-nowrap`}>→ {pct(s.risk)}%</span>
                    </li>
                  ))}
                </ul>
              )}
              <button onClick={() => go('quiz', e.employee.id)} className={`${btn.primary} mt-5 w-full justify-center`}>
                <GraduationCap className="w-4 h-4" aria-hidden /> Start training
              </button>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
