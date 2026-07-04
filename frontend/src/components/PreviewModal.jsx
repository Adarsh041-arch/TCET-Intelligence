import { X, Download } from 'lucide-react';

export default function PreviewModal({ open, onClose, previewData }) {
  if (!open || !previewData) return null;

  const { format, filename, url } = previewData;

  const handleDownload = () => {
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const renderPreview = () => {
    if (format === 'pdf') {
      return (
        <iframe
          src={url}
          className="preview-iframe"
          title="PDF Preview"
          style={{ width: '100%', height: '70vh', border: 'none', borderRadius: '8px' }}
        />
      );
    }

    if (format === 'pptx') {
      return (
        <div className="preview-pptx">
          <div className="preview-pptx-slide">
            <p>PowerPoint preview - download to view all slides</p>
          </div>
        </div>
      );
    }

    if (format === 'docx') {
      return (
        <div className="preview-docx">
          <p>Document generated successfully. Download to view.</p>
        </div>
      );
    }

    if (format === 'xlsx') {
      return (
        <div className="preview-xlsx">
          <p>Spreadsheet generated successfully. Download to view.</p>
        </div>
      );
    }

    return <p>Preview not available for this format.</p>;
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content preview-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Preview - {filename}</h2>
          <div className="modal-header-actions">
            <button className="btn btn-sm btn-secondary" onClick={handleDownload}>
              <Download size={14} /> Download
            </button>
            <button className="modal-close-btn" onClick={onClose}>
              <X size={18} />
            </button>
          </div>
        </div>
        <div className="modal-body preview-body">
          {renderPreview()}
        </div>
      </div>
    </div>
  );
}
