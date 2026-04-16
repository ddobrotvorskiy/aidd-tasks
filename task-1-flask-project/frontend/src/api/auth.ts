import type { Employee, LoginPayload, RegisterPayload, TokenResponse } from '../types';
import apiClient from './client';

export const register = async (payload: RegisterPayload): Promise<Employee> => {
  const { data } = await apiClient.post<Employee>('/auth/register', payload);
  return data;
};

export const login = async (payload: LoginPayload): Promise<TokenResponse> => {
  const { data } = await apiClient.post<TokenResponse>('/auth/login', payload);
  return data;
};
