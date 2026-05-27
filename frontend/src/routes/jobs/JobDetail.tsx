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

  if (!job) return <p>Loading...</p>;
  return (
    <section className="space-y-5">
      <div>
        <h1 className="text-2xl font-black tracking-tight text-slate-950 sm:text-3xl">{job.title}</h1>
        <div className="mt-2 text-sm font-semibold text-slate-600 sm:text-base">{job.company?.name}</div>
      </div>
      {match && (
        <div className="rounded-2xl bg-white p-4 shadow-sm">
          <div className="font-medium">Match score: {(match.score * 100).toFixed(0)}%</div>
          {match.gaps?.length > 0 && (
            <div className="text-sm text-amber-700">Gaps: {match.gaps.join(', ')}</div>
          )}
        </div>
      )}
      <article className="prose max-w-none rounded-2xl bg-white p-4 text-sm leading-7 sm:p-5 sm:text-base" dangerouslySetInnerHTML={{ __html: job.description }} />
      <div className="grid gap-2 sm:flex sm:flex-wrap">
        <button className="rounded-xl bg-indigo-600 px-4 py-3 font-bold text-white" onClick={() => apply('assist')}>Assist apply</button>
        <button className="rounded-xl bg-indigo-600 px-4 py-3 font-bold text-white" onClick={() => apply('autofill')}>Autofill</button>
        <button className="rounded-xl bg-red-600 px-4 py-3 font-bold text-white" onClick={() => apply('autonomous')}>Autonomous</button>
      </div>
    </section>
  );
}
