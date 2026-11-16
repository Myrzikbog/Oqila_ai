import React, { useEffect, useState } from 'react';
import { ThumbsDown, ThumbsUp, AlertTriangle } from 'lucide-react';
import { fetchAdminLegalFeedback } from '../utils/adminApi';

/** Ratings of the legal assistant's answers and the knowledge-base facts that are due for a manual re-check. */
export default function AdminLegal() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let alive = true;
    fetchAdminLegalFeedback()
      .then((res) => { if (alive) setData(res); })
      .catch((err) => { if (alive && err.message !== 'UNAUTHORIZED') setError(err.message); });
    return () => { alive = false; };
  }, []);

  if (error) return <p role="alert" className="text-sm font-semibold text-rose-300">{error}</p>;
  if (!data) return <p className="text-sm text-slate-400" role="status">…</p>;

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 space-y-3">
        <h2 className="text-sm font-bold flex items-center gap-2"><AlertTriangle className="w-4 h-4 text-amber-400" aria-hidden="true" />Факты базы, которые пора перепроверить</h2>
        {data.stale_facts.length === 0 ? (
          <p className="text-xs text-slate-400">Все факты проверены за последние 90 дней.</p>
        ) : (
          <ul className="space-y-1 text-xs text-slate-300">
            {data.stale_facts.map((f) => (
              <li key={f.id}><b>{f.id}</b> — {f.age_days} дн. · {f.status} · <a className="underline text-teal-300" href={f.source_url} target="_blank" rel="noopener noreferrer">источник</a></li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 space-y-3">
        <h2 className="text-sm font-bold">Оценки ответов ({data.feedback.length})</h2>
        {data.feedback.length === 0 && <p className="text-xs text-slate-400">Оценок пока нет.</p>}
        <ul className="space-y-3">
          {data.feedback.map((f) => (
            <li key={f.id} className="text-xs border-t border-slate-800 pt-3 space-y-1">
              <p className="flex items-center gap-2 font-semibold">
                {f.rating > 0 ? <ThumbsUp className="w-4 h-4 text-emerald-400" aria-label="полезно" /> : <ThumbsDown className="w-4 h-4 text-rose-400" aria-label="не помогло" />}
                <span className="text-slate-400">{f.created_at} · пользователь {f.user_id}{f.is_mock ? ' · шаблонный ответ' : ''}</span>
              </p>
              <p><span className="text-slate-400">Вопрос:</span> {f.question}</p>
              <p><span className="text-slate-400">Ответ:</span> {f.short_answer}</p>
              {f.comment && <p><span className="text-slate-400">Комментарий:</span> {f.comment}</p>}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
