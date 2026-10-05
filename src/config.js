// Default configuration matching the Kaggle notebook defaults
export const DEFAULT_CONFIG = {
  // Core
  INPUT: 'Scorpio N 2026 review',
  INPUT_TYPE: 'topic',
  CONTENT_TYPE: 'car_review',
  ORIENTATION: 'landscape',
  TARGET_SECONDS: 50,
  LANGUAGE: 'en',

  // Video model
  VIDEO_MODEL: 'wan21',
  MAX_WAN_SHOTS: '',

  // Time budget
  TIME_BUDGET_MIN: 36,
  RENDER_RESERVE_MIN: 5,
  HEARTBEAT_SECONDS: 120,

  // LLM
  LLM_PROVIDER: 'openrouter',
  LLM_FALLBACK: 'ollama',
  OLLAMA_MODEL: 'qwen2.5:7b',
  OLLAMA_CLOUD_MODEL: 'gpt-oss:120b',
  OLLAMA_NUM_CTX: 16384,
  OLLAMA_STOP_AFTER: true,
  OPENROUTER_MODEL: 'auto',
  OPENROUTER_FALLBACK: true,
  OPENROUTER_MAX_TRIES: 8,
  GEMINI_MODEL: 'gemini-2.5-flash',
  CLAUDE_MODEL: 'claude-sonnet-5-5',

  // TTS
  TTS_ENGINE: 'edge',
  EDGE_VOICE: 'en-US-AndrewNeural',
  EDGE_RATE: '+5%',
  KOKORO_VOICE: 'af_heart',

  // Visuals
  STOCK_PROVIDER: 'pixabay',
  AI_IMAGE_STYLE: ', cinematic photo, natural lighting, sharp focus, high detail',
  AI_IMAGE_NEG: 'text, watermark, logo, blurry, low quality, deformed, extra fingers',
  AI_IMAGES_FOR_KENBURNS: true,
  SPECIFIC_USES_AI: true,
  ENABLE_SCREEN_RECORDING: false,

  // Per-model settings
  WAN_FRAMES: 81,
  WAN_FPS: 16,
  USE_FAST_LORA: true,
  WAN22_FRAMES: 49,
  WAN22_STEPS: 20,
  LTX_FRAMES: 97,
  LTX_STEPS: 8,
  COGX_FRAMES: 49,
  COGX_STEPS: 30,
  ANIM_FRAMES: 16,
  ANIM_STEPS: 25,
  INTERPOLATE_LOW_FPS: true,
  WAN_STYLE_SUFFIX: ', cinematic lighting, smooth camera motion, high detail',
  WAN_NEGATIVE: 'blurry, low quality, static, overexposed, watermark, text, subtitles, deformed, extra fingers, jpeg artifacts, ugly',

  // Captions / audio
  CAPTIONS: true,
  WORDS_PER_CAPTION: 6,
  MUSIC_PATH: '',
  MUSIC_VOLUME: 0.08,

  // Misc
  RESUME: false,
  START_NGROK_UI: false,
  STOP_COMFY_AFTER: true,

  MANUAL_PLAN: null,
};

export const VIDEO_MODELS = [
  { value: 'wan21', label: 'Wan 2.1 1.3B + CausVid LoRA', desc: 'Best quality/speed on T4 (~4.5 min/clip)' },
  { value: 'ltxv',  label: 'LTX-Video 2B 0.9.8 distilled', desc: 'Fastest real video model, lower fidelity' },
  { value: 'wan22', label: 'Wan 2.2 TI2V-5B', desc: 'Nicer, 24fps, but slow on T4 (1 GPU only)' },
  { value: 'cogvideox_2b', label: 'CogVideoX-2B', desc: 'Slow, 8fps native, 1 GPU' },
  { value: 'cogvideox_5b', label: 'CogVideoX-5B', desc: 'Very slow on T4, not recommended' },
  { value: 'animatediff_sd15', label: 'AnimateDiff SD1.5', desc: 'Very fast, 2s clips, low fidelity' },
  { value: 'animatediff_sdxl', label: 'AnimateDiff SDXL beta', desc: 'Slow, weak motion, not recommended' },
];

export const CONTENT_TYPES = [
  { value: 'short',        label: 'Short',        desc: 'Fast hook, punchy, one idea' },
  { value: 'explainer',    label: 'Explainer',     desc: 'Hook → context → how it works → takeaway' },
  { value: 'news',         label: 'News',          desc: 'Neutral lead with key facts' },
  { value: 'research',     label: 'Research',      desc: 'Problem, method, results, limitations' },
  { value: 'app_demo',     label: 'App Demo',      desc: 'Problem + feature tour' },
  { value: 'tech_review',  label: 'Tech Review',   desc: 'Specs and pros/cons from source' },
  { value: 'car_review',   label: 'Car Review',    desc: 'Specs and impressions from source' },
  { value: 'movie_review', label: 'Movie Review',  desc: 'Spoiler-free opinion and themes' },
];

export const LLM_PROVIDERS = [
  { value: 'openrouter',   label: 'OpenRouter (free models)' },
  { value: 'gemini',       label: 'Google Gemini' },
  { value: 'claude',       label: 'Anthropic Claude' },
  { value: 'ollama',       label: 'Ollama (local)' },
  { value: 'ollama_cloud', label: 'Ollama Cloud' },
];

export const TTS_ENGINES = [
  { value: 'edge',   label: 'Edge TTS (Microsoft Neural)' },
  { value: 'kokoro', label: 'Kokoro TTS (local, high quality)' },
];

export const EDGE_VOICES = [
  'en-US-AndrewNeural', 'en-US-EmmaNeural', 'en-US-BrianNeural',
  'en-GB-RyanNeural', 'en-GB-SoniaNeural',
  'en-AU-WilliamNeural', 'en-AU-NatashaNeural',
  'en-IN-PrabhatNeural', 'hi-IN-MadhurNeural',
  'en-CA-LiamNeural', 'en-IE-ConnorNeural',
];

export const STOCK_PROVIDERS = [
  { value: 'auto',    label: 'Auto (best available)' },
  { value: 'pixabay', label: 'Pixabay (free key)' },
  { value: 'pexels',  label: 'Pexels (free key)' },
  { value: 'ai',      label: 'AI-only (no stock key needed)' },
];
