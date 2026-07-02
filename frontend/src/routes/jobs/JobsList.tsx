import { useEffect, useState } from 'react';
import { useJobsStore } from '../../stores/useJobsStore';
import { Link } from 'react-router-dom';
import { Search, MapPin, Building, ChevronRight } from 'lucide-react';
import { GhostRiskBadge } from '../../components/GhostRiskBadge';

export function JobsList() {
  const { jobs, fetch, loading } = useJobsStore();
  const [q, setQ] = useState('');
  
  useEffect(() => { fetch(); }, [fetch]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-800">Discover Jobs</h1>
          <p className="text-slate-500 text-sm mt-1">Find and apply to positions matching your profile.</p>
        </div>
      </div>

      {/* Search Bar */}
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <Search className="h-5 w-5 text-slate-400" />
        </div>
        <input 
          className="block w-full rounded-xl border border-slate-200 bg-white py-3 pl-10 pr-3 leading-5 shadow-sm transition-all placeholder:text-sm placeholder-slate-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500 sm:placeholder:text-base" 
          placeholder="Search for roles, companies, or keywords..."
          value={q} 
          onChange={(e) => { 
            setQ(e.target.value); 
            fetch({ search: e.target.value }); 
          }} 
        />
      </div>

      {/* Job List */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3, 4].map(i => <div key={i} className="h-28 bg-slate-200 animate-pulse rounded-xl" />)}
        </div>
      ) : (
        <div className="space-y-2.5 sm:space-y-4">
          {jobs.length === 0 && (
            <div className="text-center py-12 bg-white rounded-xl border border-dashed border-slate-300">
              <Search className="mx-auto h-12 w-12 text-slate-300 mb-3" />
              <h3 className="text-lg font-medium text-slate-900">No jobs found</h3>
              <p className="text-slate-500">Try adjusting your search terms.</p>
            </div>
          )}
          {jobs.map((j) => (
            <Link 
              key={j.id} 
              to={`/jobs/${j.id}`}
              className="group block rounded-xl border border-slate-200 bg-white p-3 shadow-sm transition-all duration-200 hover:border-brand-300 hover:shadow-md sm:p-5"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex min-w-0 items-start gap-2.5 sm:gap-4">
                  <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-slate-100 text-base font-bold text-slate-500 sm:h-12 sm:w-12 sm:text-xl">
                    {j.company?.name?.[0] || '?'}
                  </div>
                  <div className="min-w-0">
                    <h2 className="text-sm font-bold text-slate-800 transition-colors group-hover:text-brand-600 sm:text-lg">
                      {j.title}
                    </h2>
                    <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs text-slate-500 sm:mt-2 sm:gap-x-4 sm:text-sm">
                      <span className="flex min-w-0 items-center gap-1.5">
                        <Building className="h-4 w-4 flex-shrink-0 text-slate-400" />
                        {j.company?.name}
                      </span>
                      <span className="flex min-w-0 items-center gap-1.5">
                        <MapPin className="h-4 w-4 flex-shrink-0 text-slate-400" />
                        {j.location}
                      </span>
                      {j.remote && (
                        <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 font-medium rounded text-xs border border-emerald-100">
                          Remote
                        </span>
                      )}
                      {typeof j.ghost_risk === 'number' && j.ghost_risk >= 30 && (
                        <GhostRiskBadge score={j.ghost_risk} band={j.ghost_band} />
                      )}
                    </div>
                  </div>
                </div>
                <div className="hidden items-center text-brand-600 opacity-0 transition-opacity group-hover:opacity-100 sm:flex">
                  <span className="text-sm font-medium mr-1">View Details</span>
                  <ChevronRight className="w-5 h-5" />
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
