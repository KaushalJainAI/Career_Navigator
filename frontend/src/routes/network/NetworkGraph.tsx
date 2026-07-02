/**
 * Interactive network graph — a real SVG node-link diagram (no external deps).
 *
 * You (or a company) sit at the centre; contacts and companies orbit outward.
 * Everything is editable from the GUI:
 *   - Add a person (optionally at a company).
 *   - "Connect" mode: click one node then another to draw a relationship
 *     (contact→contact) or place someone at a company (contact→company).
 *   - Drag nodes to rearrange, double-click to expand a node's neighbours.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Link2, UserPlus, Maximize2 } from 'lucide-react';
import { Network } from '../../api/endpoints';
import { useAuthStore } from '../../stores/useAuthStore';

type GraphNode = { id: string; type: string; data: Record<string, unknown> };
type GraphEdge = { id: string; source: string; target: string; label: string };
type Pos = { x: number; y: number };

const VBW = 960;
const VBH = 620;

const NODE_STYLE: Record<string, { fill: string; ring: string; r: number }> = {
  user: { fill: '#0f172a', ring: '#5eead4', r: 30 },
  company: { fill: '#0369a1', ring: '#7dd3fc', r: 26 },
  contact: { fill: '#0d9488', ring: '#99f6e4', r: 22 },
};

const REL_KINDS: [string, string][] = [
  ['colleague', 'Colleague'],
  ['manager', 'Manager'],
  ['report', 'Direct report'],
  ['reference', 'Reference'],
  ['mutual', 'Mutual connection'],
  ['classmate', 'Classmate'],
  ['friend', 'Friend'],
];

function idNum(id: string) { return Number(id.split(':')[1]); }

function computeLayout(nodes: GraphNode[], edges: GraphEdge[], rootId: string, existing: Record<string, Pos>): Record<string, Pos> {
  const pos: Record<string, Pos> = { ...existing };
  const adj: Record<string, string[]> = {};
  edges.forEach((e) => { (adj[e.source] ||= []).push(e.target); (adj[e.target] ||= []).push(e.source); });
  const depth: Record<string, number> = {};
  const start = nodes.find((n) => n.id === rootId)?.id ?? nodes[0]?.id;
  if (start) {
    depth[start] = 0;
    const queue = [start];
    while (queue.length) {
      const cur = queue.shift() as string;
      for (const nb of adj[cur] ?? []) {
        if (depth[nb] === undefined) { depth[nb] = depth[cur] + 1; queue.push(nb); }
      }
    }
  }
  const byDepth: Record<number, GraphNode[]> = {};
  nodes.forEach((n) => { const d = depth[n.id] ?? 1; (byDepth[d] ||= []).push(n); });
  const cx = VBW / 2, cy = VBH / 2;
  Object.entries(byDepth).forEach(([d, list]) => {
    const dd = Number(d);
    const radius = dd === 0 ? 0 : 130 + (dd - 1) * 150;
    list.forEach((n, i) => {
      if (pos[n.id]) return;
      if (dd === 0) { pos[n.id] = { x: cx, y: cy }; return; }
      const ang = (i / Math.max(list.length, 1)) * Math.PI * 2 - Math.PI / 2;
      pos[n.id] = { x: cx + radius * Math.cos(ang), y: cy + radius * Math.sin(ang) };
    });
  });
  return pos;
}

export function NetworkGraphPage() {
  const user = useAuthStore((s) => s.user);
  const [params] = useSearchParams();
  const rootId = params.get('root') || (user ? `user:${(user as { id: number }).id}` : 'user:self');

  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [pos, setPos] = useState<Record<string, Pos>>({});
  const [selected, setSelected] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // GUI editing state
  const [connectMode, setConnectMode] = useState(false);
  const [connectSource, setConnectSource] = useState<string | null>(null);
  const [connectTarget, setConnectTarget] = useState<string | null>(null);
  const [relKind, setRelKind] = useState('colleague');
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ name: '', title: '', company: '' });
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await Network.graph(rootId, 1);
      setNodes(data.nodes);
      setEdges(data.edges);
      setPos((prev) => computeLayout(data.nodes, data.edges, rootId, prev));
    } finally { setLoading(false); }
  }, [rootId]);

  useEffect(() => { if (user) load(); }, [user, load]);

  const merge = useCallback((data: { nodes: GraphNode[]; edges: GraphEdge[] }, center: string) => {
    setNodes((prev) => {
      const seen = new Set(prev.map((n) => n.id));
      const next = [...prev, ...data.nodes.filter((n) => !seen.has(n.id))];
      setPos((p) => computeLayout(next, [...edges, ...data.edges], center, p));
      return next;
    });
    setEdges((prev) => {
      const seen = new Set(prev.map((e) => e.source + e.target + e.label));
      return [...prev, ...data.edges.filter((e) => !seen.has(e.source + e.target + e.label))];
    });
  }, [edges]);

  async function expand(nodeId: string) {
    if (nodeId.startsWith('user:')) return;
    setLoading(true);
    try { merge(await Network.graph(nodeId, 1), nodeId); }
    finally { setLoading(false); }
  }

  function flash(msg: string) { setToast(msg); setTimeout(() => setToast(''), 2500); }

  function onNodeClick(id: string) {
    if (connectMode) {
      if (!connectSource) { setConnectSource(id); return; }
      if (id === connectSource) { setConnectSource(null); return; }
      setConnectTarget(id);
      return;
    }
    setSelected(id === selected ? null : id);
  }

  async function addPerson() {
    if (!form.name.trim()) return;
    setBusy(true);
    try {
      await Network.contacts.create({ name: form.name.trim(), title: form.title.trim(), company_name: form.company.trim() });
      setForm({ name: '', title: '', company: '' });
      setShowAdd(false);
      await load();
      flash('Person added');
    } finally { setBusy(false); }
  }

  async function confirmConnect() {
    if (!connectSource || !connectTarget) return;
    const s = nodes.find((n) => n.id === connectSource);
    const t = nodes.find((n) => n.id === connectTarget);
    if (!s || !t) return;
    setBusy(true);
    try {
      if (s.type === 'contact' && t.type === 'contact') {
        await Network.relationships.create(idNum(s.id), { to_contact: idNum(t.id), kind: relKind, strength: 3 });
        flash('Relationship added');
      } else if (s.type === 'contact' && t.type === 'company') {
        await Network.employments.create(idNum(s.id), { company: idNum(t.id), is_current: true });
        flash('Placed at company');
      } else if (s.type === 'company' && t.type === 'contact') {
        await Network.employments.create(idNum(t.id), { company: idNum(s.id), is_current: true });
        flash('Placed at company');
      } else {
        flash('Pick a person + a person, or a person + a company');
        cancelConnect();
        return;
      }
      cancelConnect();
      await load();
    } finally { setBusy(false); }
  }

  function cancelConnect() { setConnectSource(null); setConnectTarget(null); }

  const selectedNode = nodes.find((n) => n.id === selected);
  const canPickKind = (() => {
    const s = nodes.find((n) => n.id === connectSource);
    const t = nodes.find((n) => n.id === connectTarget);
    return s?.type === 'contact' && t?.type === 'contact';
  })();

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-black tracking-tight text-slate-950 sm:text-3xl">Network graph</h1>
          <p className="text-sm font-semibold text-slate-500">
            {rootId.startsWith('company:') ? 'Centred on a company.' : 'You in the centre.'} Drag to arrange · double-click to expand · use Connect to link people.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => { setShowAdd((v) => !v); setConnectMode(false); cancelConnect(); }}
            className="inline-flex items-center gap-2 rounded-2xl bg-slate-950 px-4 py-2 text-sm font-black text-white"
          >
            <UserPlus className="h-4 w-4" /> Add person
          </button>
          <button
            onClick={() => { setConnectMode((v) => !v); cancelConnect(); setShowAdd(false); }}
            className={`inline-flex items-center gap-2 rounded-2xl px-4 py-2 text-sm font-black transition ${connectMode ? 'bg-teal-600 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'}`}
          >
            <Link2 className="h-4 w-4" /> {connectMode ? 'Connecting…' : 'Connect'}
          </button>
        </div>
      </header>

      {showAdd && (
        <div className="flex flex-wrap items-end gap-2 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <Field label="Name" value={form.name} onChange={(v) => setForm({ ...form, name: v })} />
          <Field label="Title" value={form.title} onChange={(v) => setForm({ ...form, title: v })} />
          <Field label="Company" value={form.company} onChange={(v) => setForm({ ...form, company: v })} />
          <button onClick={addPerson} disabled={!form.name.trim() || busy} className="rounded-2xl bg-teal-600 px-4 py-2 text-sm font-black text-white disabled:opacity-50">
            {busy ? 'Adding…' : 'Add'}
          </button>
        </div>
      )}

      {connectMode && (
        <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-teal-200 bg-teal-50 p-3 text-sm font-bold text-teal-800">
          <span>
            {!connectSource ? 'Click the first node…' : !connectTarget ? 'Now click the node to connect it to…' : 'Confirm the link →'}
          </span>
          {connectTarget && canPickKind && (
            <select value={relKind} onChange={(e) => setRelKind(e.target.value)} className="rounded-xl border border-teal-300 bg-white px-2 py-1 text-sm">
              {REL_KINDS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          )}
          {connectTarget && (
            <button onClick={confirmConnect} disabled={busy} className="rounded-xl bg-teal-600 px-3 py-1 text-xs font-black text-white disabled:opacity-50">
              {busy ? 'Saving…' : 'Confirm link'}
            </button>
          )}
          {connectSource && (
            <button onClick={cancelConnect} className="rounded-xl bg-white px-3 py-1 text-xs font-black text-teal-700">Reset</button>
          )}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[1fr_260px]">
        <div className="relative overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
          {toast && (
            <div className="absolute left-1/2 top-3 z-10 -translate-x-1/2 rounded-full bg-slate-900 px-3 py-1 text-xs font-black text-white">{toast}</div>
          )}
          {loading && nodes.length === 0 ? (
            <p className="p-8 text-sm font-semibold text-slate-400">Loading network…</p>
          ) : nodes.length === 0 ? (
            <div className="p-10 text-center">
              <Maximize2 className="mx-auto h-8 w-8 text-slate-300" />
              <p className="mt-2 text-sm font-bold text-slate-600">Your graph is empty</p>
              <p className="text-xs text-slate-400">Add a person to get started.</p>
            </div>
          ) : (
            <GraphCanvas
              nodes={nodes} edges={edges} pos={pos} setPos={setPos}
              selected={selected} connectSource={connectSource} connectTarget={connectTarget}
              onNodeClick={onNodeClick} onNodeExpand={expand}
            />
          )}
        </div>

        <aside className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-4 space-y-1.5">
            {Object.entries(NODE_STYLE).map(([type, s]) => (
              <div key={type} className="flex items-center gap-2 text-xs font-bold capitalize text-slate-500">
                <span className="h-3 w-3 rounded-full" style={{ background: s.fill }} /> {type}
              </div>
            ))}
          </div>
          <h2 className="text-sm font-black uppercase text-slate-500">Details</h2>
          {selectedNode ? (
            <div className="mt-3 space-y-2 text-sm">
              <p className="font-black text-slate-900">{(selectedNode.data.label as string) ?? selectedNode.id}</p>
              <p className="text-xs uppercase text-slate-400">{selectedNode.type}</p>
              {Object.entries(selectedNode.data).filter(([k, v]) => k !== 'label' && v).map(([k, v]) => (
                <p key={k} className="text-xs text-slate-600"><span className="font-bold capitalize">{k.replace('_', ' ')}:</span> {String(v)}</p>
              ))}
              {selectedNode.type === 'company' && (
                <a href={`/companies/${idNum(selectedNode.id)}`} className="inline-block rounded-xl bg-slate-100 px-3 py-1.5 text-xs font-black text-slate-700 hover:bg-slate-200">Open company hub →</a>
              )}
              <button onClick={() => expand(selectedNode.id)} className="block w-full rounded-xl bg-teal-50 px-3 py-1.5 text-xs font-black text-teal-700 hover:bg-teal-100">Expand neighbours</button>
            </div>
          ) : (
            <p className="mt-3 text-sm text-slate-500">Click a node to inspect it.</p>
          )}
        </aside>
      </div>
    </div>
  );
}

function GraphCanvas({
  nodes, edges, pos, setPos, selected, connectSource, connectTarget, onNodeClick, onNodeExpand,
}: {
  nodes: GraphNode[]; edges: GraphEdge[]; pos: Record<string, Pos>;
  setPos: React.Dispatch<React.SetStateAction<Record<string, Pos>>>;
  selected: string | null; connectSource: string | null; connectTarget: string | null;
  onNodeClick: (id: string) => void; onNodeExpand: (id: string) => void;
}) {
  const svgRef = useRef<SVGSVGElement>(null);
  const drag = useRef<{ id: string; moved: boolean } | null>(null);

  const toSvg = useCallback((clientX: number, clientY: number): Pos => {
    const svg = svgRef.current;
    if (!svg) return { x: 0, y: 0 };
    const pt = svg.createSVGPoint();
    pt.x = clientX; pt.y = clientY;
    const ctm = svg.getScreenCTM();
    if (!ctm) return { x: 0, y: 0 };
    const p = pt.matrixTransform(ctm.inverse());
    return { x: p.x, y: p.y };
  }, []);

  useEffect(() => {
    function onMove(e: PointerEvent) {
      if (!drag.current) return;
      drag.current.moved = true;
      const p = toSvg(e.clientX, e.clientY);
      setPos((prev) => ({ ...prev, [drag.current!.id]: p }));
    }
    function onUp() { drag.current = null; }
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    return () => { window.removeEventListener('pointermove', onMove); window.removeEventListener('pointerup', onUp); };
  }, [setPos, toSvg]);

  const positioned = useMemo(() => nodes.filter((n) => pos[n.id]), [nodes, pos]);

  return (
    <svg ref={svgRef} viewBox={`0 0 ${VBW} ${VBH}`} className="h-[480px] w-full touch-none sm:h-[560px]" role="img" aria-label="Network graph">
      {/* edges */}
      {edges.map((e) => {
        const a = pos[e.source]; const b = pos[e.target];
        if (!a || !b) return null;
        const active = selected === e.source || selected === e.target;
        return (
          <g key={e.id}>
            <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={active ? '#0d9488' : '#cbd5e1'} strokeWidth={active ? 2.5 : 1.5} />
            {active && (
              <text x={(a.x + b.x) / 2} y={(a.y + b.y) / 2 - 4} textAnchor="middle" className="fill-slate-500" fontSize="11" fontWeight="700">{e.label}</text>
            )}
          </g>
        );
      })}
      {/* nodes */}
      {positioned.map((n) => {
        const p = pos[n.id];
        const style = NODE_STYLE[n.type] ?? NODE_STYLE.contact;
        const isSel = selected === n.id;
        const isSrc = connectSource === n.id;
        const isTgt = connectTarget === n.id;
        const ring = isSrc ? '#0d9488' : isTgt ? '#f59e0b' : isSel ? style.ring : 'transparent';
        const label = (n.data.label as string) ?? n.id;
        return (
          <g
            key={n.id}
            transform={`translate(${p.x}, ${p.y})`}
            className="cursor-pointer"
            onPointerDown={(e) => { (e.target as Element).setPointerCapture?.(e.pointerId); drag.current = { id: n.id, moved: false }; }}
            onPointerUp={() => { if (drag.current && !drag.current.moved) onNodeClick(n.id); }}
            onDoubleClick={() => onNodeExpand(n.id)}
          >
            {(isSrc || isTgt || isSel) && <circle r={style.r + 6} fill="none" stroke={ring} strokeWidth={3} />}
            <circle r={style.r} fill={style.fill} />
            <text textAnchor="middle" dy="0.35em" className="fill-white" fontSize="13" fontWeight="800">
              {label.slice(0, 2).toUpperCase()}
            </text>
            <text textAnchor="middle" y={style.r + 15} className="fill-slate-700" fontSize="12" fontWeight="700">
              {label.length > 18 ? `${label.slice(0, 17)}…` : label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <label className="min-w-32 flex-1">
      <span className="block text-xs font-bold uppercase text-slate-500">{label}</span>
      <input value={value} onChange={(e) => onChange(e.target.value)} className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm" />
    </label>
  );
}
