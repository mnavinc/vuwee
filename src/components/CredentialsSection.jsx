import { useState } from 'react';
import { api } from '../api';

export default function CredentialsSection({ creds, onChange, onToast }) {
  const [testing, setTesting] = useState(false);
  const [status, setStatus] = useState(null);

  async function testCreds() {
    if (!creds.username?.trim() || !creds.kaggleKey?.trim()) {
      const msg = 'Please enter both Kaggle username and API key first';
      setStatus({ ok: false, message: msg });
      onToast(msg, 'error');
      return;
    }
    setTesting(true);
    setStatus(null);
    try {
      const r = await api.testKaggle(creds.username.trim(), creds.kaggleKey.trim());
      setStatus({ ok: r.ok, message: r.message });
      onToast(r.message, r.ok ? 'success' : 'error');
    } catch (e) {
      setStatus({ ok: false, message: e.message });
      onToast(e.message, 'error');
    } finally {
      setTesting(false);
    }
  }

  return (
    <div>
      <div className="page-header">
        <h2>🔑 Credentials & Setup</h2>
        <p>Configure your Kaggle API access and API keys for LLM providers.</p>
      </div>

      <div className="card section-gap">
        <div className="card-header">
          <div className="card-icon violet">🐱</div>
          <div>
            <h3>Kaggle API Credentials</h3>
            <p className="text-sm text-secondary">Required to push & run notebooks on Kaggle</p>
          </div>
        </div>
        <div className="card-body">
          <div className="alert alert-info" style={{ marginBottom: 20 }}>
            <span>ℹ️</span>
            <span>Find your credentials at <strong>kaggle.com → Settings → API → Create New Token</strong>. 
            Keys are stored only in your browser (localStorage) and never sent anywhere except to Kaggle.</span>
          </div>
          <div className="form-grid">
            <div className="form-group">
              <label>Kaggle Username</label>
              <input
                type="text"
                placeholder="your_kaggle_username"
                value={creds.username}
                onChange={e => onChange({ ...creds, username: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label>Kaggle API Key</label>
              <input
                type="password"
                placeholder="••••••••••••••••••••••"
                value={creds.kaggleKey}
                onChange={e => onChange({ ...creds, kaggleKey: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label>Kernel Slug <span className="label-hint">(your notebook name on Kaggle)</span></label>
              <input
                type="text"
                placeholder="vuwee-gen-pipeline"
                value={creds.kernelSlug}
                onChange={e => onChange({ ...creds, kernelSlug: e.target.value.replace(/[^a-z0-9-]/gi, '-').toLowerCase() })}
              />
            </div>
            <div className="form-group">
              <label>Output Download Path <span className="label-hint">(local folder)</span></label>
              <input
                type="text"
                placeholder="C:\Users\you\Videos  (leave blank for default)"
                value={creds.downloadPath || ''}
                onChange={e => onChange({ ...creds, downloadPath: e.target.value })}
              />
            </div>
          </div>
          <div className="flex gap-3 mt-4">
            <button className="btn btn-primary" onClick={testCreds} disabled={testing}>
              {testing ? <><div className="spinner" /> Testing...</> : '⚡ Test Connection'}
            </button>
            {status && (
              <div className={`alert ${status.ok ? 'alert-success' : 'alert-error'}`} style={{ flex: 1 }}>
                <span>{status.ok ? '✓' : '✗'}</span>
                <span>{status.message}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="card section-gap">
        <div className="card-header">
          <div className="card-icon cyan">🤖</div>
          <div>
            <h3>LLM API Keys</h3>
            <p className="text-sm text-secondary">Used for local script generation and on Kaggle</p>
          </div>
        </div>
        <div className="card-body">
          <div className="form-grid">
            <div className="form-group">
              <label>OpenRouter API Key <span className="label-hint">openrouter.ai/keys</span></label>
              <input
                type="password"
                placeholder="sk-or-..."
                value={creds.openrouterKey || ''}
                onChange={e => onChange({ ...creds, openrouterKey: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label>Google Gemini API Key <span className="label-hint">aistudio.google.com</span></label>
              <input
                type="password"
                placeholder="AIza..."
                value={creds.geminiKey || ''}
                onChange={e => onChange({ ...creds, geminiKey: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label>Anthropic Claude API Key</label>
              <input
                type="password"
                placeholder="sk-ant-..."
                value={creds.anthropicKey || ''}
                onChange={e => onChange({ ...creds, anthropicKey: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label>Pixabay API Key <span className="label-hint">pixabay.com/api/docs</span></label>
              <input
                type="password"
                placeholder="Free key after sign-up"
                value={creds.pixabayKey || ''}
                onChange={e => onChange({ ...creds, pixabayKey: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label>Pexels API Key <span className="label-hint">pexels.com/api</span></label>
              <input
                type="password"
                placeholder="Your Pexels key"
                value={creds.pexelsKey || ''}
                onChange={e => onChange({ ...creds, pexelsKey: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label>ngrok Token <span className="label-hint">optional, for ComfyUI UI</span></label>
              <input
                type="password"
                placeholder="ngrok auth token"
                value={creds.ngrokToken || ''}
                onChange={e => onChange({ ...creds, ngrokToken: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label>HuggingFace Token <span className="label-hint">optional, faster downloads</span></label>
              <input
                type="password"
                placeholder="hf_..."
                value={creds.hfToken || ''}
                onChange={e => onChange({ ...creds, hfToken: e.target.value })}
              />
            </div>
          </div>
          <div className="alert alert-warn mt-4">
            <span>⚠️</span>
            <span>These keys must also be added as <strong>Kaggle Secrets</strong> in your notebook 
            (Add-ons → Secrets) for the notebook to use them during execution.</span>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <div className="card-icon emerald">📄</div>
          <div>
            <h3>Notebook Template</h3>
            <p className="text-sm text-secondary">Save your Kaggle notebook .py file as the template</p>
          </div>
        </div>
        <div className="card-body">
          <p className="text-secondary text-sm" style={{ marginBottom: 16 }}>
            Save the full notebook Python script as <code className="font-mono" style={{ background: 'rgba(99,102,241,0.15)', padding: '2px 6px', borderRadius: 4 }}>notebook_template.py</code> in the project root. 
            The app will inject your config into CELL 0 automatically when pushing to Kaggle.
          </p>
          <div className="flex gap-3">
            <label className="btn btn-secondary" style={{ cursor: 'pointer' }}>
              📂 Upload Template
              <input
                type="file"
                accept=".py,.ipynb,.txt"
                style={{ display: 'none' }}
                onChange={async e => {
                  const file = e.target.files[0];
                  if (!file) return;
                  const content = await file.text();
                  try {
                    await api.saveTemplate(content);
                    onToast('Template saved as notebook_template.py ✓', 'success');
                  } catch (err) {
                    onToast('Failed to save template: ' + err.message, 'error');
                  }
                }}
              />
            </label>
            <button className="btn btn-secondary" onClick={async () => {
              const r = await api.templateExists();
              onToast(r.exists ? '✓ notebook_template.py found' : '✗ Template not found — please upload it', r.exists ? 'success' : 'error');
            }}>
              🔍 Check Template
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
