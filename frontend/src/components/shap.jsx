import React from 'react';

const UP = '#e66767';   // pushes click probability up
const DOWN = '#3987e5'; // protective

function fmtValue(c) {
  const v = c.value;
  if (c.unit === 'bool') return v >= 0.5 ? 'yes' : 'no';
  if (c.unit === '%') return `${Math.round(v)}%`;
  if (c.unit === 's') return `${Math.round(v)} s`;
  if (c.unit) return `${Math.round(v * 10) / 10} ${c.unit}`;
  return `${Math.round(v * 10) / 10}`;
}

/**
 * SHAP waterfall: starts at the model's expected value (population baseline),
 * each feature moves the running total, ending at this prediction.
 * All numbers are percentage points of click probability.
 */
export function ShapWaterfall({ base, risk, contributions, top = 7 }) {
  const shown = contributions.slice(0, top);
  const rest = contributions.slice(top).reduce((s, c) => s + c.shap, 0);
  const rows = [];
  let cum = base;
  for (const c of shown) {
    rows.push({ ...c, start: cum, end: cum + c.shap });
    cum += c.shap;
  }
  if (contributions.length > top) {
    rows.push({ feature: '_rest', label: `${contributions.length - top} other features`, shap: rest, start: cum, end: cum + rest, unit: null });
  }
  const pts = [0, 100, base, risk, ...rows.flatMap((r) => [r.start, r.end])];
  const lo = Math.min(...pts), hi = Math.max(...pts);
  const x = (v) => ((v - lo) / (hi - lo)) * 100;
  const ticks = [0, 25, 50, 75, 100];

  return (
    <div className="text-xs" role="figure" aria-label={`SHAP waterfall from baseline ${base} to prediction ${risk}`}>
      <div className="grid grid-cols-[minmax(0,13rem)_1fr_4rem] gap-x-3 gap-y-1.5 items-center">
        <span className="text-slate-400">Population baseline E[f(x)]</span>
        <div className="relative h-5">
          <div className="absolute inset-y-1 rounded-sm bg-slate-600" style={{ left: `${x(0)}%`, width: `${x(base) - x(0)}%` }} />
        </div>
        <span className="font-mono tabular text-right text-slate-300">{base.toFixed(1)}</span>

        {rows.map((r) => {
          const up = r.shap >= 0;
          const l = x(Math.min(r.start, r.end));
          const w = Math.max(0.6, Math.abs(x(r.end) - x(r.start)));
          return (
            <React.Fragment key={r.feature}>
              <span className="text-slate-300 truncate" title={r.label}>
                {r.label}
                {r.unit !== null && r.unit !== undefined && <span className="text-slate-500"> = {fmtValue(r)}</span>}
              </span>
              <div className="relative h-5" title={`${r.label}: ${up ? '+' : ''}${r.shap.toFixed(2)} pts`}>
                <div className="absolute top-0 bottom-0 w-px bg-slate-700" style={{ left: `${x(r.start)}%` }} />
                <div className="absolute inset-y-1 rounded-sm" style={{ left: `${l}%`, width: `${w}%`, background: up ? UP : DOWN }} />
              </div>
              <span className="font-mono tabular text-right" style={{ color: up ? '#fca5a5' : '#93c5fd' }}>
                {up ? '+' : '−'}{Math.abs(r.shap).toFixed(1)}
              </span>
            </React.Fragment>
          );
        })}

        <span className="text-white font-semibold border-t border-slate-800 pt-1.5">Predicted click probability</span>
        <div className="relative h-6 border-t border-slate-800 pt-1.5">
          <div className="absolute top-2 bottom-0.5 rounded-sm bg-cyan-400" style={{ left: `${x(0)}%`, width: `${x(risk) - x(0)}%` }} />
        </div>
        <span className="font-mono tabular text-right text-cyan-300 font-bold border-t border-slate-800 pt-1.5">{risk.toFixed(1)}</span>

        <span />
        <div className="relative h-4 text-[10px] text-slate-500 font-mono">
          {ticks.map((t) => (
            <span key={t} className="absolute -translate-x-1/2" style={{ left: `${x(t)}%` }}>{t}</span>
          ))}
        </div>
        <span />
      </div>
      <div className="flex flex-wrap gap-4 mt-3 text-[11px] text-slate-400">
        <span className="flex items-center gap-1.5"><i className="w-3 h-2 rounded-sm" style={{ background: UP }} /> Raises risk</span>
        <span className="flex items-center gap-1.5"><i className="w-3 h-2 rounded-sm" style={{ background: DOWN }} /> Protective</span>
        <span>Units: percentage points of click probability</span>
      </div>
    </div>
  );
}
