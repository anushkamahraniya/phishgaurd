import React, { useEffect, useState } from 'react';
import { CheckCircle, XCircle, ChevronRight, RotateCcw, ShieldCheck, AlertTriangle } from 'lucide-react';
import { api } from '../api.js';
import { Card, PageTitle, Loading, ErrorNote, RiskPill, PersonPicker, pct, LEVEL, levelOf, courseName, btn } from '../components/ui.jsx';
import { Artifact } from '../components/previews.jsx';

const RIGHT = 10, WRONG = -5;

function Choice({ label, sub, state, onClick, disabled }) {
  const tone = {
    right: 'border-low bg-low-soft',
    wrong: 'border-high bg-high-soft',
    idle: 'border-line bg-white hover:border-ink',
    dim: 'border-line bg-white opacity-50',
  }[state];
  return (
    <button disabled={disabled} onClick={onClick} className={`w-full text-left p-3.5 rounded-lg border-2 transition ${tone}`}>
      <span className="block text-sm font-medium">{label}</span>
      {sub && <span className="block text-xs text-muted">{sub}</span>}
    </button>
  );
}

export default function Training({ changed, empId, setEmpId, go }) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [phase, setPhase] = useState('tips'); // tips -> quiz -> done
  const [qi, setQi] = useState(0);
  const [answers, setAnswers] = useState({});
  const [feedback, setFeedback] = useState({});
  const [points, setPoints] = useState(0);
  const [startRisk, setStartRisk] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  const restart = () => { setPhase('tips'); setQi(0); setAnswers({}); setFeedback({}); setPoints(0); setResult(null); };

  const load = () => api.training(empId).then((d) => { setData(d); setStartRisk(d.employee.risk); }, setErr);
  useEffect(() => { setData(null); setErr(null); restart(); load(); /* eslint-disable-next-line */ }, [empId]);

  const q = data?.questions[qi];
  const fb = q && feedback[q.id];
  const total = data?.questions.length || 0;
  const first = data?.employee.name.split(' ')[0];

  const answer = async (v) => {
    if (fb || busy) return;
    setBusy(true);
    setAnswers((a) => ({ ...a, [q.id]: v }));
    try {
      const f = await api.checkAnswer(q.id, v, empId);
      setFeedback((s) => ({ ...s, [q.id]: f }));
      setPoints((p) => p + (f.correct ? RIGHT : WRONG));
      changed();
    } catch (e) { setErr(e); } finally { setBusy(false); }
  };

  const finish = async () => {
    setBusy(true);
    try {
      setResult(await api.submitQuiz(empId, answers));
      setPhase('done');
      changed();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (e) { setErr(e); } finally { setBusy(false); }
  };

  const retry = () => { restart(); load(); };
  const choiceState = (v) => (!fb ? 'idle' : fb.answer === v ? 'right' : answers[q.id] === v ? 'wrong' : 'dim');

  return (
    <div className="space-y-6">
      <PageTitle title="Spot the phish" sub={data ? `Taking the quiz as ${data.employee.name}` : ' '}>
        <PersonPicker onPick={setEmpId} placeholder="Switch person…" />
      </PageTitle>

      <ErrorNote error={err} />
      {!data && !err && <Loading />}

      {data && (
        <>
          <div className="bg-white border border-line rounded-xl px-5 py-4 flex flex-wrap items-center gap-4">
            <p className="flex-1 font-semibold">{data.employee.name}</p>
            <RiskPill risk={data.employee.risk} level={data.employee.level} />
            <p className="text-sm">Points <span className={`font-bold tabular ${points < 0 ? 'text-high' : 'text-low'}`}>{points}</span></p>
          </div>

          {phase === 'tips' && (
            <Card title={courseName(data.module.name)}>
              <ul className="grid md:grid-cols-3 gap-4">
                {data.module.tips.map((t) => (
                  <li key={t.title} className="p-4 rounded-lg bg-page">
                    <p className="font-semibold flex items-center gap-2"><ShieldCheck className="w-4 h-4 text-low shrink-0" aria-hidden /> {t.title}</p>
                    <p className="text-sm text-muted mt-1.5 leading-relaxed">{t.body}</p>
                  </li>
                ))}
              </ul>
              <button onClick={() => setPhase('quiz')} className={`${btn.primary} mt-5`}>Start the quiz <ChevronRight className="w-4 h-4" aria-hidden /></button>
            </Card>
          )}

          {phase === 'quiz' && q && (
            <Card title={`Question ${qi + 1} of ${total}`}
              action={
                <div className="flex gap-1" aria-hidden>
                  {data.questions.map((qq, i) => {
                    const f = feedback[qq.id];
                    return <span key={qq.id} className={`w-6 h-1.5 rounded-full ${f ? (f.correct ? 'bg-low' : 'bg-high') : i === qi ? 'bg-ink' : 'bg-line'}`} />;
                  })}
                </div>
              }>
              <div className="grid lg:grid-cols-2 gap-6">
                <Artifact a={q.artifact} />
                <div className="space-y-3">
                  <p className="font-medium">{q.prompt}</p>
                  {q.kind === 'verdict' ? (
                    <div className="grid grid-cols-2 gap-2">
                      <Choice label="Phishing" sub="It’s a scam" state={choiceState('phish')} disabled={!!fb || busy} onClick={() => answer('phish')} />
                      <Choice label="Safe" sub="It’s real" state={choiceState('legit')} disabled={!!fb || busy} onClick={() => answer('legit')} />
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {q.options.map((o) => (
                        <Choice key={o.id} label={o.text} state={choiceState(o.id)} disabled={!!fb || busy} onClick={() => answer(o.id)} />
                      ))}
                    </div>
                  )}

                  {fb && (
                    <div className={`p-4 rounded-lg text-sm leading-relaxed animate-fade-in ${fb.correct ? 'bg-low text-white' : 'bg-high text-white'}`}>
                      <p className="font-bold flex items-center gap-2 mb-1">
                        {fb.correct ? <CheckCircle className="w-4 h-4" aria-hidden /> : <XCircle className="w-4 h-4" aria-hidden />}
                        {fb.correct ? `Correct! +${RIGHT} points` : `You fell for it. ${WRONG} points`}
                      </p>
                      <p>{fb.explain}</p>
                      {!fb.correct && (
                        <p className="mt-2 flex items-center gap-1.5 font-semibold"><AlertTriangle className="w-4 h-4" aria-hidden /> {first} was added to the Needs attention list.</p>
                      )}
                    </div>
                  )}

                  {fb && (qi < total - 1
                    ? <button onClick={() => setQi((i) => i + 1)} className={btn.primary}>Next <ChevronRight className="w-4 h-4" aria-hidden /></button>
                    : <button onClick={finish} disabled={busy} className={btn.primary}>{busy ? 'Scoring…' : 'See my result'}</button>)}
                </div>
              </div>
            </Card>
          )}

          {phase === 'done' && result && (
            <Card>
              <div className="text-center py-4 space-y-4">
                <div className={`inline-grid place-items-center w-20 h-20 rounded-full ${result.passed ? 'bg-low-soft text-low' : 'bg-high-soft text-high'}`}>
                  {result.passed ? <CheckCircle className="w-10 h-10" aria-hidden /> : <XCircle className="w-10 h-10" aria-hidden />}
                </div>
                <h3 className="text-2xl font-bold">{result.passed ? `Passed! ${result.score} of ${result.total}` : `${result.score} of ${result.total}, not passed yet`}</h3>
                <p className="text-muted">{result.passed ? `${first} is off the Needs attention list.` : `Get ${result.needed} right to pass.`} {points} points.</p>
                <div className="flex items-center justify-center gap-4 text-3xl font-bold tabular">
                  <span className={LEVEL[levelOf(startRisk)].text}>{pct(startRisk)}%</span>
                  <ChevronRight className="w-6 h-6 text-muted" aria-hidden />
                  <span className={LEVEL[result.level_after].text}>{pct(result.risk_after)}%</span>
                </div>
                <p className="text-sm text-muted">Risk before → after</p>
                <div className="flex flex-wrap justify-center gap-2 pt-2">
                  <button onClick={retry} className={btn.ghost}><RotateCcw className="w-4 h-4" aria-hidden /> Try again</button>
                  <button onClick={() => go('why', empId)} className={btn.ghost}>Why at risk?</button>
                </div>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
