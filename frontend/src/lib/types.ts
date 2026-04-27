export type Category = "T1" | "T2" | "T3" | "T4" | "T5";
export type Difficulty = "easy" | "medium" | "hard";
export type RoleType = "pm" | "data" | "ai" | "other";
export type QuestionStatus =
  | "not_practiced"
  | "practiced"
  | "needs_redo"
  | "improved"
  | "skipped";
export type ExitType = "soft" | "hard_limit" | "user_end" | "skip";

export interface ResumeUploadResponse {
  id: number;
  role_type: RoleType;
  resume_json: Record<string, unknown>;
  jd_text: string | null;
  company_name: string | null;
}

export interface Question {
  id: number;
  resume_session_id: number;
  category: Category;
  text: string;
  source: string;
  difficulty: Difficulty;
  status: QuestionStatus;
  best_score: number | null;
  last_attempt_at: string | null;
  created_at: string;
}

export interface TranscriptTurn {
  role: "agent" | "user";
  text: string;
  round: number;
  kind?: "normal" | "scenario_switch" | "prompt_mode" | "system";
}

export interface DrillResponse {
  drill_id: number;
  status: "active" | "ended";
  transcript: TranscriptTurn[];
  last_agent_text: string;
  exit_type: ExitType | null;
  rubric_scores: Record<string, number> | null;
  total_score: number | null;
}

export interface RubricDimension {
  key: string;
  label: string;
  description: string;
}

export interface Rubric {
  category: Category;
  name: string;
  description: string;
  dimensions: RubricDimension[];
  threshold_complete: number;
}

export interface SingleReport {
  drill_id: number;
  question_id: number;
  question_text: string;
  category: Category;
  transcript: TranscriptTurn[];
  rubric: Rubric;
  rubric_scores: Record<string, number>;
  total_score: number;
  exit_type: ExitType;
  scenario_switch_count: number;
  prompt_mode_count: number;
  followup_rounds: number;
  exemplar_answer: string;
  improvement_suggestions: string[];
}

export interface MockSession {
  id: number;
  resume_session_id: number;
  question_ids: number[];
  current_index: number;
  drill_attempt_ids: number[];
  status: "active" | "ended";
}

export interface MockReport {
  mock_session_id: number;
  total_avg_score: number;
  category_avg_scores: Record<string, number>;
  highlights: { question_id: number; question_text: string; score: number }[];
  weaknesses: { dimension: string; avg: number; from_categories: Category[] }[];
  next_steps: string[];
  drill_summaries: {
    drill_id: number;
    question_id: number;
    question_text: string;
    category: Category;
    total_score: number;
  }[];
}
