import { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Send, Square, Paperclip, ChevronDown, ChevronRight, ChevronDownCircle,
  FileText, Sparkles, BookOpen, Database, Folder, Globe, Copy,
  Search, CheckCircle, Download, Eye,
} from 'lucide-react';
import { getHistory, chatStream, readSSEStream, uploadDocument, getApiKeyStatus, getUserDirectories } from '../services/api';
import CodeBlock from './CodeBlock';
import MermaidBlock from './MermaidBlock';
import ApiKeyModal from './ApiKeyModal';
import DirectoryManagerModal from './DirectoryManagerModal';
import ExportModal from './ExportModal';

function formatTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function Markdown({ content, isUser }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: ({ children }) => <h1 style={{ color: isUser ? 'inherit' : undefined }}>{children}</h1>,
        h2: ({ children }) => <h2 style={{ color: isUser ? 'inherit' : undefined }}>{children}</h2>,
        h3: ({ children }) => <h3 style={{ color: isUser ? 'inherit' : undefined }}>{children}</h3>,
        strong: ({ children }) => <strong style={{ color: isUser ? 'inherit' : undefined }}>{children}</strong>,
        code({ inline, className, children }) {
          const match = /language-(\w+)/.exec(className || '');
          const value = String(children).replace(/\n$/, '');
          if (inline) return <code className="inline-code">{children}</code>;
          if (match && match[1] === 'mermaid') return <MermaidBlock chart={value} />;
          return <CodeBlock language={match ? match[1] : undefined} value={value} />;
        },
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

export default function ChatPanel({ sessionId, onSessionUpdate }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState('');
  const [_streamMeta, setStreamMeta] = useState(null);
  const [expandedDocs, setExpandedDocs] = useState({});
  const [files, setFiles] = useState([]);
  const [activeModes, setActiveModes] = useState([]);
  const [thinking, setThinking] = useState(false);
  const [thinkingSteps, setThinkingSteps] = useState([]);
  const [milestones, setMilestones] = useState([]);
  const [showScrollBtn, setShowScrollBtn] = useState(false);
  const [toast, setToast] = useState(null);
  const messagesEndRef = useRef(null);
  const controllerRef = useRef(null);
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);
  const chatContainerRef = useRef(null);
  const messageCache = useRef({});
  const streamedRef = useRef('');
  const [webKeyStatus, setWebKeyStatus] = useState(null);
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [userDirs, setUserDirs] = useState([]);
  const [showDirModal, setShowDirModal] = useState(false);
  const [exportModalOpen, setExportModalOpen] = useState(false);
  const [exportContent, setExportContent] = useState('');

  // Fetch web search API key status
  useEffect(() => {
    if (!sessionId) return;
    getApiKeyStatus()
      .then((res) => setWebKeyStatus(res))
      .catch(() => setWebKeyStatus(null));
  }, [sessionId]);

  // Load user directories
  const loadDirectories = useCallback(async () => {
    try {
      const res = await getUserDirectories();
      setUserDirs(res.directories || []);
    } catch {}
  }, []);

  useEffect(() => {
    if (!sessionId) return;
    loadDirectories();
  }, [sessionId, loadDirectories]);

  // Load history when session changes
  useEffect(() => {
    if (!sessionId) {
      setMessages([]);
      return;
    }

    // Load from cache instantly, then refresh from API
    if (messageCache.current[sessionId]) {
      setMessages(messageCache.current[sessionId]);
    }

    getHistory(sessionId).then((msgs) => {
      messageCache.current[sessionId] = msgs;
      setMessages(msgs);
    }).catch(() => {});
  }, [sessionId]);

  // Auto-scroll + detect user scroll up
  useEffect(() => {
    const container = chatContainerRef.current;
    if (!container) return;
    const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 150;
    if (isNearBottom) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      setShowScrollBtn(false);
    }
  }, [messages, streamText]);

  const handleScroll = useCallback(() => {
    const container = chatContainerRef.current;
    if (!container) return;
    const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 150;
    setShowScrollBtn(!isNearBottom);
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    setShowScrollBtn(false);
  };

  // Focus input after streaming ends
  useEffect(() => {
    if (!streaming) inputRef.current?.focus();
  }, [streaming]);

  const handleStop = useCallback(() => {
    controllerRef.current?.abort();
    const partial = streamedRef.current;
    if (partial) {
      const interruptedMsg = {
        role: 'assistant',
        content: partial + '\n\n*(Generation stopped)*',
        source: null,
        response_time: null,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => {
        const updated = [...prev, interruptedMsg];
        messageCache.current[sessionId] = updated;
        return updated;
      });
      streamedRef.current = '';
    }
    setStreaming(false);
    setThinking(false);
  }, [sessionId]);

  const handleSend = useCallback(async (overrideMessage) => {
    const msg = overrideMessage || input.trim();
    if (!msg || !sessionId || streaming) return;

    setInput('');
    setStreamText('');
    setStreamMeta(null);
    setThinkingSteps([]);
    setMilestones([]);

    // Upload any attached files first
    let attachedFileNames = null;
    if (files.length > 0) {
      attachedFileNames = [];
      for (const file of files) {
        try {
          await uploadDocument(file);
          attachedFileNames.push(file.name);
        } catch {
          // silently skip failed uploads
        }
      }
      setFiles([]);
    }

    // Optimistic add user message
    const userMsg = { role: 'user', content: msg, created_at: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg]);
    setStreaming(true);
    setThinking(true);

    try {
      const { promise, controller } = chatStream(sessionId, msg, attachedFileNames, activeModes);
      controllerRef.current = controller;

      const response = await promise;
      if (!response.ok) {
        throw new Error('Stream connection failed');
      }

      let accumulated = '';
      let meta = null;

      let documentInfo = null;

      for await (const data of readSSEStream(response)) {
        if (data.done) {
          meta = data;
          break;
        }
        if (data.thinking) {
          setThinkingSteps((prev) => [...prev, data.thinking]);
          continue;
        }
        if (data.milestone) {
          setMilestones((prev) => [...prev, data.milestone]);
          continue;
        }
        if (data.token) {
          if (thinking) setThinking(false);
          accumulated += data.token;
          streamedRef.current = accumulated;
          setStreamText(accumulated);
        }
        if (data.type === 'document') {
          documentInfo = {
            download_url: data.download_url,
            preview_url: data.preview_url,
            format: data.format,
            filename: data.filename,
            size: data.size,
          };
        }
      }

      // Finalize: add assistant message
      const assistantMsg = {
        role: 'assistant',
        content: accumulated,
        source: meta?.source,
        response_time: meta?.response_time,
        retrieved_docs: meta?.retrieved_docs,
        document: documentInfo,
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => {
        const updated = [...prev, assistantMsg];
        messageCache.current[sessionId] = updated;
        return updated;
      });
      setStreamMeta(meta);
      onSessionUpdate?.();

    } catch (err) {
      if (err.name === 'AbortError') {
        const partial = streamedRef.current;
        if (partial) {
          const interruptedMsg = {
            role: 'assistant',
            content: partial + '\n\n*(Generation stopped)*',
            source: null,
            response_time: null,
            created_at: new Date().toISOString(),
          };
          setMessages((prev) => {
            const updated = [...prev, interruptedMsg];
            messageCache.current[sessionId] = updated;
            return updated;
          });
          streamedRef.current = '';
        }
      } else {
        const errMsg = { role: 'assistant', content: 'Connection failed. Please ensure the backend is running.' };
        setMessages((prev) => [...prev, errMsg]);
      }
    } finally {
      setStreaming(false);
      setStreamText('');
      controllerRef.current = null;
      streamedRef.current = '';
    }
  }, [input, sessionId, streaming, files, activeModes, onSessionUpdate]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
    }
  };

  const toggleDocs = (idx) => {
    setExpandedDocs((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(null), 2000);
  };

  const copyMessage = (text) => {
    navigator.clipboard.writeText(text);
    showToast('Copied to clipboard');
  };

  // No session selected
  if (!sessionId) {
    return (
      <div className="chat-container">
        <div className="chat-welcome">
          <div className="chat-welcome-icon">👋</div>
          <h2>Welcome to TCET Intelligence</h2>
          <p>
            Start a new conversation to ask questions about college documents,
            query databases, or interact with the RAG knowledge base.
          </p>
        </div>
      </div>
    );
  }

  // Has session, show chat
  const allMessages = messages;
  const isEmpty = allMessages.length === 0 && !streaming;

  const suggestions = [
    { title: '📄 Analyze syllabus structure', desc: 'Summarize structural changes in uploaded documents.' },
    { title: '🏫 IT course information', desc: 'List details about Information Technology courses.' },
    { title: '📊 Student attendance data', desc: 'Query attendance patterns from the database.' },
    { title: '📁 Knowledge base summary', desc: 'Get an overview of all indexed documents.' },
  ];

  return (
    <div className="chat-container">
      <div className="chat-messages" ref={chatContainerRef} onScroll={handleScroll}>
        <div className="chat-messages-inner">
          {isEmpty && (
          <div className="chat-welcome">
            <Sparkles size={36} color="#8fbc8f" />
            <h2>How can I help you today?</h2>
            <p>Select a template query or type your own question below.</p>
            <div className="suggestions-grid">
              {suggestions.map((s, i) => (
                <div
                  key={i}
                  className="suggestion-card"
                  onClick={() => handleSend(s.title)}
                >
                  <div className="suggestion-card-title">{s.title}</div>
                  <div className="suggestion-card-desc">{s.desc}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {allMessages.map((msg, idx) => (
          <div key={idx} className={`message message-${msg.role}`}>
            <div className="message-avatar">
              {msg.role === 'user' ? 'U' : 'AI'}
            </div>
            <div className="message-body">
              <div className="message-content">
                <Markdown content={msg.content} isUser={msg.role === 'user'} />
              </div>
              <div className="message-meta">
                {msg.created_at && (
                  <span className="message-time">{formatTime(msg.created_at)}</span>
                )}
                {msg.role === 'assistant' && msg.source && (
                  <span className={`badge badge-${msg.source}`}>{msg.source}</span>
                )}
                {msg.role === 'assistant' && msg.response_time != null && (
                  <span className="badge badge-general">
                    {msg.response_time >= 1 ? `${msg.response_time.toFixed(2)}s` : `${(msg.response_time * 1000).toFixed(0)}ms`}
                  </span>
                )}
              </div>
              <div className="message-actions">
                {msg.role === 'assistant' && (
                  <button
                    className="msg-action-btn"
                    onClick={() => { setExportContent(msg.content); setExportModalOpen(true); }}
                    title="Export as document"
                  >
                    <FileText size={13} />
                  </button>
                )}
                <button className="msg-action-btn" onClick={() => copyMessage(msg.content)} title="Copy message">
                  <Copy size={13} />
                </button>
              </div>
              {msg.retrieved_docs?.length > 0 && (
                <div>
                  <button
                    className="retrieved-docs-toggle"
                    onClick={() => toggleDocs(idx)}
                  >
                    {expandedDocs[idx] ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                    {msg.retrieved_docs.length} source{msg.retrieved_docs.length > 1 ? 's' : ''} retrieved
                  </button>
                  {expandedDocs[idx] && (
                    <div className="retrieved-docs-list">
                      {msg.retrieved_docs.map((doc, di) => (
                        <div key={di} className="retrieved-doc-item">
                          <div className="retrieved-doc-header">
                            <span className="retrieved-doc-filename">
                              {doc.url ? (
                                <a
                                  href={doc.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  style={{
                                    color: 'var(--sage)',
                                    textDecoration: 'underline',
                                    fontWeight: '500',
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '4px'
                                  }}
                                >
                                  <FileText size={12} /> {doc.filename}
                                </a>
                              ) : (
                                <>
                                  <FileText size={12} /> {doc.filename}
                                </>
                              )}
                            </span>
                            <span className="retrieved-doc-score">
                              {(doc.similarity * 100).toFixed(1)}% match
                            </span>
                          </div>
                          <div className="retrieved-doc-content">{doc.content}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
              {msg.document && (
                <div className="document-result" style={{ marginTop: '8px', padding: '10px', background: 'var(--bg-secondary)', borderRadius: '8px', border: '1px solid var(--border)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                    <FileText size={16} color="var(--sage)" />
                    <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>{msg.document.filename}</span>
                    {msg.document.size && (
                      <span style={{ color: 'var(--text-tertiary)', fontSize: '0.75rem' }}>
                        {(msg.document.size / 1024).toFixed(1)} KB
                      </span>
                    )}
                  </div>
                  <div style={{ display: 'flex', gap: '6px' }}>
                    <a
                      href={`http://192.168.29.134:8000${msg.document.download_url}`}
                      download={msg.document.filename}
                      className="btn btn-sm btn-primary"
                      style={{ textDecoration: 'none', fontSize: '0.78rem' }}
                    >
                      <Download size={13} /> Download
                    </a>
                    {msg.document.preview_url && (
                      <button
                        className="btn btn-sm btn-ghost"
                        onClick={() => {
                          const baseUrl = 'http://192.168.29.134:8000';
                          fetch(`${baseUrl}${msg.document.preview_url}`)
                            .then(r => r.blob())
                            .then(blob => {
                              const url = URL.createObjectURL(blob);
                              window.open(url, '_blank');
                            })
                            .catch(() => {});
                        }}
                        style={{ fontSize: '0.78rem' }}
                      >
                        <Eye size={13} /> Preview
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Streaming in progress — shows thinking trace + milestones + token stream */}
        {streaming && (thinkingSteps.length > 0 || milestones.length > 0 || streamText || thinking) && (
          <div className="message message-assistant">
            <div className="message-avatar">AI</div>
            <div className="message-body">
              {milestones.length > 0 && (
                <div className="milestone-list">
                  {milestones.map((ms, i) => (
                    <div key={i} className="milestone-item">
                      <span className="milestone-icon">✦</span>
                      <span className="milestone-text">{ms}</span>
                    </div>
                  ))}
                </div>
              )}
              {thinkingSteps.length > 0 && (
                <div className="thinking-trace">
                  {thinkingSteps.map((step, i) => (
                    <div key={i} className="thinking-trace-line">{step}</div>
                  ))}
                </div>
              )}
              {thinking && !streamText && thinkingSteps.length === 0 && (
                <div className="message-content">
                  <div className="thinking-dots">
                    <span className="thinking-dot" />
                    <span className="thinking-dot" />
                    <span className="thinking-dot" />
                  </div>
                </div>
              )}
              {streamText && (
                <div className="message-content">
                  <Markdown content={streamText} />
                  <span className="streaming-cursor" />
                </div>
              )}
            </div>
          </div>
        )}

        {/* Scroll to bottom button */}
        {showScrollBtn && (
          <button className="scroll-to-bottom-btn" onClick={scrollToBottom}>
            <ChevronDownCircle size={20} />
          </button>
        )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="chat-input-area">
        <div className="chat-input-area-inner">
        {files.length > 0 && (
          <div style={{ marginBottom: '8px', display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {files.map((f, i) => (
              <span key={i} className="file-badge">
                <Paperclip size={12} /> {f.name}
                <button
                  onClick={() => setFiles(files.filter((_, j) => j !== i))}
                  style={{ background: 'none', border: 'none', color: 'var(--text-tertiary)', cursor: 'pointer', padding: '0 2px', fontSize: '0.9rem' }}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}

        {/* Mode toggles — multi-select with mutual-exclusivity rules */}
        <div className="mode-toggles">
          <button
            className={`mode-chip ${activeModes.includes('rag') ? 'active' : ''}`}
            data-mode="rag"
            onClick={() => {
              setActiveModes((prev) => {
                if (prev.includes('rag')) return prev.filter((x) => x !== 'rag');
                return [...prev.filter((x) => x !== 'general'), 'rag'];
              });
            }}
            title="Search indexed college documents"
          >
            <BookOpen size={13} /> TCET ONLY
          </button>
          <button
            className={`mode-chip ${activeModes.includes('sql') ? 'active' : ''}`}
            data-mode="sql"
            onClick={() => {
              setActiveModes((prev) =>
                prev.includes('sql') ? prev.filter((x) => x !== 'sql') : [...prev, 'sql']
              );
            }}
            title="Query connected databases"
          >
            <Database size={13} /> SQL
          </button>
          <div className="mode-chip-group">
            <button
              className={`mode-chip ${activeModes.includes('filesystem') ? 'active' : ''}`}
              data-mode="filesystem"
              onClick={() => {
                setActiveModes((prev) =>
                  prev.includes('filesystem') ? prev.filter((x) => x !== 'filesystem') : [...prev, 'filesystem']
                );
              }}
              title="Read and write files"
            >
              <Folder size={13} /> Filesystem
              {userDirs.length > 0 ? (
                <span className="dir-count-badge">{userDirs.length}</span>
              ) : null}
              <span
                className="dir-manage-trigger"
                onClick={(e) => { e.stopPropagation(); setShowDirModal(true); }}
                title="Manage allowed directories"
              >
                <Folder size={11} />
              </span>
            </button>
          </div>
          <button
            className={`mode-chip ${activeModes.includes('documentation') ? 'active' : ''}`}
            data-mode="documentation"
            onClick={() => {
              setActiveModes((prev) =>
                prev.includes('documentation') ? prev.filter((x) => x !== 'documentation') : [...prev, 'documentation']
              );
            }}
            title="Generate documents from chat"
          >
            <FileText size={13} /> Documentation
          </button>
          <button
            className={`mode-chip ${activeModes.includes('general') ? 'active' : ''}`}
            data-mode="general"
            onClick={() => {
              setActiveModes((prev) => {
                if (prev.includes('general')) return prev.filter((x) => x !== 'general');
                return [...prev.filter((x) => x !== 'rag'), 'general'];
              });
            }}
            title="General conversation"
          >
            <Globe size={13} /> General
          </button>
          <button
            className={`mode-chip ${activeModes.includes('web') ? 'active' : ''}`}
            data-mode="web"
            onClick={() => {
              if (!webKeyStatus?.has_key) {
                setShowKeyModal(true);
              } else {
                setActiveModes((prev) =>
                  prev.includes('web') ? prev.filter((x) => x !== 'web') : [...prev, 'web']
                );
              }
            }}
            title={webKeyStatus?.has_key ? 'Search the web (configured)' : 'Configure web search'}
          >
            <Search size={13} /> Web{webKeyStatus?.has_key ? <CheckCircle size={13} className="green-tick" /> : null}
          </button>
          {activeModes.length > 1 && (
            <span className="multi-mode-badge" title="Multi-mode active: the AI will plan and coordinate across selected tools">
              <Sparkles size={13} /> Multi
            </span>
          )}
        </div>

        <div className="chat-input-wrapper">
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => fileInputRef.current?.click()}
            title="Attach file"
            style={{ padding: '6px' }}
          >
            <Paperclip size={16} />
          </button>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileSelect}
            multiple
            style={{ display: 'none' }}
            accept=".pdf,.txt,.docx,.xlsx,.xls,.csv,.json,.html"
          />
          <textarea
            ref={inputRef}
            className="chat-input"
            placeholder="Ask about documents, courses, SQL data..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={streaming}
          />
          {streaming ? (
            <button className="chat-stop-btn" onClick={handleStop}>
              <Square size={14} /> Stop
            </button>
          ) : (
            <button
              className="chat-send-btn"
              onClick={() => handleSend()}
              disabled={!input.trim()}
            >
              <Send size={16} />
            </button>
          )}
        </div>
        </div>
      </div>

      {/* Toast */}
      {toast && <div className="toast">{toast}</div>}

      <ApiKeyModal
        open={showKeyModal}
        onClose={() => setShowKeyModal(false)}
        onSaved={async () => {
          setShowKeyModal(false);
          try {
            const status = await getApiKeyStatus();
            setWebKeyStatus(status);
            setMode('web');
          } catch {}
        }}
      />

      <DirectoryManagerModal
        open={showDirModal}
        onClose={() => setShowDirModal(false)}
        onSaved={async () => {
          const updated = await getUserDirectories().catch(() => ({ directories: [] }));
          setUserDirs(updated.directories || []);
          if ((updated.directories || []).length > 0) {
            setMode('filesystem');
          }
        }}
      />

      <ExportModal
        open={exportModalOpen}
        onClose={() => setExportModalOpen(false)}
        markdownContent={exportContent}
      />
    </div>
  );
}
