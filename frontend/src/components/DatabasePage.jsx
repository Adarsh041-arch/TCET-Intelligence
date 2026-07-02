import { useState, useEffect } from 'react';
import { ChevronDown, ChevronRight, Key } from 'lucide-react';
import { sqlStatus, sqlConnect, sqlDisconnect, sqlTables, sqlSchema } from '../services/api';

export default function DatabasePage() {
  const [status, setStatus] = useState({ connected: false, db_type: null });
  const [dbType, setDbType] = useState('sqlite');
  const [form, setForm] = useState({
    host: 'localhost', port: 3306, user: 'root', password: '', database: '', path: 'data/institution.db',
  });
  const [connecting, setConnecting] = useState(false);
  const [tables, setTables] = useState([]);
  const [schemas, setSchemas] = useState({});
  const [expandedTable, setExpandedTable] = useState(null);
  const [error, setError] = useState('');

  const loadStatus = async () => {
    try {
      const s = await sqlStatus();
      setStatus(s);
      if (s.connected) loadTables();
    } catch { /* silent */ }
  };

  const loadTables = async () => {
    try {
      const data = await sqlTables();
      if (data.success) setTables(data.tables || []);
    } catch { /* silent */ }
  };

  useEffect(() => { loadStatus(); }, []);

  const handleConnect = async (e) => {
    e.preventDefault();
    setConnecting(true);
    setError('');
    try {
      const payload = { db_type: dbType, ...form, port: parseInt(form.port) || 3306 };
      const res = await sqlConnect(payload);
      if (res.success) {
        loadStatus();
      } else {
        setError(res.error || 'Connection failed.');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    await sqlDisconnect();
    setStatus({ connected: false, db_type: null });
    setTables([]);
    setSchemas({});
  };

  const toggleTable = async (table) => {
    if (expandedTable === table) {
      setExpandedTable(null);
      return;
    }
    setExpandedTable(table);
    if (!schemas[table]) {
      try {
        const data = await sqlSchema(table);
        if (data.success) {
          setSchemas((prev) => ({ ...prev, [table]: data.schema }));
        }
      } catch { /* silent */ }
    }
  };

  return (
    <div className="page-container fade-in">
      <div className="page-header">
        <h1>🗄️ Database Hub</h1>
        <p>Manage SQL database connections and explore schema.</p>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '24px' }}>
        <span className={`status-dot ${status.connected ? 'online' : 'offline'}`} />
        <span style={{ color: 'var(--text-primary)', fontSize: '0.9rem' }}>
          {status.connected ? `Connected — ${(status.db_type || '').toUpperCase()}` : 'Disconnected'}
        </span>
        {status.connected && (
          <button className="btn btn-danger btn-sm" style={{ marginLeft: 'auto' }} onClick={handleDisconnect}>
            Disconnect
          </button>
        )}
      </div>

      {status.connected ? (
        <>
          <h3 style={{ color: 'var(--text-primary)', marginBottom: '16px', fontSize: '1rem' }}>
            Schema Explorer
          </h3>
          {tables.length > 0 ? tables.map((table) => (
            <div key={table} className="schema-accordion">
              <div className="schema-accordion-header" onClick={() => toggleTable(table)}>
                <span>📋 {table}</span>
                {expandedTable === table ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
              </div>
              {expandedTable === table && schemas[table] && (
                <div className="schema-accordion-body">
                  {schemas[table].columns?.map((col, i) => (
                    <div key={i} className="schema-col">
                      <span className="schema-col-name">{col.name}</span>
                      <span className="schema-col-type">({col.type})</span>
                      {col.pk ? <span className="schema-col-pk"><Key size={10} /> PK</span> : null}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )) : (
            <div className="empty-state">No tables found.</div>
          )}
        </>
      ) : (
        <>
          <h3 style={{ color: 'var(--text-primary)', marginBottom: '16px', fontSize: '1rem' }}>
            Connect Database
          </h3>

          {error && <div className="alert alert-error">{error}</div>}

          <div className="input-group">
            <label className="input-label">Database Type</label>
            <select
              className="select-field"
              value={dbType}
              onChange={(e) => setDbType(e.target.value)}
            >
              <option value="sqlite">SQLite</option>
              <option value="mysql">MySQL</option>
              <option value="postgresql">PostgreSQL</option>
            </select>
          </div>

          <form onSubmit={handleConnect}>
            {dbType === 'sqlite' ? (
              <div className="input-group">
                <label className="input-label">Database File Path</label>
                <input
                  className="input-field"
                  value={form.path}
                  onChange={(e) => setForm({ ...form, path: e.target.value })}
                  placeholder="data/institution.db"
                />
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div className="input-group">
                  <label className="input-label">Host</label>
                  <input className="input-field" value={form.host} onChange={(e) => setForm({ ...form, host: e.target.value })} />
                </div>
                <div className="input-group">
                  <label className="input-label">Port</label>
                  <input className="input-field" type="number" value={form.port} onChange={(e) => setForm({ ...form, port: e.target.value })} />
                </div>
                <div className="input-group">
                  <label className="input-label">Database</label>
                  <input className="input-field" value={form.database} onChange={(e) => setForm({ ...form, database: e.target.value })} />
                </div>
                <div className="input-group">
                  <label className="input-label">User</label>
                  <input className="input-field" value={form.user} onChange={(e) => setForm({ ...form, user: e.target.value })} />
                </div>
                <div className="input-group" style={{ gridColumn: '1 / -1' }}>
                  <label className="input-label">Password</label>
                  <input className="input-field" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
                </div>
              </div>
            )}

            <button className="btn btn-primary btn-lg" type="submit" disabled={connecting} style={{ marginTop: '8px' }}>
              {connecting ? <><span className="spinner" /> Connecting...</> : 'Initialize Connection'}
            </button>
          </form>
        </>
      )}
    </div>
  );
}
