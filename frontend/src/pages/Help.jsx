import React from 'react';
import { BarChart3, Zap, Users, BookOpen, HelpCircle } from 'lucide-react';
import { PageHeader, Panel, GLOSSARY, RiskLegend } from '../components/ui.jsx';

const GUIDE = [
  { tab: 'dashboard', Icon: BarChart3, title: 'Executive Dashboard', who: 'Security managers',
    points: ['See the organisation’s overall risk and how it has changed week by week.',
      'Find which attack type (email, image/QR, link, voice) fools people most.',
      'Spot the riskiest departments and people, and follow the live activity feed.'] },
  { tab: 'xai', Icon: Zap, title: 'ML & XAI Risk Engine', who: 'Analysts and anyone curious about the AI',
    points: ['Pick an employee to see why the model gave them their score, one behaviour at a time.',
      'Use the sliders to invent an employee and watch the model re-score them live.',
      'See which behaviours matter most across the company, and how accurate the model is.'] },
  { tab: 'employees', Icon: Users, title: 'Employee Directory', who: 'Security and HR teams',
    points: ['Search and filter all 1,248 employees by department, risk level or weakest area.',
      'Press “Auto-assign adaptive training” to give each at-risk person the module that fixes their biggest risk factor.',
      'Use “Explain” to see why someone is risky, or “Remediate” to open their training.'] },
  { tab: 'training', Icon: BookOpen, title: 'Training Portal', who: 'Employees',
    points: ['Read three quick habits tailored to your weakest area.',
      'Practise on 5 realistic examples, with instant feedback after each answer.',
      'See your score, your new risk score, what improved and what to do next.'] },
];

export default function Help({ go }) {
  return (
    <div className="space-y-6">
      <PageHeader title="Help & glossary" subtitle="What each page does, and what the technical words mean" />
      <Panel icon={HelpCircle} title="PhishGuard in one sentence">
        <p className="text-sm text-slate-300 leading-relaxed max-w-3xl">
          PhishGuard sends safe, fake phishing tests, uses machine learning to predict who is most likely to fall for a real attack,
          explains each prediction in plain terms with explainable AI (SHAP), and gives every person short training aimed at their own weak spot.
        </p>
        <div className="mt-3"><RiskLegend /></div>
      </Panel>
      <div className="grid md:grid-cols-2 gap-6">
        {GUIDE.map((g) => (
          <Panel key={g.tab} icon={g.Icon} title={g.title} subtitle={`For: ${g.who}`}
            action={<button onClick={() => go(g.tab)} className="text-xs text-cyan-400 hover:text-cyan-300">Open →</button>}>
            <ul className="space-y-1.5 text-[13px] text-slate-300 list-disc pl-5">
              {g.points.map((p) => <li key={p}>{p}</li>)}
            </ul>
          </Panel>
        ))}
      </div>
      <Panel title="Glossary">
        <dl className="grid md:grid-cols-2 gap-x-8 gap-y-3">
          {Object.entries(GLOSSARY).map(([k, v]) => (
            <div key={k}>
              <dt className="text-sm font-semibold text-cyan-300">{k}</dt>
              <dd className="text-[13px] text-slate-400 leading-relaxed">{v}</dd>
            </div>
          ))}
        </dl>
      </Panel>
    </div>
  );
}
