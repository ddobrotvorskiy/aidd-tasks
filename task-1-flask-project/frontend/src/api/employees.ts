import type {
  ChangePasswordPayload,
  Employee,
  EmployeeListResponse,
  ProfileUpdatePayload,
} from '../types';
import apiClient from './client';

export const getEmployees = async (
  page = 1,
  perPage = 20,
  search?: string
): Promise<EmployeeListResponse> => {
  const params: Record<string, unknown> = { page, per_page: perPage };
  if (search) params.search = search;
  const { data } = await apiClient.get<EmployeeListResponse>('/', { params });
  return data;
};

export const getEmployee = async (id: number): Promise<Employee> => {
  const { data } = await apiClient.get<Employee>(`/${id}`);
  return data;
};

export const getMyProfile = async (): Promise<Employee> => {
  const { data } = await apiClient.get<Employee>('/profile/me');
  return data;
};

export const updateMyProfile = async (payload: ProfileUpdatePayload): Promise<Employee> => {
  const { data } = await apiClient.patch<Employee>('/profile/me', payload);
  return data;
};

export const uploadPhoto = async (file: File): Promise<{ photo_url: string }> => {
  const formData = new FormData();
  formData.append('photo', file);
  const { data } = await apiClient.post<{ photo_url: string }>('/profile/me/photo', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
};

export const changePassword = async (payload: ChangePasswordPayload): Promise<void> => {
  await apiClient.post('/profile/me/change-password', payload);
};
