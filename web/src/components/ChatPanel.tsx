import { useState } from "react";

interface Msg {
  role: "user" | "system";
  text: string;
}

const TRIGGERS: Array<[RegExp, string, string]> = [
  [/深判|\/judge|怎么判断|评估/, "judge", "nexo-judge"],
  [/消化|\/digest/, "digest", "nexo-digest"],
];

interface Props {
  onTrigger: (scenario: string) => void;
  skillLabel: string | null;
}

export function ChatPanel({ onTrigger, skillLabel }: Props) {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");

  const submit = () => {
    const text = input.trim();
    if (!text) return;
    setInput("");
    const hit = TRIGGERS.find(([re]) => re.test(text));
    const scenario = hit ? hit[1] : "talk";
    const skill = hit ? hit[2] : "nexo-talk";
    setMsgs((m) => [
      ...m,
      { role: "user", text },
      { role: "system", text: `触发 ${skill}（模拟剧本 ${scenario}），观察图谱激活…` },
    ]);
    onTrigger(scenario);
  };

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-lg border border-slate-700/60 bg-slate-950/80">
      <div className="flex items-center justify-between border-b border-slate-700/60 px-3 py-1.5">
        <span className="text-xs text-slate-400">对话</span>
        {skillLabel && (
          <span className="rounded-full border border-teal-300/50 px-2 py-0.5 text-[10px] text-teal-300">
            {skillLabel}
          </span>
        )}
      </div>
      <div className="flex-1 space-y-2 overflow-y-auto px-3 py-2 text-sm">
        {msgs.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-slate-100" : "text-slate-500"}>
            {m.role === "user" ? "你：" : ""}{m.text}
          </div>
        ))}
      </div>
      <div className="border-t border-slate-700/60 p-2">
        <input
          className="w-full rounded bg-slate-900 px-3 py-1.5 text-sm text-slate-100 outline-none placeholder:text-slate-600"
          placeholder="试试：深判 止损纪律 / 消化 / 随便问问"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
        />
      </div>
    </div>
  );
}
