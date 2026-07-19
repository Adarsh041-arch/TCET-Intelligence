import { useState, useEffect } from 'react';
import {
  FileText, File, Presentation, Table, X, Download, Eye, Loader, Zap,
} from 'lucide-react';
import { generateDocument, getDocumentFormats, getTemplates } from '../services/api';
import PreviewModal from './PreviewModal';

const FORMAT_ICONS = {
  docx: FileText,
  pdf: File,
  pptx: Presentation,
  xlsx: Table,
};

const FORMAT_NAMES = {
  docx: 'Word Document',
  pdf: 'PDF Document',
  pptx: 'PowerPoint',
  xlsx: 'Excel Spreadsheet',
};

const V2_CAPABLE = ['docx', 'pptx', 'xlsx'];

export default function ExportModal({ open, onClose, markdownContent }) {
  const [formats, setFormats] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [selectedFormat, setSelectedFormat] = useState('docx');
  const [selectedTemplate, setSelectedTemplate] = useState('default');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewData, setPreviewData] = useState(null);

  useEffect(() => {
    if (!open) {
      setResult(null);
      setError(null);
      setPreviewData(null);
      return;
    }
    getDocumentFormats().then((data) => setFormats(data.formats || [])).catch(() => {});
    getTemplates().then((data) => setTemplates(data || [])).catch(() => {});
    setSelectedFormat('docx');
    setSelectedTemplate('default');
  }, [open]);

  if (!open) return null;

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await generateDocument({
        markdown: markdownContent,
        format: selectedFormat,
        template_id: selectedTemplate,
        generator_version: V2_CAPABLE.includes(selectedFormat) ? 'v2' : 'v1',
      });
      setResult(res);
    } catch (err) {
      setError(err.message || 'Generation failed');
    } finally {
      setLoading(false);
    }
  };

  const handlePreview = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await generateDocument({
        markdown: markdownContent,
        format: selectedFormat,
        template_id: selectedTemplate,
        generator_version: V2_CAPABLE.includes(selectedFormat) ? 'v2' : 'v1',
      });
      setResult(res);
      if (res.download_url) {
        const baseUrl = 'http://192.168.29.134:8000';
        const resp = await fetch(`${baseUrl}${res.download_url}`);
        const blob = await resp.blob();
        setPreviewData({
          blob,
          format: selectedFormat,
          filename: res.filename,
          url: `${baseUrl}${res.download_url}`,
        });
        setPreviewOpen(true);
      }
    } catch (err) {
      setError(err.message || 'Preview failed');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (!result?.download_url) return;
    const baseUrl = 'http://192.168.29.134:8000';
    const a = document.createElement('a');
    a.href = `${baseUrl}${result.download_url}`;
    a.download = result.filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const handleClosePreview = () => {
    setPreviewOpen(false);
    setPreviewData(null);
  };

  return (
    <>
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal-content export-modal" onClick={(e) => e.stopPropagation()}>
          <div className="modal-header">
            <h2>Export Document</h2>
            <button className="modal-close-btn" onClick={onClose}>
              <X size={18} />
            </button>
          </div>

          <div className="modal-body">
            <div className="export-section">
              <label className="export-label">Format</label>
              <div className="format-grid">
                {formats.filter((f) => !f.id.endsWith('-v2')).map((fmt) => {
                  const Icon = FORMAT_ICONS[fmt.id] || File;
                  const isActive = selectedFormat === fmt.id;
                  return (
                    <button
                      key={fmt.id}
                      className={`format-card ${isActive ? 'active' : ''}`}
                      onClick={() => setSelectedFormat(fmt.id)}
                    >
                      <Icon size={24} />
                      <span className="format-name">{FORMAT_NAMES[fmt.id] || fmt.name}</span>
                      <span className="format-ext">{fmt.extension}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* V2 generators are now the default and only option for docx, pptx, xlsx */}

            <div className="export-section">
              <label className="export-label">Template</label>
              <select
                className="template-select"
                value={selectedTemplate}
                onChange={(e) => setSelectedTemplate(e.target.value)}
              >
                {templates.map((tpl) => (
                  <option key={tpl.id} value={tpl.id}>
                    {tpl.name}
                  </option>
                ))}
              </select>
            </div>

            {error && <div className="export-error">{error}</div>}

            {result && (
              <div className="export-result">
                <div className="export-result-icon">
                  <Download size={20} />
                </div>
                <div className="export-result-info">
                  <span className="export-result-name">{result.filename}</span>
                  <span className="export-result-size">
                    {(result.size / 1024).toFixed(1)} KB
                  </span>
                </div>
                <button className="btn btn-sm btn-secondary" onClick={handleDownload}>
                  <Download size={14} /> Download
                </button>
              </div>
            )}
          </div>

          <div className="modal-footer">
            <button
              className="btn btn-ghost"
              onClick={handlePreview}
              disabled={loading}
            >
              <Eye size={16} /> Preview
            </button>
            <button
              className="btn btn-primary"
              onClick={handleGenerate}
              disabled={loading}
            >
              {loading ? <Loader size={16} className="spin" /> : <Download size={16} />}
              {loading ? 'Generating...' : 'Generate'}
            </button>
          </div>
        </div>
      </div>

      <PreviewModal
        open={previewOpen}
        onClose={handleClosePreview}
        previewData={previewData}
      />
    </>
  );
}
