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
}

export function ChatPanel({ onTrigger }: Props) {
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
    <div className="flex h-full flex-col">
      {/* 消息区 */}
      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
        {msgs.length === 0 && (
          <p className="mt-8 text-center text-xs leading-6 text-zinc-600">
            对知识体提问、深判或消化。
            <br />
            图谱会随检索与思考实时激活。
          </p>
        )}
        {msgs.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="flex justify-end">
              <div className="max-w-[85%] rounded-2xl rounded-br-md bg-zinc-800 px-3.5 py-2 text-[13px] leading-5 text-zinc-100">
                {m.text}
              </div>
            </div>
          ) : (
            <div key={i} className="border-l-2 border-teal-400/50 pl-3 text-[13px] leading-5 text-zinc-400">
              {m.text}
            </div>
          )
        )}
      </div>
      {/* 输入区 */}
      <div className="border-t border-white/[0.06] p-3">
        <input
          className="w-full rounded-full border border-white/[0.08] bg-zinc-900 px-4 py-2 text-[13px] text-zinc-100 outline-none transition placeholder:text-zinc-600 focus:border-teal-400/40 focus:ring-2 focus:ring-teal-400/20"
          placeholder="提问、深判、消化…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
        />
      </div>
    </div>
  );
}
