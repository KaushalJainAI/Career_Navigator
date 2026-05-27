import { useEffect, useState } from 'react';
import { Resumes } from '../../api/endpoints';

interface Resume {
  id: number;
  label: string;
  parse_status: string;
  is_master: boolean;
  created_at: string;
}

export function ResumesPage() {
  const [items, setItems] = useState<Resume[]>([]);
  const [busy, setBusy] = useState(false);
  const refresh = () => Resumes.list().then((d) => setItems(d.results ?? d));
  useEffect(() => { refresh(); }, []);

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    if (!e.target.files?.[0]) return;
    setBusy(true);
    try {
      await Resumes.upload(e.target.files[0]);
      refresh();
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="space-y-4">
      <div>
        <h1 className="text-2xl font-black tracking-tight text-slate-950">Resumes</h1>
        <p className="mt-1 text-sm font-semibold text-slate-500">Keep your master resume ready for matching and tailoring.</p>
      </div>
      <label className="block rounded-2xl border border-dashed border-slate-300 bg-white p-4 text-sm font-bold text-slate-700 shadow-sm">
        <span className="block">Upload PDF or DOCX</span>
        <input className="mt-3 block w-full text-sm file:mr-3 file:rounded-xl file:border-0 file:bg-slate-950 file:px-4 file:py-2 file:font-bold file:text-white" type="file" accept=".pdf,.docx" onChange={onUpload} disabled={busy} />
      </label>
      <ul className="space-y-2">
        {items.map((r) => (
          <li key={r.id} className="rounded-2xl bg-white p-4 shadow-sm">
            <div className="font-bold text-slate-900">{r.label}</div>
            <div className="mt-1 text-sm text-slate-500">{r.parse_status} - {r.is_master ? 'master' : 'variant'}</div>
          </li>
        ))}
      </ul>
    </section>
  );
}
