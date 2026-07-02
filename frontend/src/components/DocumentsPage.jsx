import { useState, useEffect } from 'react';
import { Trash2, FileText, AlertCircle } from 'lucide-react';
import { getDocuments, deleteDocument } from '../services/api';

export default function DocumentsPage() {
  const [docs, setDocs] = useState({ documents: [], total_chunks: 0 });
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(null);

  const load = async () => {
    try {
      const data = await getDocuments();
      setDocs(data);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleDelete = async (docId) => {
    if (!confirm('Delete this document and its embeddings?')) return;
    setDeleting(docId);
    try {
      await deleteDocument(docId);
      load();
    } catch {
      // silent
    } finally {
      setDeleting(null);
    }
  };

  return (
    <div className="page-container fade-in">
      <div className="page-header">
        <h1>📚 Knowledge Base</h1>
        <p>View and manage all documents indexed into the RAG vector storage.</p>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-card-label">Total Chunks</div>
          <div className="stat-card-value">{docs.total_chunks}</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-label">Documents</div>
          <div className="stat-card-value">{docs.documents?.length || 0}</div>
        </div>
      </div>

      <h3 style={{ color: 'var(--text-primary)', marginBottom: '16px', fontSize: '1rem' }}>
        Indexed Documents
      </h3>

      {loading ? (
        <div className="empty-state"><span className="spinner" /> Loading...</div>
      ) : docs.documents?.length > 0 ? (
        docs.documents.map((doc) => (
          <div key={doc.doc_id} className="doc-item">
            <div className="doc-item-info">
              <h4><FileText size={14} style={{ marginRight: '6px', verticalAlign: '-2px' }} />{doc.filename}</h4>
              <div className="doc-item-meta">
                <span className="badge badge-general" style={{ marginRight: '6px' }}>{doc.file_type}</span>
                Uploaded: {doc.uploaded_at?.slice(0, 10)}
              </div>
            </div>
            <button
              className="btn btn-danger btn-sm"
              onClick={() => handleDelete(doc.doc_id)}
              disabled={deleting === doc.doc_id}
            >
              {deleting === doc.doc_id ? <span className="spinner" /> : <Trash2 size={14} />}
              Delete
            </button>
          </div>
        ))
      ) : (
        <div className="empty-state">
          <AlertCircle size={24} style={{ marginBottom: '8px' }} />
          <br />No documents in the knowledge base.
        </div>
      )}
    </div>
  );
}
