import { useState, useRef } from 'react';
import { Upload, FileText, CheckCircle, AlertCircle } from 'lucide-react';
import { uploadDocument } from '../services/api';

const ALLOWED = ['PDF', 'TXT', 'DOCX', 'XLSX', 'XLS', 'CSV', 'JSON', 'HTML', 'PNG', 'JPG', 'JPEG', 'GIF', 'BMP', 'WEBP'];

export default function UploadPage() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [dragover, setDragover] = useState(false);
  const inputRef = useRef(null);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragover(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) setFile(dropped);
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setResult(null);
    try {
      const res = await uploadDocument(file);
      setResult(res);
      if (res.success) setFile(null);
    } catch (err) {
      setResult({ success: false, message: err.message });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="page-container fade-in">
      <div className="page-header">
        <h1>📤 Index Documents</h1>
        <p>Upload documents to parse, chunk, and index into the persistent vector storage.</p>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '20px' }}>
        {ALLOWED.map((ext) => (
          <span key={ext} className="badge badge-general">{ext}</span>
        ))}
      </div>

      {result && (
        <div className={`alert ${result.success ? 'alert-success' : 'alert-error'}`}>
          {result.success ? <CheckCircle size={16} /> : <AlertCircle size={16} />}
          {result.success
            ? `Processed! ${result.chunks_created || 0} embedding chunks created.`
            : result.message || 'Upload failed.'
          }
        </div>
      )}

      <div
        className={`upload-zone ${dragover ? 'dragover' : ''}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragover(true); }}
        onDragLeave={() => setDragover(false)}
        onDrop={handleDrop}
      >
        <div className="upload-zone-icon"><Upload size={32} color="var(--text-tertiary)" /></div>
        <div className="upload-zone-text">
          {file ? '' : 'Drop a file here or click to browse'}
        </div>
        <div className="upload-zone-hint">
          Max 20MB · Supported: PDF, TXT, DOCX, XLSX, CSV, JSON, HTML, PNG, JPG, GIF
        </div>
        <input
          ref={inputRef}
          type="file"
          style={{ display: 'none' }}
          accept=".pdf,.txt,.docx,.xlsx,.xls,.csv,.json,.html,.png,.jpg,.jpeg,.gif,.bmp,.webp"
          onChange={(e) => { if (e.target.files[0]) setFile(e.target.files[0]); }}
        />
      </div>

      {file && (
        <div className="upload-file-preview">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <FileText size={18} color="var(--sage)" />
            <div>
              <div className="upload-file-name">{file.name}</div>
              <div className="upload-file-size">{(file.size / 1024).toFixed(1)} KB</div>
            </div>
          </div>
          <button
            className="btn btn-primary"
            onClick={handleUpload}
            disabled={uploading}
          >
            {uploading ? <><span className="spinner" /> Processing...</> : '🚀 Generate Embeddings'}
          </button>
        </div>
      )}
    </div>
  );
}
