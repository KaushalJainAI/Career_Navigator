/**
 * Interactive expand-on-click network graph.
 * Lightweight DOM-only rendering — no extra deps; React-Flow can be swapped in
 * later by replacing the <GraphCanvas /> implementation. The data model and
 * fetch logic stay the same.
 */
import { useEffect, useState } from 'react';
import { Network } from '../../api/endpoints';
import { useAuthStore } from '../../stores/useAuthStore';

type GraphNode = { id: string; type: string; data: Record<string, unknown> };
type GraphEdge = { id: string; source: string; target: string; label: string };

export function NetworkGraphPage() {
  const user = useAuthStore((s) => s.user);
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!user) return;
    setLoading(true);
    Network.graph(`user:${(user as { id: number }).id}`, 1)
      .then((data) => {
        setNodes(data.nodes);
        setEdges(data.edges);
      })
      .finally(() => setLoading(false));
  }, [user]);

  async function handleNodeClick(node: GraphNode) {
    setSelected(node);
    if (node.id.startsWith('user:')) return;
    setLoading(true);
    try {
      const data = await Network.graph(node.id, 1);
      // Merge new nodes/edges into the current canvas.
      setNodes((prev) => {
        const seen = new Set(prev.map((n) => n.id));
        return [...prev, ...data.nodes.filter((n) => !seen.has(n.id))];
      });
      setEdges((prev) => {
        const seen = new Set(prev.map((e) => e.id + e.source + e.target));
        return [...prev, ...data.edges.filter((e) => !seen.has(e.id + e.source + e.target))];
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-2xl font-black text-slate-900">Network graph</h1>
        <p className="text-sm text-slate-600">
          You (centre) and your network. Click a company or contact to expand.
        </p>
      </header>

      <div className="grid gap-4 lg:grid-cols-[3fr_1fr]">
        <div className="min-h-[500px] rounded-3xl bg-white p-4 shadow-sm">
          {loading && nodes.length === 0 ? (
            <p className="text-sm text-slate-500">Loading network…</p>
          ) : (
            <GraphCanvas nodes={nodes} edges={edges} onNodeClick={handleNodeClick} />
          )}
        </div>
        <aside className="rounded-3xl bg-white p-4 shadow-sm">
          <h2 className="text-sm font-black uppercase text-slate-500">Details</h2>
          {selected ? (
            <div className="mt-3 space-y-2 text-sm">
              <p className="font-bold text-slate-900">
                {(selected.data.label as string) ?? selected.id}
              </p>
              <p className="text-xs uppercase text-slate-400">{selected.type}</p>
              {Object.entries(selected.data)
                .filter(([k]) => k !== 'label')
                .map(([k, v]) => (
                  <p key={k} className="text-xs text-slate-600">
                    <span className="font-bold">{k}:</span> {String(v ?? '—')}
                  </p>
                ))}
            </div>
          ) : (
            <p className="mt-3 text-sm text-slate-500">Click a node to inspect.</p>
          )}
        </aside>
      </div>
    </div>
  );
}

function GraphCanvas({
  nodes,
  edges,
  onNodeClick,
}: {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onNodeClick: (node: GraphNode) => void;
}) {
  // Minimal placeholder: list-by-type grouping. A full SVG/React-Flow viz can
  // replace this without touching the data layer.
  const grouped: Record<string, GraphNode[]> = {};
  for (const n of nodes) {
    (grouped[n.type] ||= []).push(n);
  }
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {Object.entries(grouped).map(([type, list]) => (
        <div key={type}>
          <h3 className="text-xs font-black uppercase text-slate-400">{type}s</h3>
          <ul className="mt-2 space-y-1">
            {list.map((n) => (
              <li key={n.id}>
                <button
                  onClick={() => onNodeClick(n)}
                  className="w-full rounded-xl border border-slate-200 px-3 py-2 text-left text-sm hover:border-teal-400 hover:bg-teal-50"
                >
                  {(n.data.label as string) ?? n.id}
                </button>
              </li>
            ))}
          </ul>
        </div>
      ))}
      <div className="md:col-span-3">
        <h3 className="text-xs font-black uppercase text-slate-400">Edges ({edges.length})</h3>
        <ul className="mt-2 max-h-40 overflow-auto text-xs text-slate-600">
          {edges.map((e) => (
            <li key={e.id}>
              {e.source} → {e.target}: {e.label}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
