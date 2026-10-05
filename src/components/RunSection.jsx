import { useState, useEffect, useRef } from 'react';
import { api } from '../api';

const STATUS_MAP = {
  'complete':  { label: 'Complete',  cls: 'badge-complete', icon: '✅' },
  'running':   { label: 'Running',   cls: 'badge-running',  icon: '⚡' },
  'queued':    { label: 'Queued',    cls: 'badge-queued',   icon: '⏳' },
  'error':     { label: 'Error',     cls: 'badge-error',    icon: '❌' },
  'cancelRequested': { label: 'Cancelling', cls: 'badge-queued', icon: '🛑' },
};

function StatusBadge({ status }) {
  const s = STATUS_MAP[status] || { label: status || 'Idle', cls: 'badge-idle', icon: '💤' };
  return (
    <span className={`badge ${s.cls} ${status === 'running' ? 'pulse' : ''}`}>
      {s.icon} {s.label}
    </span>
  );
}

export default function RunSection({ config, creds, plan, onToast }) {
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState(null);   // Kaggle kernel status string
  const [kernelData, setKernelData] = useState(null);
  const [outputFiles, setOutputFiles] = useState([]);
  const [downloading, setDownloading] = useState(false);
  const [downloadedPath, setDownloadedPath] = useState('');
  const [pollInterval, setPollInterval] = useState(null);
  const [elapsedMs, setElapsedMs] = useState(0);
  const startRef = useRef(null);
  const timerRef = useRef(null);

  useEffect(() => () => {
    if (pollInterval) clearInterval(pollInterval);
    if (timerRef.current) clearInterval(timerRef.current);
  }, []);

  function startElapsedTimer() {
    startRef.current = Date.now();
    timerRef.current = setInterval(() => {
      setElapsedMs(Date.now() - startRef.current);
    }, 1000);
  }

  function stopElapsedTimer() {
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
  }

  function fmtElapsed(ms) {
    const s = Math.floor(ms / 1000);
    const m = Math.floor(s / 60);
    const h = Math.floor(m / 60);
    if (h > 0) return `${h}h ${m % 60}m ${s % 60}s`;
    if (m > 0) return `${m}m ${s % 60}s`;
    return `${s}s`;
  }

  async function pollStatus() {
    if (!creds.username || !creds.kaggleKey || !creds.kernelSlug) return;
    try {
      const r = await api.getStatus(creds.username, creds.kaggleKey, creds.kernelSlug);
      if (r.ok) {
        const st = r.data?.currentRunningVersion?.status || r.data?.lastRunningVersion?.status;
        setStatus(st);
        setKernelData(r.data);
        if (st === 'complete' || st === 'error') {
          setRunning(false);
          stopElapsedTimer();
          if (pollInterval) { clearInterval(pollInterval); setPollInterval(null); }
          if (st === 'complete') {
            onToast('🎉 Notebook run complete!', 'success');
            fetchOutput();
          } else {
            onToast('Notebook run encountered an error.', 'error');
          }
        }
      }
    } catch (e) {
      console.warn('poll error:', e);
    }
  }

  async function fetchOutput() {
    try {
      const r = await api.getOutput(creds.username, creds.kaggleKey, creds.kernelSlug);
      if (r.ok) setOutputFiles(r.data?.files || []);
    } catch (_) {}
  }

  async function startRun() {
    if (!creds.username || !creds.kaggleKey || !creds.kernelSlug) {
      onToast('Set Kaggle credentials and kernel slug in Credentials tab first', 'error');
      return;
    }
    setRunning(true);
    setStatus('queued');
    setElapsedMs(0);
    setDownloadedPath('');
    startElapsedTimer();
    try {
      const runConfig = plan
        ? { ...config, MANUAL_PLAN: plan }
        : config;
      const r = await api.runKernel(creds.username, creds.kaggleKey, creds.kernelSlug, runConfig);
      if (!r.ok) throw new Error(r.message);
      onToast('Notebook pushed to Kaggle and queued ✓', 'success');
      // Start polling every 30s
      const interval = setInterval(pollStatus, 30000);
      setPollInterval(interval);
      // First poll after 15s
      setTimeout(pollStatus, 15000);
    } catch (e) {
      setRunning(false);
      setStatus('error');
      stopElapsedTimer();
      onToast('Failed to start run: ' + e.message, 'error');
    }
  }

  async function downloadVideo(file) {
    setDownloading(true);
    try {
      const r = await api.downloadOutput(
        creds.username, creds.kaggleKey, creds.kernelSlug,
        file?.fileName || 'final.mp4',
        creds.downloadPath || ''
      );
      if (!r.ok) throw new Error(r.message);
      setDownloadedPath(r.savedPath);
      onToast(`Downloaded to: ${r.savedPath}`, 'success');
    } catch (e) {
      onToast('Download failed: ' + e.message, 'error');
    } finally {
      setDownloading(false);
    }
  }

  const videoFile = outputFiles.find(f => f.fileName?.endsWith('.mp4'));
  const metadataFile = outputFiles.find(f => f.fileName?.includes('metadata'));

  const estimatedMinutes = (() => {
    const n_wan = config.MAX_WAN_SHOTS || 6;
    const est_per_clip = { wan21: 270, ltxv: 150, wan22: 600, cogvideox_2b: 420, animatediff_sd15: 60, animatediff_sdxl: 240 }[config.VIDEO_MODEL] || 270;
    return Math.round((n_wan * est_per_clip / 60) + 15);
  })();

  return (
    <div>
      <div className="page-header">
        <h2>🚀 Run on Kaggle</h2>
        <p>Push your configured notebook to Kaggle and monitor the run in real-time.</p>
      </div>

      {/* Summary hero */}
      <div className="run-hero">
        <h2>Ready to Generate</h2>
        <p>{config.INPUT?.slice(0, 80)}{config.INPUT?.length > 80 ? '...' : ''}</p>
        <div className="flex gap-3 mt-4" style={{ flexWrap: 'wrap' }}>
          <span style={{ background: 'rgba(255,255,255,0.2)', borderRadius: 6, padding: '4px 12px', fontSize: '0.8rem', color: 'white' }}>
            🎬 {config.VIDEO_MODEL}
          </span>
          <span style={{ background: 'rgba(255,255,255,0.2)', borderRadius: 6, padding: '4px 12px', fontSize: '0.8rem', color: 'white' }}>
            ⏱️ ~{config.TARGET_SECONDS}s video
          </span>
          <span style={{ background: 'rgba(255,255,255,0.2)', borderRadius: 6, padding: '4px 12px', fontSize: '0.8rem', color: 'white' }}>
            🧠 {config.LLM_PROVIDER}
          </span>
          <span style={{ background: 'rgba(255,255,255,0.2)', borderRadius: 6, padding: '4px 12px', fontSize: '0.8rem', color: 'white' }}>
            📐 {config.ORIENTATION}
          </span>
          {plan && <span style={{ background: 'rgba(255,255,255,0.2)', borderRadius: 6, padding: '4px 12px', fontSize: '0.8rem', color: 'white' }}>✓ Script ready ({plan.shots?.length} shots)</span>}
        </div>
      </div>

      {/* Stats */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{config.TARGET_SECONDS}s</div>
          <div className="stat-label">Target Length</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">~{estimatedMinutes}m</div>
          <div className="stat-label">Est. Run Time</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{config.MAX_WAN_SHOTS || 'auto'}</div>
          <div className="stat-label">AI Clips</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{running || status ? fmtElapsed(elapsedMs) : '—'}</div>
          <div className="stat-label">Elapsed</div>
        </div>
      </div>

      {/* Control */}
      <div className="card section-gap">
        <div className="card-header">
          <div className="card-icon rose">▶️</div>
          <div style={{ flex: 1 }}>
            <h3>Kaggle Run</h3>
            <p className="text-sm text-secondary">kernel: <span className="font-mono" style={{ color: 'var(--accent-primary)' }}>{creds.username}/{creds.kernelSlug || 'not-set'}</span></p>
          </div>
          <StatusBadge status={status || 'idle'} />
        </div>
        <div className="card-body">
          <div className="alert alert-warn" style={{ marginBottom: 20 }}>
            <span>⚠️</span>
            <span>Make sure your Kaggle notebook has <strong>Accelerator = GPU T4 x2</strong> and <strong>Internet = ON</strong>. 
            The kernel will run as a batch commit (no interactive idle stop). Status is polled every 30 seconds.</span>
          </div>

          <div className="flex gap-3 items-center" style={{ flexWrap: 'wrap' }}>
            <button
              className="btn btn-gradient btn-lg"
              onClick={startRun}
              disabled={running}
            >
              {running ? <><div className="spinner" /> Running on Kaggle...</> : '🚀 Start Kaggle Run'}
            </button>
            <button
              className="btn btn-secondary"
              onClick={pollStatus}
              disabled={!creds.username}
            >
              🔄 Check Status
            </button>
            <button
              className="btn btn-secondary"
              onClick={fetchOutput}
              disabled={!creds.username}
            >
              📂 Check Output
            </button>
          </div>

          {running && (
            <div style={{ marginTop: 20 }}>
              <div className="flex justify-between text-sm mb-4" style={{ color: 'var(--text-secondary)' }}>
                <span>Elapsed: <strong>{fmtElapsed(elapsedMs)}</strong></span>
                <span>Polling every 30s</span>
              </div>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${Math.min(95, (elapsedMs / (estimatedMinutes * 60000)) * 100).toFixed(1)}%` }} />
              </div>
            </div>
          )}

          {kernelData && (
            <div className="mt-4 text-sm" style={{ color: 'var(--text-secondary)' }}>
              <div className="flex gap-4" style={{ flexWrap: 'wrap' }}>
                {kernelData.currentRunningVersion?.executionDuration && (
                  <span>⏱ Duration: <strong>{Math.round(kernelData.currentRunningVersion.executionDuration / 60)}m</strong></span>
                )}
                {kernelData.currentRunningVersion?.totalVotes !== undefined && (
                  <span>Version: <strong>{kernelData.currentRunningVersion?.runningVersion}</strong></span>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Output files */}
      {outputFiles.length > 0 && (
        <div className="card section-gap">
          <div className="card-header">
            <div className="card-icon emerald">📦</div>
            <h3>Output Files</h3>
          </div>
          <div className="card-body">
            {outputFiles.map((file, i) => (
              <div key={i} className="flex items-center gap-3 section-gap" style={{ padding: '12px 16px', background: 'rgba(0,0,0,0.2)', borderRadius: 8, border: '1px solid var(--border)' }}>
                <span style={{ fontSize: '1.5rem' }}>{file.fileName?.endsWith('.mp4') ? '🎬' : file.fileName?.endsWith('.json') ? '📋' : '📄'}</span>
                <div style={{ flex: 1 }}>
                  <div className="font-bold" style={{ fontSize: '0.9rem' }}>{file.fileName}</div>
                  <div className="text-xs text-muted">{file.totalBytes ? `${(file.totalBytes / 1024 / 1024).toFixed(1)} MB` : 'size unknown'}</div>
                </div>
                {file.fileName?.endsWith('.mp4') && (
                  <button
                    className="btn btn-primary"
                    onClick={() => downloadVideo(file)}
                    disabled={downloading}
                  >
                    {downloading ? <><div className="spinner" /> Downloading...</> : '⬇️ Download'}
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Downloaded */}
      {downloadedPath && (
        <div className="card">
          <div className="card-header">
            <div className="card-icon emerald">🎉</div>
            <h3>Video Downloaded!</h3>
          </div>
          <div className="card-body">
            <div className="alert alert-success">
              <span>✅</span>
              <div>
                <div style={{ marginBottom: 6 }}>Saved to:</div>
                <code className="font-mono" style={{ fontSize: '0.85rem', background: 'rgba(16,185,129,0.1)', padding: '4px 8px', borderRadius: 4 }}>
                  {downloadedPath}
                </code>
              </div>
            </div>
            <div className="flex gap-3 mt-4">
              <button className="btn btn-secondary" onClick={() => api.openDownloads()}>
                📂 Open Downloads Folder
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Kaggle link */}
      {creds.username && creds.kernelSlug && (
        <div className="alert alert-info mt-6">
          <span>🔗</span>
          <span>
            View on Kaggle:{' '}
            <a href={`https://www.kaggle.com/code/${creds.username}/${creds.kernelSlug}`} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent-cyan)', textDecoration: 'underline' }}>
              kaggle.com/code/{creds.username}/{creds.kernelSlug}
            </a>
          </span>
        </div>
      )}
    </div>
  );
}
