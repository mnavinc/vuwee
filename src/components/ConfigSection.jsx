import { CONTENT_TYPES, VIDEO_MODELS, LLM_PROVIDERS, TTS_ENGINES, EDGE_VOICES, STOCK_PROVIDERS } from '../config';

function Field({ label, hint, children, span2 }) {
  return (
    <div className={`form-group${span2 ? ' span-2' : ''}`}>
      <label>{label}{hint && <span className="label-hint">{hint}</span>}</label>
      {children}
    </div>
  );
}

function Toggle({ id, label, hint, checked, onChange }) {
  return (
    <div className="toggle-row" onClick={() => onChange(!checked)}>
      <input type="checkbox" id={id} checked={checked} onChange={e => onChange(e.target.checked)} onClick={e => e.stopPropagation()} />
      <label htmlFor={id} onClick={e => e.preventDefault()}>{label}</label>
      {hint && <span className="toggle-hint">{hint}</span>}
    </div>
  );
}

export default function ConfigSection({ config, onChange }) {
  const set = (key, val) => onChange({ ...config, [key]: val });

  return (
    <div>
      <div className="page-header">
        <h2>⚙️ Pipeline Configuration</h2>
        <p>Set all parameters for the script-to-video pipeline. These map directly to CELL 0 of the notebook.</p>
      </div>

      {/* ─── Core ─── */}
      <div className="card section-gap">
        <div className="card-header">
          <div className="card-icon violet">🎯</div>
          <h3>Input & Content</h3>
        </div>
        <div className="card-body">
          <div className="form-grid">
            <Field label="INPUT" hint="topic, URL, or paste your text" span2>
              <textarea
                value={config.INPUT}
                onChange={e => set('INPUT', e.target.value)}
                placeholder="Your topic, article URL, PDF URL, or full text..."
                style={{ minHeight: 80 }}
              />
            </Field>
            <Field label="INPUT_TYPE">
              <select value={config.INPUT_TYPE} onChange={e => set('INPUT_TYPE', e.target.value)}>
                <option value="topic">topic</option>
                <option value="url">url</option>
                <option value="pdf_url">pdf_url</option>
                <option value="text">text</option>
              </select>
            </Field>
            <Field label="CONTENT_TYPE">
              <select value={config.CONTENT_TYPE} onChange={e => set('CONTENT_TYPE', e.target.value)}>
                {CONTENT_TYPES.map(ct => (
                  <option key={ct.value} value={ct.value}>{ct.label} — {ct.desc}</option>
                ))}
              </select>
            </Field>
            <Field label="ORIENTATION">
              <select value={config.ORIENTATION} onChange={e => set('ORIENTATION', e.target.value)}>
                <option value="landscape">landscape (16:9 — YouTube)</option>
                <option value="portrait">portrait (9:16 — Shorts)</option>
              </select>
            </Field>
            <Field label="TARGET_SECONDS" hint="approx. video length">
              <input type="number" value={config.TARGET_SECONDS} min={10} max={600} onChange={e => set('TARGET_SECONDS', +e.target.value)} />
            </Field>
            <Field label="LANGUAGE" hint="BCP-47 code, e.g. en, hi, fr">
              <input type="text" value={config.LANGUAGE} onChange={e => set('LANGUAGE', e.target.value)} />
            </Field>
          </div>
        </div>
      </div>

      {/* ─── Video Model ─── */}
      <div className="card section-gap">
        <div className="card-header">
          <div className="card-icon rose">🎬</div>
          <h3>AI Video Model</h3>
        </div>
        <div className="card-body">
          <div className="form-grid">
            <Field label="VIDEO_MODEL" span2>
              <select value={config.VIDEO_MODEL} onChange={e => set('VIDEO_MODEL', e.target.value)}>
                {VIDEO_MODELS.map(m => (
                  <option key={m.value} value={m.value}>{m.label} — {m.desc}</option>
                ))}
              </select>
            </Field>
            <Field label="MAX_WAN_SHOTS" hint="blank = auto per model">
              <input
                type="number"
                value={config.MAX_WAN_SHOTS}
                placeholder="auto"
                min={0}
                max={20}
                onChange={e => set('MAX_WAN_SHOTS', e.target.value === '' ? '' : +e.target.value)}
              />
            </Field>
            <Field label="WAN_FRAMES" hint="81=5s @16fps">
              <input type="number" value={config.WAN_FRAMES} min={16} max={200} onChange={e => set('WAN_FRAMES', +e.target.value)} />
            </Field>
            <Field label="WAN_FPS">
              <input type="number" value={config.WAN_FPS} min={8} max={30} onChange={e => set('WAN_FPS', +e.target.value)} />
            </Field>
            <Field label="LTX_FRAMES" hint="97=4s @24fps">
              <input type="number" value={config.LTX_FRAMES} min={16} max={300} onChange={e => set('LTX_FRAMES', +e.target.value)} />
            </Field>
            <Field label="LTX_STEPS" hint="8 = distilled fast">
              <input type="number" value={config.LTX_STEPS} min={1} max={50} onChange={e => set('LTX_STEPS', +e.target.value)} />
            </Field>
            <Field label="COGX_FRAMES">
              <input type="number" value={config.COGX_FRAMES} min={16} max={100} onChange={e => set('COGX_FRAMES', +e.target.value)} />
            </Field>
            <Field label="COGX_STEPS">
              <input type="number" value={config.COGX_STEPS} min={10} max={100} onChange={e => set('COGX_STEPS', +e.target.value)} />
            </Field>
            <Field label="ANIM_FRAMES">
              <input type="number" value={config.ANIM_FRAMES} min={8} max={32} onChange={e => set('ANIM_FRAMES', +e.target.value)} />
            </Field>
            <Field label="ANIM_STEPS">
              <input type="number" value={config.ANIM_STEPS} min={10} max={50} onChange={e => set('ANIM_STEPS', +e.target.value)} />
            </Field>
            <Field label="WAN_STYLE_SUFFIX" span2>
              <input type="text" value={config.WAN_STYLE_SUFFIX} onChange={e => set('WAN_STYLE_SUFFIX', e.target.value)} />
            </Field>
            <Field label="WAN_NEGATIVE" span2>
              <input type="text" value={config.WAN_NEGATIVE} onChange={e => set('WAN_NEGATIVE', e.target.value)} />
            </Field>
            <Field label="WAN22_FRAMES">
              <input type="number" value={config.WAN22_FRAMES} min={16} max={200} onChange={e => set('WAN22_FRAMES', +e.target.value)} />
            </Field>
            <Field label="WAN22_STEPS">
              <input type="number" value={config.WAN22_STEPS} min={5} max={50} onChange={e => set('WAN22_STEPS', +e.target.value)} />
            </Field>
          </div>
          <div className="form-grid mt-4" style={{ gridTemplateColumns: '1fr 1fr 1fr' }}>
            <Toggle id="USE_FAST_LORA" label="USE_FAST_LORA" hint="~6 steps instead of 25" checked={config.USE_FAST_LORA} onChange={v => set('USE_FAST_LORA', v)} />
            <Toggle id="INTERPOLATE_LOW_FPS" label="INTERPOLATE_LOW_FPS" hint="Motion-interpolate 8fps clips" checked={config.INTERPOLATE_LOW_FPS} onChange={v => set('INTERPOLATE_LOW_FPS', v)} />
          </div>
        </div>
      </div>

      {/* ─── Time budget ─── */}
      <div className="card section-gap">
        <div className="card-header">
          <div className="card-icon amber">⏱️</div>
          <h3>Session Time Budget</h3>
        </div>
        <div className="card-body">
          <div className="form-grid cols-3">
            <Field label="TIME_BUDGET_MIN" hint="0 = disable guard">
              <input type="number" value={config.TIME_BUDGET_MIN} min={0} max={120} onChange={e => set('TIME_BUDGET_MIN', +e.target.value)} />
            </Field>
            <Field label="RENDER_RESERVE_MIN">
              <input type="number" value={config.RENDER_RESERVE_MIN} min={1} max={20} onChange={e => set('RENDER_RESERVE_MIN', +e.target.value)} />
            </Field>
            <Field label="HEARTBEAT_SECONDS">
              <input type="number" value={config.HEARTBEAT_SECONDS} min={30} max={600} onChange={e => set('HEARTBEAT_SECONDS', +e.target.value)} />
            </Field>
          </div>
        </div>
      </div>

      {/* ─── LLM ─── */}
      <div className="card section-gap">
        <div className="card-header">
          <div className="card-icon cyan">🧠</div>
          <h3>LLM (Script Writing)</h3>
        </div>
        <div className="card-body">
          <div className="form-grid">
            <Field label="LLM_PROVIDER">
              <select value={config.LLM_PROVIDER} onChange={e => set('LLM_PROVIDER', e.target.value)}>
                {LLM_PROVIDERS.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
              </select>
            </Field>
            <Field label="LLM_FALLBACK" hint="blank to disable">
              <input type="text" value={config.LLM_FALLBACK} onChange={e => set('LLM_FALLBACK', e.target.value)} />
            </Field>
            <Field label="OPENROUTER_MODEL" hint={'"auto" = best free live'}>
              <input type="text" value={config.OPENROUTER_MODEL} onChange={e => set('OPENROUTER_MODEL', e.target.value)} />
            </Field>
            <Field label="OPENROUTER_MAX_TRIES">
              <input type="number" value={config.OPENROUTER_MAX_TRIES} min={1} max={20} onChange={e => set('OPENROUTER_MAX_TRIES', +e.target.value)} />
            </Field>
            <Field label="GEMINI_MODEL">
              <input type="text" value={config.GEMINI_MODEL} onChange={e => set('GEMINI_MODEL', e.target.value)} />
            </Field>
            <Field label="CLAUDE_MODEL">
              <input type="text" value={config.CLAUDE_MODEL} onChange={e => set('CLAUDE_MODEL', e.target.value)} />
            </Field>
            <Field label="OLLAMA_MODEL" hint="local; e.g. qwen2.5:7b">
              <input type="text" value={config.OLLAMA_MODEL} onChange={e => set('OLLAMA_MODEL', e.target.value)} />
            </Field>
            <Field label="OLLAMA_CLOUD_MODEL">
              <input type="text" value={config.OLLAMA_CLOUD_MODEL} onChange={e => set('OLLAMA_CLOUD_MODEL', e.target.value)} />
            </Field>
            <Field label="OLLAMA_NUM_CTX">
              <input type="number" value={config.OLLAMA_NUM_CTX} min={2048} max={131072} onChange={e => set('OLLAMA_NUM_CTX', +e.target.value)} />
            </Field>
          </div>
          <div className="form-grid mt-4" style={{ gridTemplateColumns: '1fr 1fr 1fr' }}>
            <Toggle id="OPENROUTER_FALLBACK" label="OPENROUTER_FALLBACK" hint="Try next free model on fail" checked={config.OPENROUTER_FALLBACK} onChange={v => set('OPENROUTER_FALLBACK', v)} />
            <Toggle id="OLLAMA_STOP_AFTER" label="OLLAMA_STOP_AFTER" hint="Free GPU after script done" checked={config.OLLAMA_STOP_AFTER} onChange={v => set('OLLAMA_STOP_AFTER', v)} />
          </div>
        </div>
      </div>

      {/* ─── TTS ─── */}
      <div className="card section-gap">
        <div className="card-header">
          <div className="card-icon emerald">🎙️</div>
          <h3>Text-to-Speech (TTS)</h3>
        </div>
        <div className="card-body">
          <div className="form-grid">
            <Field label="TTS_ENGINE">
              <select value={config.TTS_ENGINE} onChange={e => set('TTS_ENGINE', e.target.value)}>
                {TTS_ENGINES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </Field>
            <Field label="EDGE_VOICE">
              <select value={config.EDGE_VOICE} onChange={e => set('EDGE_VOICE', e.target.value)}>
                {EDGE_VOICES.map(v => <option key={v} value={v}>{v}</option>)}
                <option value={config.EDGE_VOICE}>{config.EDGE_VOICE}</option>
              </select>
            </Field>
            <Field label="EDGE_RATE" hint="e.g. +5% or -10%">
              <input type="text" value={config.EDGE_RATE} onChange={e => set('EDGE_RATE', e.target.value)} />
            </Field>
            <Field label="KOKORO_VOICE" hint="used if TTS_ENGINE=kokoro">
              <input type="text" value={config.KOKORO_VOICE} onChange={e => set('KOKORO_VOICE', e.target.value)} />
            </Field>
          </div>
        </div>
      </div>

      {/* ─── Visuals ─── */}
      <div className="card section-gap">
        <div className="card-header">
          <div className="card-icon indigo">🖼️</div>
          <h3>Visuals & Stock Footage</h3>
        </div>
        <div className="card-body">
          <div className="form-grid">
            <Field label="STOCK_PROVIDER">
              <select value={config.STOCK_PROVIDER} onChange={e => set('STOCK_PROVIDER', e.target.value)}>
                {STOCK_PROVIDERS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
              </select>
            </Field>
            <Field label="AI_IMAGE_STYLE" span2>
              <input type="text" value={config.AI_IMAGE_STYLE} onChange={e => set('AI_IMAGE_STYLE', e.target.value)} />
            </Field>
            <Field label="AI_IMAGE_NEG" span2>
              <input type="text" value={config.AI_IMAGE_NEG} onChange={e => set('AI_IMAGE_NEG', e.target.value)} />
            </Field>
          </div>
          <div className="form-grid mt-4" style={{ gridTemplateColumns: '1fr 1fr 1fr' }}>
            <Toggle id="AI_IMAGES_FOR_KENBURNS" label="AI_IMAGES_FOR_KENBURNS" hint="SDXL for kenburns shots" checked={config.AI_IMAGES_FOR_KENBURNS} onChange={v => set('AI_IMAGES_FOR_KENBURNS', v)} />
            <Toggle id="SPECIFIC_USES_AI" label="SPECIFIC_USES_AI" hint="Specific stock → AI image" checked={config.SPECIFIC_USES_AI} onChange={v => set('SPECIFIC_USES_AI', v)} />
            <Toggle id="ENABLE_SCREEN_RECORDING" label="ENABLE_SCREEN_RECORDING" hint="For app demos" checked={config.ENABLE_SCREEN_RECORDING} onChange={v => set('ENABLE_SCREEN_RECORDING', v)} />
          </div>
        </div>
      </div>

      {/* ─── Captions ─── */}
      <div className="card section-gap">
        <div className="card-header">
          <div className="card-icon amber">📝</div>
          <h3>Captions & Audio</h3>
        </div>
        <div className="card-body">
          <div className="form-grid">
            <Field label="WORDS_PER_CAPTION" hint="3 for portrait, 6 for landscape">
              <input type="number" value={config.WORDS_PER_CAPTION} min={1} max={15} onChange={e => set('WORDS_PER_CAPTION', +e.target.value)} />
            </Field>
            <Field label="MUSIC_VOLUME" hint="0.0 to 1.0">
              <input type="number" value={config.MUSIC_VOLUME} min={0} max={1} step={0.01} onChange={e => set('MUSIC_VOLUME', +e.target.value)} />
            </Field>
            <Field label="MUSIC_PATH" hint="Path on Kaggle; leave blank for none" span2>
              <input type="text" value={config.MUSIC_PATH} placeholder="/kaggle/input/my-music/loop.mp3" onChange={e => set('MUSIC_PATH', e.target.value)} />
            </Field>
          </div>
          <div className="form-grid mt-4" style={{ gridTemplateColumns: '1fr 1fr 1fr' }}>
            <Toggle id="CAPTIONS" label="CAPTIONS" hint="Burn in word-highlight captions" checked={config.CAPTIONS} onChange={v => set('CAPTIONS', v)} />
          </div>
        </div>
      </div>

      {/* ─── Misc ─── */}
      <div className="card">
        <div className="card-header">
          <div className="card-icon violet">🔧</div>
          <h3>Miscellaneous</h3>
        </div>
        <div className="card-body">
          <div className="form-grid cols-3">
            <Toggle id="RESUME" label="RESUME" hint="Reuse existing work files" checked={config.RESUME} onChange={v => set('RESUME', v)} />
            <Toggle id="START_NGROK_UI" label="START_NGROK_UI" hint="Expose ComfyUI via ngrok" checked={config.START_NGROK_UI} onChange={v => set('START_NGROK_UI', v)} />
            <Toggle id="STOP_COMFY_AFTER" label="STOP_COMFY_AFTER" hint="Stop ComfyUI after clips done" checked={config.STOP_COMFY_AFTER} onChange={v => set('STOP_COMFY_AFTER', v)} />
          </div>
        </div>
      </div>
    </div>
  );
}
