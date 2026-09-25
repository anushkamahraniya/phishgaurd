async function req(path, opts = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch { /* keep status text */ }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return res.json();
}

export const api = {
  dashboard: () => req('/api/dashboard'),
  employees: (params) => req('/api/employees?' + new URLSearchParams(params)),
  explain: (id) => req(`/api/xai/employee/${id}`),
  predict: (features) => req('/api/xai/predict', { method: 'POST', body: features }),
  globalXai: () => req('/api/xai/global'),
  highRisk: (n = 12) => req(`/api/xai/high-risk?n=${n}`),
  report: () => req('/api/model/report'),
  analyzeText: (text, kind) => req('/api/analyze/text', { method: 'POST', body: { text, kind } }),
  templates: () => req('/api/templates'),
  campaigns: () => req('/api/campaigns'),
  forecast: (modality, dept, difficulty) =>
    req('/api/campaigns/forecast?' + new URLSearchParams({ modality, dept, difficulty })),
  launch: (body) => req('/api/campaigns', { method: 'POST', body }),
  autoAssign: () => req('/api/training/auto-assign', { method: 'POST' }),
  training: (id) => req(`/api/training/${id}`),
  checkAnswer: (question_id, answer, emp_id) => req('/api/training/check', { method: 'POST', body: { question_id, answer, emp_id } }),
  submitQuiz: (id, answers) => req(`/api/training/${id}/submit`, { method: 'POST', body: { answers } }),
  reset: () => req('/api/reset', { method: 'POST' }),
  check: (text) => req('/api/check', { method: 'POST', body: { text } }),
  checkFile: async (file) => {
    const form = new FormData();
    form.append('file', file);
    const res = await fetch('/api/check/file', { method: 'POST', body: form });
    if (!res.ok) {
      let detail = res.statusText;
      try { detail = (await res.json()).detail || detail; } catch { /* keep status text */ }
      throw new Error(detail);
    }
    return res.json();
  },
};
