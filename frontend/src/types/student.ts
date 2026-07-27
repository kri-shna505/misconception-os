export interface StudentSessionCreate {
  alias: string;
  consent_status: boolean;
}

export interface StudentSessionResponse {
  student_alias_id: string;
  alias: string;
  pseudonymous_id: string;
  consent_status: boolean;
  created_at: string;
}