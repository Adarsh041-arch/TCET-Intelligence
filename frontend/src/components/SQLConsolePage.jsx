import { useState } from 'react';
import { Play, AlertCircle, Table } from 'lucide-react';
import { sqlQuery } from '../services/api';

export default function SQLConsolePage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleExecute = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError('');
    setResults(null);
    try {
      const res = await sqlQuery(query);
      if (res.success) {
        setResults(res);
      } else {
        setError(res.error || 'Query failed.');
      }
    } catch (err) {
      setError(err.message || 'Failed to execute query.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-container fade-in">
      <div className="page-header">
        <h1>SQL Console</h1>
        <p>Execute raw SQL queries against the connected database.</p>
      </div>

      <form onSubmit={handleExecute}>
        <div className="input-group">
          <textarea
            className="input-field sql-editor"
            placeholder="SELECT * FROM users LIMIT 10;"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            rows={5}
            spellCheck={false}
          />
        </div>
        <button
          className="btn btn-primary btn-lg"
          type="submit"
          disabled={loading || !query.trim()}
        >
          {loading ? <><span className="spinner" /> Executing...</> : <><Play size={16} /> Execute Query</>}
        </button>
      </form>

      {error && (
        <div className="alert alert-error" style={{ marginTop: '20px' }}>
          <AlertCircle size={16} /> {error}
        </div>
      )}

      {results && results.columns && results.rows && (
        <div style={{ marginTop: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
            <Table size={16} color="var(--sage)" />
            <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
              {results.rows.length} row{results.rows.length !== 1 ? 's' : ''} returned
            </span>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table className="sql-results-table">
              <thead>
                <tr>
                  {results.columns.map((col, i) => (
                    <th key={i}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {results.rows.map((row, ri) => (
                  <tr key={ri}>
                    {results.columns.map((col, ci) => (
                      <td key={ci}>{row[col] != null ? String(row[col]) : 'NULL'}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
