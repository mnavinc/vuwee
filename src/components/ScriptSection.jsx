import { useState } from 'react';
import { api } from '../api';
import { CONTENT_TYPES } from '../config';

const VISUAL_COLORS = {
  wan: 'wan', stock: 'stock', kenburns: 'kenburns', card: 'card', screen: 'screen'
};

function ShotCard({ shot, index, onChange, onRemove }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="shot-card section-gap">
      <div className="shot-header">
        <div className="shot-index">#{index + 1}</div>
        <span className={`visual-tag visual-${shot.visual}`}>{shot.visual}</span>
        <div style={{ flex: 1, overflow: 'hidden' }}>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {shot.narration || <em style={{ color: 'var(--text-muted)' }}>No narration</em>}
          </div>
        </div>
        <button className="btn btn-sm btn-secondary" onClick={() => setExpanded(!expanded)} style={{ flexShrink: 0 }}>
          {expanded ? '▲ Less' : '▼ Edit'}
        </button>
        <button className="btn btn-sm btn-danger" onClick={onRemove} style={{ flexShrink: 0 }}>✕</button>
      </div>

      {expanded && (
        <div className="form-grid" style={{ marginTop: 12 }}>
          <div className="form-group span-2">
            <label>Narration</label>
            <textarea value={shot.narration} onChange={e => onChange({ ...shot, narration: e.target.value })} style={{ minHeight: 60 }} />
          </div>
          <div className="form-group">
            <label>Visual Type</label>
            <select value={shot.visual} onChange={e => onChange({ ...shot, visual: e.target.value })}>
              {['wan', 'stock', 'kenburns', 'card', 'screen'].map(v => <option key={v} value={v}>{v}</option>)}
            </select>
          </div>
          {shot.visual === 'wan' && (
            <div className="form-group">
              <label>wan_prompt</label>
              <input type="text" value={shot.wan_prompt || ''} onChange={e => onChange({ ...shot, wan_prompt: e.target.value })} />
            </div>
          )}
          {(shot.visual === 'stock' || shot.visual === 'kenburns') && (
            <div className="form-group">
              <label>stock_query</label>
              <input type="text" value={shot.stock_query || ''} onChange={e => onChange({ ...shot, stock_query: e.target.value })} />
            </div>
          )}
          {shot.visual === 'kenburns' && (
            <div className="form-group span-2">
              <label>image_prompt</label>
              <input type="text" value={shot.image_prompt || ''} onChange={e => onChange({ ...shot, image_prompt: e.target.value })} />
            </div>
          )}
          {shot.visual === 'card' && (
            <div className="form-group">
              <label>on_screen_text</label>
              <input type="text" value={shot.on_screen_text || ''} onChange={e => onChange({ ...shot, on_screen_text: e.target.value })} />
            </div>
          )}
          {shot.visual === 'screen' && (
            <div className="form-group">
              <label>URL</label>
              <input type="url" value={shot.url || ''} onChange={e => onChange({ ...shot, url: e.target.value })} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ScriptSection({ config, creds, onToast, onPlanChange }) {
  const [generating, setGenerating] = useState(false);
  const [planState, setPlanState] = useState(null);
  const [rawScript, setRawScript] = useState('');
  const [tab, setTab] = useState('shots'); // shots | raw | json

  const plan = planState;
  function setPlan(p) { setPlanState(p); if (onPlanChange) onPlanChange(p); }

  async function generateScript() {
    const provider = config.LLM_PROVIDER;
    let apiKey = '';
    if (provider === 'openrouter') apiKey = creds.openrouterKey;
    else if (provider === 'gemini') apiKey = creds.geminiKey;
    else if (provider === 'claude') apiKey = creds.anthropicKey;

    if (!apiKey && provider !== 'ollama') {
      onToast(`No API key for ${provider}. Set it in Credentials.`, 'error');
      return;
    }

    setGenerating(true);
    const n_shots = Math.max(4, Math.round(config.TARGET_SECONDS / 5.0));
    const words_per_shot = Math.round(5 * 2.6);
    const contentGuide = CONTENT_TYPES.find(ct => ct.value === config.CONTENT_TYPE)?.desc || '';

    const system = `You are a YouTube producer. Write a narration script and visual plan as a JSON object.
Return ONLY valid JSON with this shape:
{"title": str, "description": str, "tags": [str], "visual_anchor": str, "shots": [{"narration": str, "visual": "wan"|"stock"|"kenburns"|"card"|"screen", "wan_prompt": str, "stock_query": str, "stock_queries": [str], "specific": bool, "image_prompt": str, "on_screen_text": str, "url": str}]}

Rules:
- Exactly about ${n_shots} shots; each narration about ${words_per_shot} words, in language "${config.LANGUAGE}".
- Content type: ${config.CONTENT_TYPE}. ${contentGuide}
- Use ONLY facts from the provided source. Do not invent statistics or specs.
- "wan" = AI clip: at most ${config.MAX_WAN_SHOTS || 6} shots. wan_prompt = vivid English sentence, motion, lighting. No real people, logos.
- "stock" = stock footage for generic real-world scenes. Give stock_queries: 3 English queries, specific to generic.
- "kenburns" = still image with zoom. Give image_prompt (vivid, no real people/logos).
- "card" = text card; on_screen_text = short title/stat (max 10 words).
- "screen" = screen recording; only if URL in source.
- First shot: strong hook. Last shot: takeaway or CTA.`;

    const user = `Source (${config.INPUT_TYPE}):\n\n${config.INPUT}\n\nTarget length: ${config.TARGET_SECONDS} seconds.`;

    try {
      const r = await api.generateScript(provider, apiKey, config.OPENROUTER_MODEL, user, system);
      if (!r.ok) throw new Error(r.message);
      setRawScript(r.script);
      // Parse JSON
      const jsonMatch = r.script.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        const parsed = JSON.parse(jsonMatch[0]);
        setPlan(parsed);
        setTab('shots');
        onToast(`Script generated: "${parsed.title}" (${parsed.shots?.length} shots)`, 'success');
      } else {
        setTab('raw');
        onToast('Script generated (could not auto-parse shots — check Raw tab)', 'info');
      }
    } catch (e) {
      onToast('Script generation failed: ' + e.message, 'error');
    } finally {
      setGenerating(false);
    }
  }

  function updateShot(i, updated) {
    const shots = [...(plan.shots || [])];
    shots[i] = updated;
    setPlan({ ...plan, shots });
  }

  function removeShot(i) {
    const shots = [...(plan.shots || [])];
    shots.splice(i, 1);
    setPlan({ ...plan, shots });
  }

  function addShot() {
    const shots = [...(plan?.shots || [])];
    shots.push({ narration: '', visual: 'card', on_screen_text: '', wan_prompt: '', stock_query: '', image_prompt: '', url: '' });
    setPlan({ ...(plan || { title: '', description: '', tags: [] }), shots });
  }

  function tryParseRaw() {
    try {
      const jsonMatch = rawScript.match(/\{[\s\S]*\}/);
      if (!jsonMatch) throw new Error('No JSON found');
      const parsed = JSON.parse(jsonMatch[0]);
      setPlan(parsed);
      setTab('shots');
      onToast('Parsed successfully', 'success');
    } catch (e) {
      onToast('Parse failed: ' + e.message, 'error');
    }
  }

  const shotCounts = plan?.shots?.reduce((acc, s) => {
    acc[s.visual] = (acc[s.visual] || 0) + 1;
    return acc;
  }, {}) || {};

  return (
    <div>
      <div className="page-header">
        <h2>📝 Script & Shot List</h2>
        <p>Generate your video script with an LLM, then review and edit individual shots.</p>
      </div>

      <div className="card section-gap">
        <div className="card-header">
          <div className="card-icon cyan">✨</div>
          <div style={{ flex: 1 }}>
            <h3>Generate Script</h3>
            <p className="text-sm text-secondary">Uses the LLM provider set in your config</p>
          </div>
          <span className="badge badge-idle">{config.LLM_PROVIDER}</span>
        </div>
        <div className="card-body">
          <div className="alert alert-info" style={{ marginBottom: 20 }}>
            <span>ℹ️</span>
            <span>Script generation runs <strong>locally</strong> via your API key, not on Kaggle. 
            The generated plan is automatically embedded into the notebook when you start the run.</span>
          </div>
          <div className="flex gap-3 items-center">
            <button
              className="btn btn-gradient"
              onClick={generateScript}
              disabled={generating}
            >
              {generating ? <><div className="spinner" /> Generating...</> : '🪄 Generate Script with LLM'}
            </button>
            {plan && (
              <span className="badge badge-complete">
                ✓ {plan.shots?.length} shots ready
              </span>
            )}
          </div>
        </div>
      </div>

      {plan && (
        <div className="card section-gap">
          <div className="card-header">
            <div className="card-icon emerald">🎬</div>
            <div style={{ flex: 1 }}>
              <h3>{plan.title || 'Untitled'}</h3>
              <p className="text-sm text-secondary">{plan.description?.slice(0, 120)}</p>
            </div>
            <div className="flex gap-2">
              {Object.entries(shotCounts).map(([v, n]) => (
                <span key={v} className={`visual-tag visual-${v}`}>{n} {v}</span>
              ))}
            </div>
          </div>
          <div className="card-body">
            {plan.tags?.length > 0 && (
              <div className="flex gap-2 mb-4" style={{ flexWrap: 'wrap' }}>
                {plan.tags.map(t => (
                  <span key={t} style={{ background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.2)', borderRadius: 4, padding: '2px 8px', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>#{t}</span>
                ))}
              </div>
            )}

            <div className="tab-list">
              <button className={`tab-btn ${tab === 'shots' ? 'active' : ''}`} onClick={() => setTab('shots')}>🎞️ Shots ({plan.shots?.length})</button>
              <button className={`tab-btn ${tab === 'raw' ? 'active' : ''}`} onClick={() => setTab('raw')}>📄 Raw</button>
              <button className={`tab-btn ${tab === 'json' ? 'active' : ''}`} onClick={() => setTab('json')}>{ } JSON</button>
            </div>

            {tab === 'shots' && (
              <div>
                {plan.shots?.map((shot, i) => (
                  <ShotCard
                    key={i}
                    shot={shot}
                    index={i}
                    onChange={s => updateShot(i, s)}
                    onRemove={() => removeShot(i)}
                  />
                ))}
                <button className="btn btn-secondary btn-full mt-4" onClick={addShot}>+ Add Shot</button>
              </div>
            )}

            {tab === 'raw' && (
              <div>
                <textarea
                  className="script-editor"
                  value={rawScript}
                  onChange={e => setRawScript(e.target.value)}
                  style={{ minHeight: 500 }}
                />
                <div className="flex gap-3 mt-4">
                  <button className="btn btn-primary" onClick={tryParseRaw}>🔄 Parse to Shots</button>
                </div>
              </div>
            )}

            {tab === 'json' && (
              <div>
                <textarea
                  className="script-editor"
                  value={JSON.stringify(plan, null, 2)}
                  onChange={e => {
                    try { setPlan(JSON.parse(e.target.value)); } catch (_) {}
                  }}
                  style={{ minHeight: 500 }}
                />
              </div>
            )}
          </div>
        </div>
      )}

      {/* Manual plan editor */}
      {!plan && (
        <div className="card">
          <div className="card-header">
            <div className="card-icon amber">✏️</div>
            <h3>Manual Plan (Skip LLM)</h3>
          </div>
          <div className="card-body">
            <p className="text-secondary text-sm" style={{ marginBottom: 12 }}>
              Paste a JSON plan directly to skip LLM generation. See the notebook's MANUAL_PLAN example for the format.
            </p>
            <textarea
              className="script-editor"
              placeholder={'{\n  "title": "My Video",\n  "shots": [\n    {"narration": "...", "visual": "wan", "wan_prompt": "..."}\n  ]\n}'}
              style={{ minHeight: 200 }}
              onChange={e => {
                try { setPlan(JSON.parse(e.target.value)); setTab('shots'); } catch (_) {}
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
