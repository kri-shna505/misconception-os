export type AuthenticatedUserRole =
  | "teacher"
  | "admin";

export interface AuthenticatedUser {
  id: string;
  email: string;
  display_name: string;
  role: AuthenticatedUserRole;
  is_active: boolean;
  last_login_at: string | null;
  password_changed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: AuthenticatedUser;
}