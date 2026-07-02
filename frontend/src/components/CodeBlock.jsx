import { useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check } from 'lucide-react';

export default function CodeBlock({ language, value }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const lineCount = value.split('\n').length;
  const showLines = lineCount > 10;

  return (
    <div className="code-block-wrapper">
      <div className="code-block-header">
        <span className="code-lang">{language || 'text'}</span>
        <button onClick={handleCopy} className="copy-btn">
          {copied ? <Check size={14} /> : <Copy size={14} />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <div className="code-block-body">
        <SyntaxHighlighter
          language={language || 'text'}
          style={vscDarkPlus}
          showLineNumbers={showLines}
          wrapLines
          customStyle={{
            margin: 0,
            borderRadius: '0 0 8px 8px',
            fontSize: '0.82rem',
          }}
          lineNumberStyle={{
            minWidth: '2.5em',
            paddingRight: '1em',
            color: '#555',
            userSelect: 'none',
          }}
        >
          {value}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}
