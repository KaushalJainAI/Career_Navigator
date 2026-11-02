import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, ArrowRight, CheckCircle2, Loader2, Search } from 'lucide-react';
import { Jobs, Resumes } from '../../api/endpoints';
import { errorMessage } from '../../api/client';
import type { RefreshResult, ResumeUploadResult } from '../../lib/types';
import { ResumeImport } from '../../components/ResumeImport';
import { TargetsForm } from '../../components/TargetsForm';
import { Alert, Badge, Button, Card, Spinner } from '../../components/ui';

const STEP_KEYS = ['resume', 'targets', 'find'] as const;
const STEP_TITLES = ['Add your résumé', 'What roles do you want?', 'Find jobs'];

function stepFromParam(p: string | null): number {
  if (p === 'targets' || p === '2') return 2;
  if (p === 'find' || p === '3') return 3;
  return 1;
}

function listOf<T>(d: unknown): T[] {
  if (Array.isArray(d)) return d as T[];
  const results = (d as { results?: unknown })?.results;
  return Array.isArray(results) ? (results as T[]) : [];
}

export function SetupWizard() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const step = stepFromParam(searchParams.get('step'));

  // Step 1: a parsed résumé either already exists (returning user) or was just imported.
  const [resumeCheckDone, setResumeCheckDone] = useState(false);
  const [hasParsedResume, setHasParsedResume] = useState(false);
  const [justImported, setJustImported] = useState(false);

  // Step 2
  const [targetsSaved, setTargetsSaved] = useState(false);

  // Step 3
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState('');
  const [refresh, setRefresh] = useState<RefreshResult | null>(null);

  useEffect(() => {
    let cancelled = false;
    Resumes.list()
      .then((d: unknown) => {
        if (!cancelled) setHasParsedResume(listOf<{ parse_status: string }>(d).some((r) => r.parse_status === 'done'));
      })
      .catch(() => { /* no list means we just ask the user to add one */ })
      .finally(() => { if (!cancelled) setResumeCheckDone(true); });
    return () => { cancelled = true; };
  }, []);

  function goTo(n: number) {
    setSearchParams({ step: STEP_KEYS[n - 1] });
    setSearchError('');
  }

  function onResumeDone(r: ResumeUploadResult) {
    if (r.parse_status === 'done') setJustImported(true);
  }

  async function findJobs() {
    setSearching(true);
    setSearchError('');
    setRefresh(null);
    try {
      setRefresh(await Jobs.refresh());
    } catch (e) {
      setSearchError(errorMessage(e, 'The job search did not finish. Please try again.'));
    } finally {
      setSearching(false);
    }
  }

  const resumeReady = hasParsedResume || justImported;
  const allSourcesFailed = !!refresh && refresh.sources.length > 0 && refresh.sources.every((s) => !s.ok);
  const nothingFound = !!refresh && (refresh.new_jobs === 0 || allSourcesFailed);

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <header className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm font-semibold text-slate-500">Step {step} of 3</p>
          <Link to="/profile" className="text-sm font-medium text-slate-500 hover:text-slate-900">
            Skip setup
          </Link>
        </div>
        <div className="flex gap-2" aria-hidden="true">
          {[1, 2, 3].map((n) => (
            <span key={n} className={`h-1.5 flex-1 rounded-full ${n <= step ? 'bg-slate-950' : 'bg-slate-200'}`} />
          ))}
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">{STEP_TITLES[step - 1]}</h1>
      </header>

      <Card className="sm:p-6">
        {step === 1 && (
          <div className="space-y-5">
            <p className="text-sm text-slate-600">
              We read your résumé once to fill your profile: name, skills, projects and education.
              You can edit everything afterwards.
            </p>

            {!resumeCheckDone ? (
              <Spinner label="Checking for an existing résumé…" />
            ) : hasParsedResume && !justImported ? (
              <Alert tone="green">
                <span className="inline-flex items-center gap-2 font-semibold">
                  <CheckCircle2 className="h-4 w-4" aria-hidden="true" /> Your résumé is on file.
                </span>
                {!justImported && <span className="mt-1 block">You can replace it later from your profile.</span>}
              </Alert>
            ) : (
              <ResumeImport onDone={onResumeDone} />
            )}

            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-5">
              <Link to="/profile" className="text-sm font-semibold text-slate-600 hover:text-slate-950">
                Skip — I'll fill my profile manually
              </Link>
              <Button onClick={() => goTo(2)} disabled={!resumeReady}>
                Continue <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-5">
            <p className="text-sm text-slate-600">
              We pre-filled these from your résumé. Change anything you like, then save to continue.
              Add at least one role.
            </p>
            <TargetsForm onSaved={() => setTargetsSaved(true)} />

            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-5">
              <Button variant="ghost" onClick={() => goTo(1)}>
                <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Back
              </Button>
              <Button onClick={() => goTo(3)} disabled={!targetsSaved}>
                Continue <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-5">
            <p className="text-sm text-slate-600">
              We search public company career boards (Greenhouse and Lever) and job APIs such as Remotive
              and Arbeitnow for the roles you picked, then rank each job against your profile.
            </p>

            {!refresh && !searching && (
              <Button onClick={findJobs} className="w-full sm:w-auto">
                <Search className="h-4 w-4" aria-hidden="true" /> Find jobs
              </Button>
            )}

            {searching && (
              <Alert tone="slate">
                <span className="inline-flex items-center gap-2 font-semibold">
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> Searching company job boards and job APIs…
                </span>
                <span className="mt-1 block">This can take up to a minute. Please keep this tab open.</span>
              </Alert>
            )}

            {searchError && <Alert tone="red">{searchError}</Alert>}

            {refresh && (
              <div className="space-y-4">
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-2xl font-bold text-slate-950">{refresh.new_jobs} new {refresh.new_jobs === 1 ? 'job' : 'jobs'}</p>
                  <p className="text-sm text-slate-600">added to your feed</p>
                </div>

                {refresh.sources.length > 0 && (
                  <ul className="divide-y divide-slate-100 rounded-xl border border-slate-200">
                    {refresh.sources.map((s) => (
                      <li key={s.source} className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 text-sm">
                        <span className="font-medium text-slate-900">{s.source}</span>
                        <span className="flex items-center gap-3">
                          {s.ok ? (
                            <span className="text-slate-600">
                              {s.fetched} fetched · {s.kept} kept · {s.created} new
                            </span>
                          ) : null}
                          <Badge tone={s.ok ? 'green' : 'red'}>{s.ok ? 'OK' : 'Failed'}</Badge>
                        </span>
                      </li>
                    ))}
                  </ul>
                )}

                {nothingFound && (
                  <Alert tone="amber">
                    <p className="font-semibold">
                      {allSourcesFailed ? 'The job sources were unavailable this time.' : 'No new jobs matched this time.'}
                    </p>
                    <p className="mt-1">
                      Try again later, or add jobs you already found. Campus drives, referrals and company
                      career pages you bookmarked usually are not on job boards.
                    </p>
                    <Link to="/jobs" className="mt-3 inline-flex font-semibold text-amber-900 underline underline-offset-2">
                      Add a job manually
                    </Link>
                  </Alert>
                )}

                <Button variant="secondary" onClick={findJobs} loading={searching}>
                  Search again
                </Button>
              </div>
            )}

            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-5">
              <Button variant="ghost" onClick={() => goTo(2)} disabled={searching}>
                <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Back
              </Button>
              <Button onClick={() => navigate('/jobs')} disabled={searching}>
                Finish <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
