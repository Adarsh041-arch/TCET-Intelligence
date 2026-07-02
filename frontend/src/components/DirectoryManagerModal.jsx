import { useState, useEffect } from 'react';
import { X, FolderPlus, Trash2, Folder, FolderOpen } from 'lucide-react';
import { getUserDirectories, addUserDirectory, deleteUserDirectory } from '../services/api';

export default function DirectoryManagerModal({ open, onClose, onSaved }) {
  const [directories, setDirectories] = useState([]);
  const [newDir, setNewDir] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (open) loadDirectories();
  }, [open]);

  const loadDirectories = async () => {
    setLoading(true);
    try {
      const res = await getUserDirectories();
      setDirectories(res.directories || []);
    } catch {
      setError('Failed to load directories.');
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!newDir.trim()) return;
    setError('');
    setSaving(true);
    try {
      await addUserDirectory(newDir.trim());
      setNewDir('');
      await loadDirectories();
      onSaved?.();
    } catch (err) {
      setError(err.message || 'Failed to add directory.');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (dirPath) => {
    try {
      await deleteUserDirectory(dirPath);
      await loadDirectories();
      onSaved?.();
    } catch (err) {
      setError(err.message || 'Failed to delete directory.');
    }
  };

  if (!open) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content glass-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2><FolderOpen size={18} /> Allowed Directories</h2>
          <button className="modal-close-btn" onClick={onClose}><X size={18} /></button>
        </div>
        <div className="modal-body">
          <p>
            These directories are accessible to you when using the Filesystem tool.
            You can add multiple directories. All paths must be absolute.
          </p>

          {/* Existing directories */}
          {loading ? (
            <div className="alert" style={{ color: 'var(--text-tertiary)' }}>Loading...</div>
          ) : directories.length > 0 ? (
            <div className="dir-list">
              {directories.map((d) => (
                <div key={d.id} className="dir-item">
                  <Folder size={14} className="dir-item-icon" />
                  <span className="dir-item-path">{d.directory_path}</span>
                  <button
                    className="dir-item-delete"
                    onClick={() => handleDelete(d.directory_path)}
                    title="Remove directory"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="alert" style={{ color: 'var(--text-tertiary)', marginBottom: 12 }}>
              No directories configured yet.
              {!loading && ' The config default will be used as fallback.'}
            </div>
          )}

          {/* Add new directory */}
          <form onSubmit={handleAdd} className="dir-add-form">
            <div className="input-group">
              <label className="input-label">Add Directory</label>
              <div className="dir-add-row">
                <input
                  className="input-field"
                  type="text"
                  placeholder="C:/Users/you/Desktop"
                  value={newDir}
                  onChange={(e) => setNewDir(e.target.value)}
                  spellCheck={false}
                />
                <button type="submit" className="btn btn-primary btn-sm" disabled={saving || !newDir.trim()}>
                  {saving ? <span className="spinner" /> : <FolderPlus size={14} />}
                  Add
                </button>
              </div>
            </div>
          </form>

          {error && <div className="alert alert-error">{error}</div>}

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
