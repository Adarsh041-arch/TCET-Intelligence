import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Zap } from 'lucide-react';

export default function LoginPage() {
  const { login, register } = useAuth();
  const [tab, setTab] = useState('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [regUsername, setRegUsername] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regRole, setRegRole] = useState('user');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError('Please fill in all fields.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await login(username, password);
    } catch (err) {
      setError(err.message || 'Invalid username or password.');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    if (!regUsername.trim() || !regPassword.trim()) {
      setError('Please fill in all fields.');
      return;
    }
    if (regPassword.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await register(regUsername, regPassword, regRole);
      setSuccess('Account created! Please sign in.');
      setTab('login');
      setRegUsername('');
      setRegPassword('');
    } catch (err) {
      setError(err.message || 'Username already exists.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page fade-in">
      <div className="glass-card login-card">
        <div className="login-icon"><Zap size={40} color="#8fbc8f" /></div>
        <h1 className="login-title">TCET Intelligence</h1>
        <p className="login-subtitle">Institutional RAG & SQL Decision Engine</p>

        <div className="login-tabs">
          <button
            className={`login-tab ${tab === 'login' ? 'active' : ''}`}
            onClick={() => { setTab('login'); setError(''); setSuccess(''); }}
          >
            🔒 Sign In
          </button>
          <button
            className={`login-tab ${tab === 'register' ? 'active' : ''}`}
            onClick={() => { setTab('register'); setError(''); setSuccess(''); }}
          >
            ✉️ Register
          </button>
        </div>

        {error && <div className="login-error">{error}</div>}
        {success && <div className="login-success">{success}</div>}

        {tab === 'login' ? (
          <form onSubmit={handleLogin}>
            <div className="input-group">
              <label className="input-label">Username</label>
              <input
                className="input-field"
                type="text"
                placeholder="Enter username..."
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoFocus
              />
            </div>
            <div className="input-group">
              <label className="input-label">Password</label>
              <input
                className="input-field"
                type="password"
                placeholder="Enter password..."
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            <button className="btn btn-primary btn-block btn-lg" type="submit" disabled={loading}>
              {loading ? <><span className="spinner" /> Authenticating...</> : 'Authenticate Access'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleRegister}>
            <div className="input-group">
              <label className="input-label">Choose Username</label>
              <input
                className="input-field"
                type="text"
                placeholder="e.g., student_123"
                value={regUsername}
                onChange={(e) => setRegUsername(e.target.value)}
                autoFocus
              />
            </div>
            <div className="input-group">
              <label className="input-label">Create Password</label>
              <input
                className="input-field"
                type="password"
                placeholder="Min 6 characters..."
                value={regPassword}
                onChange={(e) => setRegPassword(e.target.value)}
              />
            </div>
            <div className="input-group">
              <label className="input-label">Role</label>
              <select
                className="select-field"
                value={regRole}
                onChange={(e) => setRegRole(e.target.value)}
              >
                <option value="user">User</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <button className="btn btn-primary btn-block btn-lg" type="submit" disabled={loading}>
              {loading ? <><span className="spinner" /> Creating...</> : 'Create Account'}
            </button>
          </form>
        )}

        <p className="login-hint">
          Default Admin: <code>admin</code> / <code>admin123</code>
        </p>
      </div>
    </div>
  );
}
