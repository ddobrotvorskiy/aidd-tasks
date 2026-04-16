import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { login as apiLogin, register as apiRegister } from '../api/auth';
import type { LoginPayload, RegisterPayload } from '../types';

interface AuthContextValue {
  isAuthenticated: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(
    () => Boolean(localStorage.getItem('access_token'))
  );

  const login = useCallback(async (payload: LoginPayload) => {
    const { access_token } = await apiLogin(payload);
    localStorage.setItem('access_token', access_token);
    setIsAuthenticated(true);
  }, []);

  const register = useCallback(async (payload: RegisterPayload) => {
    await apiRegister(payload);
    // Auto-login after registration
    const { access_token } = await apiLogin({ email: payload.email, password: payload.password });
    localStorage.setItem('access_token', access_token);
    setIsAuthenticated(true);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('access_token');
    setIsAuthenticated(false);
  }, []);

  const value = useMemo(
    () => ({ isAuthenticated, login, register, logout }),
    [isAuthenticated, login, register, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};
