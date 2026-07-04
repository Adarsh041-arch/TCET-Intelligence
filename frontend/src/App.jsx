import { useState, useEffect, useCallback } from 'react';
import { ChevronRight } from 'lucide-react';
import { AuthProvider, useAuth } from './context/AuthContext';
import LoginPage from './pages/LoginPage';
import Sidebar from './components/Sidebar';
import ChatPanel from './components/ChatPanel';
import UploadPage from './components/UploadPage';
import DocumentsPage from './components/DocumentsPage';
import DatabasePage from './components/DatabasePage';
import SQLConsolePage from './components/SQLConsolePage';
import TCETDocsPage from './components/TCETDocsPage';
import { getSessions, createSession, deleteSession } from './services/api';

function MainLayout() {
  const { isAdmin } = useAuth();
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [activePage, setActivePage] = useState('chat');
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    const saved = localStorage.getItem('sidebarOpen');
    return saved !== null ? saved === 'true' : true;
  });

  const handleToggleSidebar = () => {
    setSidebarOpen(prev => {
      const newVal = !prev;
      localStorage.setItem('sidebarOpen', newVal);
      return newVal;
    });
  };

  const loadSessions = useCallback(async () => {
    try {
      const list = await getSessions();
      setSessions(list);
    } catch {
      // silent
    }
  }, []);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  const handleNewChat = async () => {
    try {
      const data = await createSession();
      if (data.session_id) {
        setActiveSessionId(data.session_id);
        await loadSessions();
      }
    } catch {
      // silent
    }
  };

  const handleDeleteSession = async (sessionId) => {
    try {
      await deleteSession(sessionId);
      if (activeSessionId === sessionId) {
        setActiveSessionId(null);
      }
      await loadSessions();
    } catch {
      // silent
    }
  };

  const handleSelectSession = (sessionId) => {
    setActiveSessionId(sessionId);
    setActivePage('chat');
  };

  const renderPage = () => {
    switch (activePage) {
      case 'upload':
        return <UploadPage />;
      case 'documents':
        return <DocumentsPage />;
      case 'database':
        return <DatabasePage />;
      case 'sql':
        return <SQLConsolePage />;
      case 'tcet-docs':
        return <TCETDocsPage />;
      case 'chat':
      default:
        return (
          <ChatPanel
            sessionId={activeSessionId}
            onSessionUpdate={loadSessions}
          />
        );
    }
  };

  return (
    <div className="app-layout">
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        activePage={activePage}
        onNewChat={handleNewChat}
        onSelectSession={handleSelectSession}
        onDeleteSession={handleDeleteSession}
        onSelectPage={setActivePage}
        sidebarOpen={sidebarOpen}
        onToggleSidebar={handleToggleSidebar}
      />
      <main className={`main-content ${!sidebarOpen ? 'sidebar-collapsed' : ''}`}>
        {!sidebarOpen && (
          <button className="sidebar-toggle-btn open-sidebar-btn" onClick={() => setSidebarOpen(true)} title="Expand Sidebar">
            <ChevronRight size={18} />
          </button>
        )}
        {renderPage()}
      </main>
    </div>
  );
}

function AppContent() {
  const { user } = useAuth();

  if (!user) {
    return <LoginPage />;
  }

  return <MainLayout />;
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
