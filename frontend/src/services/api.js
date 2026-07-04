const API_BASE = 'http://192.168.29.134:8000/api';

function getToken() {
  return localStorage.getItem('tcet_token');
}

function authHeaders() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request(endpoint, options = {}) {
  const { method = 'GET', body, headers = {} } = options;

  const config = {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
      ...headers,
    },
  };

  if (body) {
    config.body = JSON.stringify(body);
  }

  const res = await fetch(`${API_BASE}${endpoint}`, config);

  if (res.status === 401) {
    localStorage.removeItem('tcet_token');
    localStorage.removeItem('tcet_user');
    window.location.reload();
    throw new Error('Unauthorized');
  }

  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.detail || 'Request failed');
  }

  return data;
}

// ── Auth ────────────────────────────────────────────────────
export async function login(username, password) {
  return request('/auth/login', {
    method: 'POST',
    body: { username, password },
  });
}

export async function register(username, password, role = 'user') {
  return request('/auth/register', {
    method: 'POST',
    body: { username, password, role },
  });
}

// ── Health ──────────────────────────────────────────────────
export async function healthCheck() {
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) });
    return res.ok;
  } catch {
    return false;
  }
}

// ── Sessions ────────────────────────────────────────────────
export async function getSessions() {
  const data = await request('/sessions');
  return data.sessions || [];
}

export async function createSession(sessionName) {
  return request('/sessions', {
    method: 'POST',
    body: { session_name: sessionName || null },
  });
}

export async function deleteSession(sessionId) {
  return request(`/sessions/${sessionId}`, { method: 'DELETE' });
}

export async function getHistory(sessionId) {
  const data = await request(`/sessions/${sessionId}/history`);
  return data.messages || [];
}

// ── Chat (SSE Streaming) ────────────────────────────────────
export function chatStream(sessionId, message, attachedFiles = null, modes = null) {
  const controller = new AbortController();
  const body = { session_id: sessionId, message };
  if (attachedFiles && attachedFiles.length > 0) {
    body.attached_files = attachedFiles;
  }
  if (modes && modes.length > 0) {
    body.mode = modes.length === 1 ? modes[0] : modes;
  }

  const promise = fetch(`${API_BASE}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
    },
    body: JSON.stringify(body),
    signal: controller.signal,
  });

  return { promise, controller };
}

export async function* readSSEStream(response) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            yield data;
            if (data.done) return;
          } catch {
            // skip malformed JSON
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

// ── Documents (Admin) ───────────────────────────────────────
export async function getDocuments() {
  return request('/admin/documents');
}

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/admin/documents/upload`, {
    method: 'POST',
    headers: authHeaders(),
    body: formData,
  });

  return res.json();
}

export async function deleteDocument(docId) {
  return request(`/admin/documents/${docId}`, { method: 'DELETE' });
}

export async function clearAllDocuments() {
  return request('/admin/documents', { method: 'DELETE' });
}

// ── SQL (Admin) ─────────────────────────────────────────────
export async function sqlStatus() {
  return request('/admin/sql/status');
}

export async function sqlConnect(config) {
  return request('/admin/sql/connect', {
    method: 'POST',
    body: config,
  });
}

export async function sqlDisconnect() {
  return request('/admin/sql/disconnect', { method: 'POST' });
}

export async function sqlTables() {
  return request('/admin/sql/tables');
}

export async function sqlSchema(tableName) {
  return request(`/admin/sql/schema/${tableName}`);
}

export async function sqlQuery(query) {
  const res = await fetch(`${API_BASE}/admin/sql/query?query=${encodeURIComponent(query)}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
    },
  });
  return res.json();
}

// ── TCET Documents (Admin) ──────────────────────────────────
export async function getTcetDocs() {
  return request('/admin/tcet-docs');
}

export async function indexTcetDocs(fileNames) {
  return request('/admin/tcet-docs/index', {
    method: 'POST',
    body: { file_names: fileNames },
  });
}

// ── API Keys (Web Search) ────────────────────────────────────
export async function getApiKeyStatus() {
  return request('/auth/api-key');
}

export async function saveApiKey(apiKey) {
  return request('/auth/api-key', {
    method: 'POST',
    body: { api_key: apiKey, provider: 'tavily' },
  });
}

export async function deleteApiKey() {
  return request('/auth/api-key', { method: 'DELETE' });
}

// ── User Directories (Filesystem) ───────────────────────────
export async function getUserDirectories() {
  return request('/auth/directories');
}

export async function addUserDirectory(directoryPath) {
  return request('/auth/directories', {
    method: 'POST',
    body: { directory_path: directoryPath },
  });
}

export async function deleteUserDirectory(directoryPath) {
  return request('/auth/directories', {
    method: 'DELETE',
    body: { directory_path: directoryPath },
  });
}

// ── Document Generation ─────────────────────────────────────
export async function generateDocument({ markdown, html, format, template_id, metadata, filename, generator_version }) {
  return request('/document-gen/generate', {
    method: 'POST',
    body: {
      markdown: markdown || null,
      html: html || null,
      format: format || 'docx',
      template_id: template_id || 'default',
      metadata: metadata || {},
      filename: filename || null,
      generator_version: generator_version || 'v1',
    },
  });
}

export async function previewDocument({ markdown, html, format, template_id }) {
  return request('/document-gen/preview', {
    method: 'POST',
    body: {
      markdown: markdown || null,
      html: html || null,
      format: format || 'docx',
      template_id: template_id || 'default',
    },
  });
}

export async function getDocumentFormats() {
  return request('/document-gen/formats');
}

export async function getTemplates() {
  return request('/document-gen/templates');
}

export async function getTemplate(templateId) {
  return request(`/document-gen/templates/${templateId}`);
}
