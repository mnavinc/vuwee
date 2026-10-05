import { useState, useEffect, useCallback } from 'react';
import './index.css';
import { DEFAULT_CONFIG } from './config';
import CredentialsSection from './components/CredentialsSection';
import ConfigSection from './components/ConfigSection';
import ScriptSection from './components/ScriptSection';
import RunSection from './components/RunSection';

// ─── Toast system ────────────────────────────────────────────
function ToastContainer({ toasts }) {
  return (
    <div className="toast-container">
      {toasts.map(t => (
        <div key={t.id} className={`toast toast-${t.type}`}>
          <span>{t.type === 'success' ? '✅' : t.type === 'error' ? '❌' : 'ℹ️'}</span>
          <span>{t.message}</span>
        </div>
      ))}
    </div>
  );
}

// ─── Nav items ───────────────────────────────────────────────
const NAV = [
  { id: 'credentials', icon: '🔑', label: 'Credentials', group: 'Setup' },
  { id: 'config',      icon: '⚙️', label: 'Configuration', group: 'Pipeline' },
  { id: 'script',      icon: '📝', label: 'Script / Shots', group: 'Pipeline' },
  { id: 'run',         icon: '🚀', label: 'Run & Download', group: 'Pipeline' },
];

const STORAGE_KEY_CREDS  = 'vuwee_creds';
const STORAGE_KEY_CONFIG = 'vuwee_config';

export default function App() {
  const [section, setSection] = useState('credentials');
  const [toasts, setToasts] = useState([]);
  const [plan, setPlan]   = useState(null);

  // Credentials (username, kaggle key, etc.)
  const [creds, setCreds] = useState(() => {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY_CREDS) || '{}'); }
    catch { return {}; }
  });

  // All notebook config options
  const [config, setConfig] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY_CONFIG) || 'null');
      return saved ? { ...DEFAULT_CONFIG, ...saved } : DEFAULT_CONFIG;
    } catch { return DEFAULT_CONFIG; }
  });

  // Persist to localStorage
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY_CREDS, JSON.stringify(creds));
  }, [creds]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY_CONFIG, JSON.stringify(config));
  }, [config]);

  // Toast helper
  const toast = useCallback((message, type = 'info') => {
    const id = Date.now() + Math.random();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000);
  }, []);

  // Group nav items by group
  const groups = [...new Set(NAV.map(n => n.group))];

  return (
    <div className="app-layout">
      {/* ─── Sidebar ─── */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <a className="logo-mark" href="#">
            <div className="logo-icon">🎬</div>
            <div>
              <div className="logo-text">Vuwee-Gen</div>
              <div className="logo-sub">AI Video Pipeline</div>
            </div>
          </a>
        </div>

        <nav className="sidebar-nav">
          {groups.map(group => (
            <div key={group}>
              <div className="nav-section-label">{group}</div>
              {NAV.filter(n => n.group === group).map(item => (
                <button
                  key={item.id}
                  className={`nav-item ${section === item.id ? 'active' : ''}`}
                  onClick={() => setSection(item.id)}
                >
                  <span className="nav-icon">{item.icon}</span>
                  {item.label}
                  {item.id === 'script' && plan && (
                    <span className="nav-badge">{plan.shots?.length}</span>
                  )}
                </button>
              ))}
            </div>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="text-xs text-muted" style={{ marginBottom: 8, lineHeight: 1.6 }}>
            <strong style={{ color: 'var(--text-secondary)' }}>Kaggle GPU required</strong><br />
            Accelerator: GPU T4 x2<br />
            Internet: ON
          </div>
          <button
            className="btn btn-secondary btn-sm btn-full"
            onClick={() => {
              if (confirm('Reset all settings to defaults?')) {
                setConfig(DEFAULT_CONFIG);
                toast('Settings reset to defaults', 'info');
              }
            }}
          >
            ↺ Reset Defaults
          </button>
        </div>
      </aside>

      {/* ─── Main content ─── */}
      <main className="main-content">
        <div className={`page-section ${section === 'credentials' ? 'active' : ''}`}>
          <CredentialsSection creds={creds} onChange={setCreds} onToast={toast} />
        </div>

        <div className={`page-section ${section === 'config' ? 'active' : ''}`}>
          <ConfigSection config={config} onChange={setConfig} />
        </div>

        <div className={`page-section ${section === 'script' ? 'active' : ''}`}>
          <ScriptSection
            config={config}
            creds={creds}
            onToast={toast}
            onPlanChange={setPlan}
          />
        </div>

        <div className={`page-section ${section === 'run' ? 'active' : ''}`}>
          <RunSection
            config={config}
            creds={creds}
            plan={plan}
            onToast={toast}
          />
        </div>
      </main>

      <ToastContainer toasts={toasts} />
    </div>
  );
}
