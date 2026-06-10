/** Shapes shared between content scripts, background, and tests.
 *  Must mirror backend/extension_api/serializers.py. */

export type ParserId =
  | 'linkedin'
  | 'greenhouse'
  | 'lever'
  | 'naukri'
  | 'unstop'
  | 'mercor';

export interface ParsedCompany {
  name: string;
  domain?: string;
  ats_type?: string;
}

export interface ParsedPosting {
  parser: ParserId;
  external_id: string;
  title: string;
  description?: string;
  location?: string;
  remote?: boolean;
  salary_min?: number | null;
  salary_max?: number | null;
  salary_currency?: string;
  apply_url?: string;
  company: ParsedCompany;
  raw?: Record<string, unknown>;
}

export interface AutofillPayload {
  application_id: number | null;
  fields: Record<string, string>;
  field_confidence: Record<string, number>;
}

export interface AutofillResult {
  filled: Record<string, string>;
  skipped: Record<string, string>;
}

export interface ParsedExperience {
  company_name: string;
  company_domain?: string;
  title?: string;
  started_at?: string | null;
  ended_at?: string | null;
  is_current?: boolean;
  raw?: Record<string, unknown>;
}

export interface ParsedProfile {
  profile_url: string;
  name: string;
  headline?: string;
  location?: string;
  email?: string;
  experiences?: ParsedExperience[];
  raw?: Record<string, unknown>;
}

export interface PostingParser {
  id: ParserId;
  detect(url: string): boolean;
  parse(doc: Document, url: string): ParsedPosting | null;
}

export interface ProfileParser {
  detect(url: string): boolean;
  parse(doc: Document, url: string): ParsedProfile | null;
}

export type RuntimeMessage =
  | { type: 'page-context'; posting: ParsedPosting }
  | { type: 'profile-context'; profile: ParsedProfile }
  | { type: 'submit-event'; payload: Record<string, unknown> };
