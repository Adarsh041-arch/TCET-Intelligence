import { useState, useEffect } from 'react';
import { ChevronDown, ChevronRight, Key, Globe, Trash2 } from 'lucide-react';
import { sqlStatus, sqlConnect, sqlDisconnect, sqlTables, sqlSchema, sqlExposeDatabase, getExposedDatabases, deleteExposedDatabase } from '../services/api';

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
  const [exposeLabel, setExposeLabel] = useState('');
  const [exposedDBs, setExposedDBs] = useState([]);
  const [exposeMsg, setExposeMsg] = useState('');
  const [showExposeForm, setShowExposeForm] = useState(false);
  const [exposeForm, setExposeForm] = useState({ db_type: 'sqlite', host: 'localhost', port: 5433, user: 'admin', password: 'admin123', database_name: 'tcet_tnp_db', path: 'data/institution.db' });

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

  const loadExposed = async () => {
    try {
      const data = await getExposedDatabases();
      if (data.success) setExposedDBs(data.databases || []);
    } catch { /* silent */ }
  };

  useEffect(() => { loadStatus(); loadExposed(); }, []);

  const handleExpose = async () => {
    if (!exposeLabel.trim()) return;
    setExposeMsg('');
    try {
      const payload = { ...exposeForm, label: exposeLabel.trim(), port: parseInt(exposeForm.port) || 5432 };
      const data = await sqlExposeDatabase(payload);
      if (data.success) {
        setExposeMsg(`✓ ${data.message}`);
        setExposeLabel('');
        loadExposed();
      } else {
        setExposeMsg(`✗ ${data.error}`);
      }
    } catch (err) {
      setExposeMsg(`✗ ${err.message}`);
    }
  };

  const handleUnexpose = async (dbId) => {
    try {
      await deleteExposedDatabase(dbId);
      loadExposed();
    } catch { /* silent */ }
  };

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
    setExposeMsg('');
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
          <div className="card" style={{ padding: '16px', marginBottom: '20px' }}>
            <h4 style={{ margin: '0 0 12px', fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Globe size={16} /> Expose to Users
            </h4>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '8px' }}>
              <input className="input-field" style={{ flex: 1 }} placeholder="Label (e.g. TNP Database)" value={exposeLabel} onChange={(e) => setExposeLabel(e.target.value)} />
              <button className={`btn btn-sm ${showExposeForm ? 'btn-secondary' : 'btn-outline'}`} onClick={() => setShowExposeForm(!showExposeForm)}>
                {showExposeForm ? 'Cancel' : 'Configure'}
              </button>
              <button className="btn btn-primary btn-sm" onClick={handleExpose} disabled={!exposeLabel.trim()}>
                Expose
              </button>
            </div>
            {showExposeForm && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', padding: '8px', background: 'var(--bg-tertiary)', borderRadius: '6px' }}>
                <select className="select-field" value={exposeForm.db_type} onChange={(e) => setExposeForm({ ...exposeForm, db_type: e.target.value })}>
                  <option value="sqlite">SQLite</option><option value="mysql">MySQL</option><option value="postgresql">PostgreSQL</option>
                </select>
                {exposeForm.db_type === 'sqlite' ? (
                  <input className="input-field" placeholder="Path" value={exposeForm.path} onChange={(e) => setExposeForm({ ...exposeForm, path: e.target.value })} />
                ) : (
                  <>
                    <input className="input-field" placeholder="Host" value={exposeForm.host} onChange={(e) => setExposeForm({ ...exposeForm, host: e.target.value })} />
                    <input className="input-field" type="number" placeholder="Port" value={exposeForm.port} onChange={(e) => setExposeForm({ ...exposeForm, port: e.target.value })} />
                    <input className="input-field" placeholder="Database" value={exposeForm.database_name} onChange={(e) => setExposeForm({ ...exposeForm, database_name: e.target.value })} />
                    <input className="input-field" placeholder="User" value={exposeForm.user} onChange={(e) => setExposeForm({ ...exposeForm, user: e.target.value })} />
                    <input className="input-field" type="password" placeholder="Password" value={exposeForm.password} onChange={(e) => setExposeForm({ ...exposeForm, password: e.target.value })} />
                  </>
                )}
              </div>
            )}
            {exposeMsg && <p style={{ fontSize: '0.85rem', margin: '8px 0 0', color: exposeMsg.startsWith('✓') ? 'var(--sage)' : 'var(--danger)' }}>{exposeMsg}</p>}
          </div>

          {exposedDBs.length > 0 && (
            <div className="card" style={{ padding: '16px', marginBottom: '20px' }}>
              <h4 style={{ margin: '0 0 8px', fontSize: '0.95rem' }}>Exposed Databases</h4>
              {exposedDBs.map((db) => (
                <div key={db.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
                  <div>
                    <strong>{db.label}</strong>
                    <span style={{ marginLeft: '8px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                      ({db.db_type.toUpperCase()}{db.database_name ? ` — ${db.database_name}` : ''})
                    </span>
                  </div>
                  <button className="btn btn-danger btn-sm" onClick={() => handleUnexpose(db.id)} title="Remove">
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
          )}

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

          <div style={{ marginBottom: '20px' }}>
            <label className="input-label" style={{ marginBottom: '8px', display: 'block' }}>Quick Connect</label>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <button
                type="button" className="btn btn-outline btn-sm"
                onClick={() => {
                  setDbType('sqlite');
                  setForm({ host: 'localhost', port: 3306, user: 'root', password: '', database: '', path: 'data/institution.db' });
                }}
              >
                ⚡ SQLite (default)
              </button>
              <button
                type="button" className="btn btn-outline btn-sm"
                onClick={() => {
                  setDbType('postgresql');
                  setForm({ host: 'localhost', port: 5433, user: 'admin', password: 'admin123', database: 'tcet_tnp_db', path: '' });
                }}
              >
                ⚡ PostgreSQL — tcet_tnp_db
              </button>
            </div>
          </div>

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
