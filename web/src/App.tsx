import { useEffect, useMemo, useState } from "react";
import { ActivationEngine } from "./activation/engine";
import { GraphCanvas } from "./graph/GraphCanvas";
import type { GraphData } from "./graph/types";

export default function App() {
  const [data, setData] = useState<GraphData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/graph")
      .then((r) => r.json())
      .then(setData)
      .catch((e) => setError(String(e)));
  }, []);

  const engine = useMemo(
    () =>
      data
        ? new ActivationEngine(new Map(data.edges.map((e) => [e.id, e.bundle])))
        : null,
    [data]
  );

  if (error) return <div className="p-8 text-red-400">加载失败：{error}</div>;
  if (!data || !engine) return <div className="p-8 text-slate-400">加载中…</div>;
  if (data.nodes.length === 0)
    return <div className="p-8 text-slate-400">知识库为空：01-Cards/ 中没有卡片。</div>;
  return (
    <div className="h-full w-full">
      <GraphCanvas data={data} engine={engine} onNodeClick={() => {}} />
    </div>
  );
}
