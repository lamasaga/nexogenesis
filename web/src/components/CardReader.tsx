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
    <div className="absolute bottom-3 right-3 top-14 z-10 flex w-96 flex-col overflow-hidden rounded-xl border border-white/[0.08] bg-[#101013]/95 shadow-2xl shadow-black/60 backdrop-blur">
      <div className="flex items-center justify-between border-b border-white/[0.06] px-4 py-2.5">
        <span className="micro-label">卡片</span>
        <button
          className="rounded-md px-1.5 py-0.5 text-zinc-500 transition hover:bg-white/[0.06] hover:text-zinc-200"
          onClick={onClose}
        >
          ✕
        </button>
      </div>
      <div className="flex-1 overflow-y-auto px-4 py-3">
        {error && <p className="text-[13px] text-red-400">{error}</p>}
        {!error && !card && <p className="text-[13px] text-zinc-600">读取中…</p>}
        {card && (
          <>
            <h2 className="mb-1.5 text-[15px] font-medium leading-6 text-zinc-100">{card.title}</h2>
            <p className="micro-label mb-3 !normal-case !tracking-normal">
              {card.type} · {card.maturity} · 更新 {card.updated}
            </p>
            <pre className="whitespace-pre-wrap font-sans text-[13px] leading-6 text-zinc-300">
              {card.body}
            </pre>
          </>
        )}
      </div>
    </div>
  );
}
