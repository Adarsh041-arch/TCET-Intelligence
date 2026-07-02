import { useEffect, useState } from 'react';
import mermaid from 'mermaid';
import { Download } from 'lucide-react';

mermaid.initialize({ theme: 'dark', startOnLoad: false });

export default function MermaidBlock({ chart }) {
  const [svg, setSvg] = useState('');

  useEffect(() => {
    const id = `mermaid-${Math.random().toString(36).slice(2, 9)}`;
    mermaid.render(id, chart).then(({ svg }) => setSvg(svg)).catch(() => {});
  }, [chart]);

  const downloadSVG = () => {
    const blob = new Blob([svg], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'flowchart.svg';
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!svg) return null;

  return (
    <div className="mermaid-wrapper">
      <div className="code-block-header">
        <span className="code-lang">flowchart</span>
        <button onClick={downloadSVG} className="copy-btn">
          <Download size={14} /> Export
        </button>
      </div>
      <div className="mermaid-body" dangerouslySetInnerHTML={{ __html: svg }} />
    </div>
  );
}
