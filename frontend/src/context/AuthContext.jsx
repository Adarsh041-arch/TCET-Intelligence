import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { login as apiLogin, register as apiRegister } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const savedToken = localStorage.getItem('tcet_token');
    const savedUser = localStorage.getItem('tcet_user');
    if (savedToken && savedUser) {
      try {
        setToken(savedToken);
        setUser(JSON.parse(savedUser));
      } catch {
        localStorage.removeItem('tcet_token');
        localStorage.removeItem('tcet_user');
      }
    }
    setLoading(false);
  }, []);

  const login = useCallback(async (username, password) => {
    const data = await apiLogin(username, password);
    const userObj = {
      user_id: data.user_id,
      username: data.username,
      role: data.role,
    };
    setToken(data.access_token);
    setUser(userObj);
    localStorage.setItem('tcet_token', data.access_token);
    localStorage.setItem('tcet_user', JSON.stringify(userObj));
    return data;
  }, []);

  const register = useCallback(async (username, password, role = 'user') => {
    await apiRegister(username, password, role);
    return true;
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('tcet_token');
    localStorage.removeItem('tcet_user');
  }, []);

  if (loading) return null;

  return (
    <AuthContext.Provider value={{ user, token, login, register, logout, isAdmin: user?.role === 'admin' }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
