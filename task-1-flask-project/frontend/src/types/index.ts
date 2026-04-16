export interface Employee {
  id: number;
  email: string;
  full_name: string;
  job_title: string | null;
  department: string | null;
  phone: string | null;
  photo_url: string | null;
  created_at: string | null;
}

export interface EmployeeListResponse {
  items: Employee[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
  job_title?: string;
  department?: string;
  phone?: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface ProfileUpdatePayload {
  full_name?: string;
  job_title?: string;
  department?: string;
  phone?: string;
}

export interface ChangePasswordPayload {
  current_password: string;
  new_password: string;
}

export interface ApiError {
  error: string;
  code: string;
  details?: unknown[];
}
