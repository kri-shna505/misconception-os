export interface ProblemListItem {
  id: string;
  code: string;
  title: string;
  topic: string;
  difficulty: string | null;
  active: boolean;
}

export interface SupportedMisconception {
  id: string;
  code: string;
  name: string;
  topic: string | null;
}

export interface ProblemDetail {
  id: string;
  code: string;
  title: string;
  topic: string;
  statement: string;
  difficulty: string | null;
  expected_language: string | null;
  rule_context: Record<string, unknown> | null;
  supported_misconceptions: SupportedMisconception[];
  created_at: string;
}