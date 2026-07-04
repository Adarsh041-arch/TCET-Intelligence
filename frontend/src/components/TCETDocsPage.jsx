import { useState, useEffect } from 'react';
import { FileText, CheckCircle, Clock, RefreshCw, Upload, AlertCircle } from 'lucide-react';
import { getTcetDocs, indexTcetDocs } from '../services/api';

export default function TCETDocsPage() {
  const [data, setData] = useState({ files: [], total: 0, indexed: 0, unindexed: 0 });
  const [loading, setLoading] = useState(true);
  const [indexing, setIndexing] = useState(false);
  const [selected, setSelected] = useState({});
  const [result, setResult] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const res = await getTcetDocs();
      setData(res);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const toggleSelect = (fileName) => {
    setSelected((prev) => ({ ...prev, [fileName]: !prev[fileName] }));
  };

  const handleIndex = async () => {
    const fileNames = Object.keys(selected).filter((k) => selected[k]);
    if (fileNames.length === 0) return;
    setIndexing(true);
    setResult(null);
    try {
      const res = await indexTcetDocs(fileNames);
      setResult(res);
      setSelected({});
      load();
    } catch (err) {
      setResult({ results: [{ success: false, message: err.message }] });
    } finally {
      setIndexing(false);
    }
  };

  const selectedCount = Object.values(selected).filter(Boolean).length;

  return (
    <div className="page-container fade-in">
      <div className="page-header">
        <h1>📄 TCET Document Indexing</h1>
        <p>
          Place files in <code>data/tcet_docs/</code> on the server. Scan the directory,
          then select unindexed files to process them through split → chunk → embed → vector storage.
          These documents are used in <strong>TCET ONLY</strong> mode.
        </p>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-card-label">Total Files</div>
          <div className="stat-card-value">{data.total}</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-label">Indexed</div>
          <div className="stat-card-value" style={{ color: 'var(--sage)' }}>{data.indexed}</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-label">Unindexed</div>
          <div className="stat-card-value" style={{ color: data.unindexed > 0 ? '#fbbf24' : undefined }}>{data.unindexed}</div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
        <button className="btn btn-primary" onClick={load} disabled={loading}>
          <RefreshCw size={14} /> Rescan Directory
        </button>
        {selectedCount > 0 && (
          <button
            className="btn btn-primary"
            onClick={handleIndex}
            disabled={indexing}
          >
            {indexing ? <><span className="spinner" /> Indexing...</> : <><Upload size={14} /> Index Selected ({selectedCount})</>}
          </button>
        )}
      </div>

      {result && (
        <div style={{ marginBottom: '20px' }}>
          {result.results?.map((r, i) => (
            <div key={i} className={`alert ${r.success ? 'alert-success' : 'alert-error'}`}>
              {r.success ? <CheckCircle size={16} /> : <AlertCircle size={16} />}
              {r.file_name}: {r.success ? `Indexed (${r.chunks_created || 0} chunks)` : r.message}
            </div>
          ))}
        </div>
      )}

      {loading ? (
        <div className="empty-state"><span className="spinner" /> Scanning...</div>
      ) : data.files?.length > 0 ? (
        data.files.map((f) => (
          <div key={f.file_name} className="doc-item" style={{ opacity: f.indexed ? 0.7 : 1 }}>
            <div className="doc-item-info">
              <h4><FileText size={14} style={{ marginRight: '6px', verticalAlign: '-2px' }} />{f.file_name}</h4>
              <div className="doc-item-meta">
                {(f.file_size / 1024).toFixed(1)} KB
                {f.indexed ? (
                  <span className="badge badge-general" style={{ marginLeft: '8px', background: 'rgba(52, 211, 153, 0.15)', color: '#34d399' }}>
                    ✅ Indexed
                  </span>
                ) : (
                  <span className="badge badge-general" style={{ marginLeft: '8px', background: 'rgba(251, 191, 36, 0.15)', color: '#fbbf24' }}>
                    ⏳ Pending
                  </span>
                )}
              </div>
            </div>
            {!f.indexed && (
              <label className="checkbox-label" style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={!!selected[f.file_name]}
                  onChange={() => toggleSelect(f.file_name)}
                />
                <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Index</span>
              </label>
            )}
          </div>
        ))
      ) : (
        <div className="empty-state">
          <AlertCircle size={24} style={{ marginBottom: '8px' }} />
          <br />No files in data/tcet_docs/. Add files to the directory and rescan.
        </div>
      )}
    </div>
  );
}
