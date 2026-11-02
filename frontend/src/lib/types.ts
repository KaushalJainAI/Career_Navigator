// Shapes returned by the backend API (see backend/*/views.py). Keep in sync.

export type Verdict = 'strong' | 'good' | 'stretch' | 'weak';
export type ReasonKind = 'positive' | 'negative' | 'neutral';
export interface Reason { kind: ReasonKind; title: string; detail: string }

export type AppStatus =
  | 'saved' | 'tailored' | 'ready' | 'applied' | 'assessment' | 'phone' | 'onsite' | 'offer' | 'rejected' | 'withdrawn';

/** Pipeline order shown to users. 'assessment' = online test / take-home; 'phone' = interview rounds; 'onsite' = final/HR round. */
export const PIPELINE_ORDER: AppStatus[] = ['saved', 'tailored', 'ready', 'applied', 'assessment', 'phone', 'onsite', 'offer', 'rejected', 'withdrawn'];

/** GET /matching/feed/ -> { count, total_jobs, has_profile, results: FeedJob[] } */
export interface FeedJob {
  id: number;
  title: string;
  company: { id: number; name: string; domain: string };
  location: string;
  remote: boolean;
  apply_url: string;
  posted_at: string | null;
  created_at: string;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string;
  source: string;
  ghost_risk: number;
  ghost_band: 'low' | 'medium' | 'high';
  fit: number | null;          // 0..100, null when the user has no profile yet
  verdict: Verdict | null;
  matched_skills: string[];
  missing_skills: string[];
  reasons: Reason[];
  application: { id: number; status: AppStatus } | null;
}
export interface FeedResponse { count: number; total_jobs: number; has_profile: boolean; results: FeedJob[] }

/** GET /jobs/:id/ */
export interface JobDetailData {
  id: number;
  title: string;
  company: { id: number; name: string; domain: string };
  location: string;
  remote: boolean;
  apply_url: string;
  description: string;        // raw (may be HTML) — do NOT render as HTML
  description_text: string;   // clean plain text with \n paragraphs and "• " bullets — render this
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string;
  posted_at: string | null;
  ghost_risk: number;
  ghost_band: 'low' | 'medium' | 'high';
  ghost_reasons: string[];
  skills: Record<string, number>;
}

/** GET /matching/jobs/:id/  (400 {detail} if no profile) */
export interface MatchData {
  fit: number;
  score: number;
  verdict: Verdict;
  matched_skills: string[];
  missing_skills: string[];
  explanation: Reason[];
  breakdown: { skills: number | null; title: number; text: number; location: number; seniority_penalty: number };
}

/** GET /applications/  (paginated {results} or array) */
export interface Application {
  id: number;
  job: number;
  job_detail: JobDetailData;
  status: AppStatus;
  tier_used: string;
  notes: string;
  applied_at: string | null;
  follow_up_at: string | null;
  next_interview_at: string | null;  // next round date-time (assessment / interview)
  deadline: string | null;           // YYYY-MM-DD apply-by date (campus drives etc.)
  created_at: string;
  updated_at: string;
  events: { id: number; type: string; payload: Record<string, unknown>; created_at: string }[];
}

export interface ResumeContent {
  full_name: string; headline: string; email: string; phone: string; location: string; links: string[];
  summary: string;
  skills: { name: string }[];
  experiences: { title: string; company: string; location: string; start: string; end: string;
                 is_current: boolean; bullets: string[] }[];
  educations: { degree: string; field_of_study: string; institution: string; end: string; gpa: string }[];
  projects: { name: string; description: string; tech_stack?: string[] }[];
}

/** POST /tailoring/resume/ {application_id} | GET ?application_id= | PATCH /tailoring/resume/:id/ {content} */
export interface TailoredResume {
  id: number;
  application_id: number;
  content: ResumeContent;
  model_used: string;
  diff_from_master: {
    changed_sections: string[];
    summary_before: string;
    skills_moved_up: string[];
    skills_added_from_experience: string[];
    reordered_roles: string[];
    bullets_trimmed: number;
    keyword_coverage: number | null;  // 0..100
    missing_skills: string[];
    suggestions: string[];
    verification: string[];
  };
}

/** POST /tailoring/cover-letter/ {application_id} | GET ?application_id= | PATCH /tailoring/cover-letter/:id/ {content} */
export interface CoverLetter { id: number; application_id: number; content: string; model_used: string; verification?: string[] }

/** GET /applications/today/ */
export interface TodayStep {
  kind: 'setup' | 'interview' | 'follow_up' | 'apply' | 'discover' | 'deadline';
  title: string;
  detail: string;
  action: { label: string; to: string };
  application_id?: number;
}
export interface TodayData {
  setup: { has_resume: boolean; has_targets: boolean; has_jobs: boolean; complete: boolean };
  steps: TodayStep[];
  week: { applied: number; goal: number };
  stats: {
    jobs_available: number; strong_matches: number; in_progress: number; applied: number;
    responses: number; response_rate: number | null; interviewing: number; offers: number;
  };
  top_matches: FeedJob[];
  targets: string[];
}

/** GET/PATCH /profile/ */
export interface Preference {
  target_titles: string[]; locations: string[]; remote: boolean; salary_min: number | null;
  seniority: string; keywords: string[]; exclude_companies: string[]; work_auth: string;
  stealth_mode: boolean; watch_companies: string[]; weekly_goal: number;
}

/** POST /resumes/ (multipart file) or /resumes/import-text/ {text} */
export interface ResumeUploadResult {
  id: number; label: string; parse_status: 'pending' | 'done' | 'failed'; parse_error: string; is_master: boolean;
  parsed_json: Record<string, unknown> | null;
  profile_update: { changed: string[]; added_skills: string[] };
}

/** POST /jobs/refresh/ */
export interface RefreshResult { sources: { source: string; fetched: number; kept: number; created: number; updated: number; ok: boolean }[]; new_jobs: number }

/** Interview: POST /interview/sessions/ {application?, role?, stage} ; POST /:id/answer/ {answer} ; POST /:id/report/ */
export interface InterviewQuestion { id: number; prompt: string; category: string; order: number }
export interface InterviewSession {
  id: number; role: string; stage: string; status: string; job: number | null; company: number | null;
  questions: InterviewQuestion[]; started_at: string;
}
export interface InterviewTurn {
  id: number; question: number; user_answer: string; score: number; feedback: string;
  evaluation: { structure: number; specificity: number; outcome: number; ownership?: number; score: number;
                feedback: string; strengths?: string[]; gaps?: string[] };
}
export interface InterviewReport { overall_score: number; strengths: string[]; gaps: string[]; study_plan: { topic: string; action: string }[] }

export const STATUS_LABEL: Record<AppStatus, string> = {
  saved: 'Saved', tailored: 'Materials ready', ready: 'Ready to apply', applied: 'Applied',
  assessment: 'Online assessment', phone: 'Interviewing', onsite: 'Final / HR round', offer: 'Offer',
  rejected: 'Rejected', withdrawn: 'Withdrawn',
};

/** POST /interview/sessions/ stage values. */
export const INTERVIEW_STAGES: { value: string; label: string; hint: string }[] = [
  { value: 'tech_phone', label: 'Technical interview', hint: 'Your projects, skills from the JD, problem solving' },
  { value: 'cs_fundamentals', label: 'CS fundamentals', hint: 'DBMS, OS, OOP, networks, SQL — common in campus interviews' },
  { value: 'hr', label: 'HR round', hint: 'Tell me about yourself, why us, strengths, relocation' },
  { value: 'behavioral', label: 'Behavioural', hint: 'Teamwork, conflict, failure, leadership (STAR)' },
  { value: 'recruiter', label: 'Recruiter screen', hint: 'Background, motivation, expectations' },
  { value: 'system_design', label: 'System design', hint: 'For experienced roles' },
];

/** Copilot chat. POST /agent/copilot/ {message, session_id?} -> CopilotTurn */
export interface CopilotUi { type: 'link' | 'navigate'; label?: string; to: string }
export interface CopilotPending { id: string; tool: string; args: Record<string, unknown>; summary: string }
export interface CopilotTurn {
  session_id: number; message_id: number; reply: string;
  steps: { tool: string; args: Record<string, unknown>; ok: boolean; error?: string | null }[];
  ui: CopilotUi[]; pending_action: CopilotPending | null; mode: string;  // 'rules' or the LLM label
}
/** GET /agent/copilot/latest/ or /agent/copilot/:id/ */
export interface CopilotSession {
  id: number | null; status: string; pending_action: CopilotPending | null;
  messages: { id: number; role: 'user' | 'assistant'; content: string;
              meta: { steps?: CopilotTurn['steps']; ui?: CopilotUi[]; pending_action?: CopilotPending | null }[];
              created_at: string }[];
}
