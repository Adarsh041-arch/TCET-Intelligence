import { useState } from 'react';
import { X, ExternalLink, Key, CheckCircle } from 'lucide-react';
import { saveApiKey } from '../services/api';

export default function ApiKeyModal({ open, onClose, onSaved }) {
  const [apiKey, setApiKey] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  if (!open) return null;

  const handleSave = async (e) => {
    e.preventDefault();
    if (!apiKey.trim()) {
      setError('Please enter an API key.');
      return;
    }
    setError('');
    setSaving(true);
    try {
      await saveApiKey(apiKey.trim());
      onSaved();
    } catch (err) {
      setError(err.message || 'Failed to save API key.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content glass-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2><Key size={18} /> Configure Web Search</h2>
          <button className="modal-close-btn" onClick={onClose}><X size={18} /></button>
        </div>
        <div className="modal-body">
          <p>
            Web search uses the <strong>Tavily</strong> API to fetch real-time information from the internet.
            You need a Tavily API key to use this feature.
          </p>
          <ol className="modal-steps">
            <li>
              Go to{' '}
              <a
                href="https://tavily.com"
                target="_blank"
                rel="noopener noreferrer"
                className="modal-link"
              >
                tavily.com <ExternalLink size={12} />
              </a>
              {' '}and sign up for a free account.
            </li>
            <li>Generate an API key from your dashboard.</li>
            <li>Paste the key below and save.</li>
          </ol>
          <form onSubmit={handleSave}>
            <div className="input-group">
              <label className="input-label">Tavily API Key</label>
              <input
                className="input-field"
                type="text"
                placeholder="tvly-..."
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                autoFocus
                spellCheck={false}
              />
            </div>
            {error && <div className="alert alert-error">{error}</div>}
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" onClick={onClose} disabled={saving}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? <><span className="spinner" /> Saving...</> : <><CheckCircle size={16} /> Save Key</>}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
