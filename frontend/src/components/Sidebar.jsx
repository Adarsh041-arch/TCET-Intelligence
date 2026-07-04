import { useAuth } from '../context/AuthContext';
import {
  MessageSquare, Plus, Upload, BookOpen, Database, Terminal, LogOut, Zap, ChevronLeft, FileText,
} from 'lucide-react';

const ADMIN_PAGES = [
  { key: 'chat', label: 'Chat Interface', icon: MessageSquare },
  { key: 'upload', label: 'Index Documents', icon: Upload },
  { key: 'documents', label: 'Knowledge Base', icon: BookOpen },
  { key: 'tcet-docs', label: 'TCET Docs', icon: FileText },
  { key: 'database', label: 'Database Hub', icon: Database },
  { key: 'sql', label: 'SQL Console', icon: Terminal },
];

export default function Sidebar({
  sessions,
  activeSessionId,
  activePage,
  onNewChat,
  onSelectSession,
  onSelectPage,
  sidebarOpen,
  onToggleSidebar,
}) {
  const { user, logout, isAdmin } = useAuth();

  return (
    <aside className={`sidebar ${!sidebarOpen ? 'collapsed' : ''}`}>
      <div className="sidebar-inner">
        {/* Brand */}
        <div className="sidebar-header">
          <div className="sidebar-header-left">
            <div className="sidebar-brand">
              <Zap size={20} color="#8fbc8f" />
              <h2>TCET Portal</h2>
            </div>
            <span className="role-badge">{user?.role} Console</span>
          </div>
          <button
            className="sidebar-toggle-btn close-btn"
            onClick={onToggleSidebar}
            title="Collapse Sidebar"
          >
            <ChevronLeft size={16} />
          </button>
        </div>

      {/* New Chat */}
      <div className="sidebar-actions">
        <button className="btn btn-primary btn-block" onClick={onNewChat}>
          <Plus size={16} /> New Chat
        </button>
      </div>

      {/* Sessions */}
      <div className="sidebar-sessions">
        <div className="sidebar-section-title">Conversations</div>
        {sessions.length > 0 ? (
          sessions.map((s) => {
            const name = s.session_name || 'Untitled Session';
            const truncated = name.length > 26 ? name.slice(0, 26) + '…' : name;
            const isActive = s.session_id === activeSessionId;
            return (
              <div
                key={s.session_id}
                className={`session-item ${isActive ? 'active' : ''}`}
                onClick={() => onSelectSession(s.session_id)}
                title={name}
              >
                <MessageSquare size={14} />
                <span>{truncated}</span>
              </div>
            );
          })
        ) : (
          <div style={{ padding: '10px 6px', color: 'var(--text-tertiary)', fontSize: '0.82rem' }}>
            No conversations yet.
          </div>
        )}
      </div>

      {/* Admin Nav */}
      {isAdmin && (
        <div className="sidebar-nav">
          <div className="sidebar-section-title">Administration</div>
          {ADMIN_PAGES.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              className={`nav-item ${activePage === key ? 'active' : ''}`}
              onClick={() => onSelectPage(key)}
            >
              <Icon size={15} />
              <span>{label}</span>
            </button>
          ))}
        </div>
      )}

      {/* Footer */}
      <div className="sidebar-footer">
        <div className="sidebar-footer-user">
          <span className="sidebar-footer-name">{user?.username}</span>
          <span className="sidebar-footer-role">Scope: {user?.role}</span>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={logout} title="Logout">
          <LogOut size={16} />
        </button>
      </div>
      </div>
    </aside>
  );
}
