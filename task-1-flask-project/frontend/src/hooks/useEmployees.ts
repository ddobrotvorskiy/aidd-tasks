import { useQuery } from '@tanstack/react-query';
import { getEmployee, getEmployees, getMyProfile } from '../api/employees';

export const useEmployees = (page: number, perPage: number, search?: string) =>
  useQuery({
    queryKey: ['employees', page, perPage, search],
    queryFn: () => getEmployees(page, perPage, search),
  });

export const useEmployee = (id: number) =>
  useQuery({
    queryKey: ['employee', id],
    queryFn: () => getEmployee(id),
    enabled: id > 0,
  });

export const useMyProfile = () =>
  useQuery({
    queryKey: ['my-profile'],
    queryFn: getMyProfile,
  });
