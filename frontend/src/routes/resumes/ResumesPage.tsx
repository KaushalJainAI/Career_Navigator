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
    await Resumes.upload(e.target.files[0]);
    setBusy(false);
    refresh();
  }
  return (
    <section>
      <h1 className="text-xl font-semibold mb-4">Resumes</h1>
      <input type="file" accept=".pdf,.docx" onChange={onUpload} disabled={busy} />
      <ul className="mt-4 space-y-2">
        {items.map((r) => (
          <li key={r.id} className="bg-white p-3 rounded shadow-sm">
            <div className="font-medium">{r.label}</div>
            <div className="text-sm text-slate-500">{r.parse_status} · {r.is_master ? 'master' : 'variant'}</div>
          </li>
        ))}
      </ul>
    </section>
  );
}
