import { useEffect, useState } from "react";
import { fetchCard, type CardDetail } from "../api/client";

export function CardReader({ cardId, onClose }: { cardId: string | null; onClose: () => void }) {
  const [card, setCard] = useState<CardDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setCard(null);
    setError(null);
    if (cardId) fetchCard(cardId).then(setCard).catch((e) => setError(String(e)));
  }, [cardId]);

  if (!cardId) return null;
  return (
    <div className="absolute bottom-0 right-0 top-0 z-10 w-96 overflow-y-auto border-l border-slate-700 bg-slate-950/95 p-4 shadow-2xl">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs text-slate-500">{cardId}</span>
        <button className="text-slate-500 hover:text-slate-200" onClick={onClose}>✕</button>
      </div>
      {error && <p className="text-sm text-red-400">{error}</p>}
      {card && (
        <>
          <h2 className="mb-1 text-lg text-slate-100">{card.title}</h2>
          <p className="mb-3 text-xs text-slate-500">
            {card.type} · {card.maturity} · 更新 {card.updated}
          </p>
          <pre className="whitespace-pre-wrap font-sans text-sm leading-6 text-slate-300">
            {card.body}
          </pre>
        </>
      )}
    </div>
  );
}
