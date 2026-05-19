import { useParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { Jobs, Applications, Tailoring } from '../../api/endpoints';

interface Job {
  id: number;
  title: string;
  description: string;
  apply_url: string;
  company: { name: string };
}

interface Match {
  score: number;
  breakdown: Record<string, number>;
  gaps: string[];
}

export function JobDetail() {
  const { id } = useParams();
  const jobId = Number(id);
  const [job, setJob] = useState<Job | null>(null);
  const [match, setMatch] = useState<Match | null>(null);

  useEffect(() => {
    Jobs.detail(jobId).then(setJob);
    Jobs.match(jobId).then(setMatch).catch(() => undefined);
  }, [jobId]);

  async function apply(tier: string) {
    const app = await Applications.create(jobId, tier);
    await Tailoring.resume(app.id);
    alert('Application created and tailored resume generated.');
  }

  if (!job) return <p>Loading…</p>;
  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold">{job.title}</h1>
      <div className="text-slate-600">{job.company?.name}</div>
      {match && (
        <div className="bg-white p-3 rounded shadow-sm">
          <div className="font-medium">Match score: {(match.score * 100).toFixed(0)}%</div>
          {match.gaps?.length > 0 && (
            <div className="text-sm text-amber-700">Gaps: {match.gaps.join(', ')}</div>
          )}
        </div>
      )}
      <article className="prose" dangerouslySetInnerHTML={{ __html: job.description }} />
      <div className="flex gap-2">
        <button className="bg-indigo-600 text-white px-3 py-2 rounded" onClick={() => apply('assist')}>Assist apply</button>
        <button className="bg-indigo-600 text-white px-3 py-2 rounded" onClick={() => apply('autofill')}>Autofill</button>
        <button className="bg-red-600 text-white px-3 py-2 rounded" onClick={() => apply('autonomous')}>Autonomous</button>
      </div>
    </section>
  );
}
