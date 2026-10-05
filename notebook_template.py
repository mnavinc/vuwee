"""
KAGGLE (2x T4) SCRIPT-TO-VIDEO PIPELINE  -  multi-model edition
===============================================================
topic / article URL / paper PDF / pasted text
  -> LLM script + shot list (OpenRouter / Ollama / Gemini / Claude)
  -> TTS narration (edge-tts or Kokoro)
  -> per-shot visuals:
        wan      : AI video clip, model chosen by VIDEO_MODEL (see CELL 0)
        stock    : Pixabay / Pexels stock video
        kenburns : SDXL image (or stock photo) with pan/zoom
        card     : generated text card
        screen   : Playwright screen recording of a URL
  -> word-timed captions (faster-whisper) burned in via ffmpeg
  -> optional background music -> final.mp4 (9:16 Shorts or 16:9)

VIDEO_MODEL options (CELL 0)
  wan21             Wan 2.1 1.3B + CausVid LoRA   best quality/speed on T4 (measured ~4.5 min per 5s clip)
  ltxv              LTX-Video 2B 0.9.8 distilled  fastest real video model, lower fidelity
  wan22             Wan 2.2 TI2V-5B               nicer, 24 fps, but slow on T4 (1 GPU only, RAM-heavy)
  cogvideox_2b      CogVideoX-2B (diffusers)      slow, 8 fps native, 1 GPU
  cogvideox_5b      CogVideoX-5B (diffusers)      very slow on T4, not recommended
  animatediff_sd15  AnimateDiff SD1.5 motion      very fast, 2 s clips, low fidelity
  animatediff_sdxl  AnimateDiff SDXL beta         slow, weak motion, not recommended
  hunyuan           NOT supported on a T4 -> falls back to wan21

HOW TO USE
  * Kaggle: Accelerator = GPU T4 x2, Internet = ON.
  * To avoid the interactive idle stop, run it as a BATCH run: top-right "Save Version" ->
    "Save & Run All (Commit)". Batch runs are not subject to the interactive inactivity limit.
  * Add Kaggle Secrets (Add-ons -> Secrets):
        OPENROUTER_API_KEY  (script writing; free key at openrouter.ai/keys, use ":free" models)
        OLLAMA_API_KEY      (only for LLM_PROVIDER = "ollama_cloud"; local "ollama" needs no key)
        GEMINI_API_KEY      (only if LLM_PROVIDER = "gemini")
        ANTHROPIC_API_KEY   (only if LLM_PROVIDER = "claude")
        PIXABAY_API_KEY     (optional, free)
        PEXELS_API_KEY      (optional)
        NGROK_TOKEN         (optional, only to open the ComfyUI UI)
        HF_TOKEN            (optional, faster model downloads)
  * Paste each "# %%" block into its own cell (or run the whole file).
  * Edit CELL 0, run everything. Output: /kaggle/working/final/final.mp4
"""

# %% ============================================================
# CELL 0 - CONFIG  (edit this)
# ===============================================================
import os, sys, re, json, time, shutil, subprocess, queue, textwrap, glob, uuid, threading
from concurrent.futures import ThreadPoolExecutor

NB_T0 = time.time()   # notebook start, used by the time budget below

INPUT        = "Scorpio N 2026 review"      # topic, URL, PDF URL, or full text
INPUT_TYPE   = "topic"                            # topic | url | pdf_url | text
CONTENT_TYPE = "car_review"                        # short | explainer | news | research |
                                                  # app_demo | tech_review | car_review | movie_review
ORIENTATION  = "landscape"                        # portrait (9:16 Shorts) | landscape (16:9)
TARGET_SECONDS = 50                               # ~50 for Shorts, 180+ for explainers
LANGUAGE     = "en"                               # narration language (whisper/LLM)

# --- AI VIDEO MODEL (the "wan" shots) ---
VIDEO_MODEL  = "wan21"
#   wan21 | ltxv | wan22 | cogvideox_2b | cogvideox_5b | animatediff_sd15 | animatediff_sdxl | hunyuan
MAX_WAN_SHOTS = None   # None = automatic per model (wan21 6, ltxv 8, wan22 3, cogvideox_2b 3, animatediff 8...). Or set an int.

# --- Session time guard (Kaggle stops interactive sessions after ~40 min of inactivity) ---
TIME_BUDGET_MIN    = 36   # stop starting new AI clips when the budget is nearly used; remaining shots use cards/stock
RENDER_RESERVE_MIN = 5    # minutes kept free for the final fit + render. TIME_BUDGET_MIN = 0 disables the guard
HEARTBEAT_SECONDS  = 120  # prints a line every N seconds so the console never looks idle

# --- LLM ---
LLM_PROVIDER = "openrouter"                       # openrouter | ollama | ollama_cloud | gemini | claude
LLM_FALLBACK = "ollama"                           # tried automatically if LLM_PROVIDER fails ("" to disable)
OLLAMA_MODEL = "qwen2.5:7b"                       # local; ~4.7GB download. Others: llama3.1:8b, gemma3:12b, qwen3:8b
OLLAMA_CLOUD_MODEL = "gpt-oss:120b"               # hosted free tier; check ollama.com/search?c=cloud for names
OLLAMA_NUM_CTX = 16384
OLLAMA_STOP_AFTER = True                          # stop local Ollama after the script is written (frees the GPU)
OPENROUTER_MODEL = "auto"                         # "auto" = pick best free model live, or a specific id,
                                                  # e.g. "meta-llama/llama-3.3-70b-instruct:free"
OPENROUTER_FALLBACK = True                        # if a model fails/rate-limits, try the next free model
OPENROUTER_MAX_TRIES = 8
OPENROUTER_PREFER = ["llama-3.3-70b", "qwen3", "qwen-2.5", "deepseek-chat", "deepseek-v3",
                     "gemma-3", "mistral", "llama"]   # name fragments ranked first when picking free models
GEMINI_MODEL = "gemini-2.5-flash"                 # check ai.google.dev/gemini-api/docs/models for current names
CLAUDE_MODEL = "claude-sonnet-5-5"
MANUAL_PLAN  = None   # set a dict (see make_plan docstring) to skip the LLM entirely

# --- TTS ---
TTS_ENGINE   = "edge"                             # edge | kokoro
EDGE_VOICE   = "en-US-AndrewNeural"               # e.g. hi-IN-MadhurNeural, en-GB-RyanNeural
EDGE_RATE    = "+5%"
KOKORO_VOICE = "af_heart"

# --- Visuals (stock / stills) ---
STOCK_PROVIDER     = "pixabay"   # pixabay | pexels | auto | ai  (falls back to "ai" if the key is missing)
AI_IMAGE_STYLE     = ", cinematic photo, natural lighting, sharp focus, high detail"
AI_IMAGE_NEG       = "text, watermark, logo, blurry, low quality, deformed, extra fingers"
AI_IMAGES_FOR_KENBURNS = True # "kenburns" shots = SDXL image of the exact subject (more relevant than stock photos)
SPECIFIC_USES_AI   = True     # stock shots the LLM marks "specific" become AI images
ENABLE_SCREEN_RECORDING = False   # True for app demos (installs Playwright + Chromium)

# --- Per-model settings ---
WAN_FRAMES         = 81       # wan21: 4k+1 frames; 81 = ~5s @16fps. Lower (49/33) = faster
WAN_FPS            = 16
USE_FAST_LORA      = True     # wan21 CausVid LoRA: ~6 steps instead of ~25 (big speedup)
WAN22_FRAMES       = 49       # wan22: 4k+1; 49 = 2s @24fps. 81 would be ~2x slower
WAN22_STEPS        = 20
LTX_FRAMES         = 97       # ltxv: 8k+1; 97 = ~4s @24fps
LTX_STEPS          = 8        # distilled model: 8 steps, cfg 1
COGX_FRAMES        = 49       # cogvideox: 49 frames = 6s @8fps
COGX_STEPS         = 30       # official default is 50; 30 saves ~40% time
ANIM_FRAMES        = 16       # animatediff was trained on 16 frames
ANIM_STEPS         = 25
INTERPOLATE_LOW_FPS = True    # 8 fps models (CogVideoX / AnimateDiff): motion-interpolate to 24 fps
WAN_STYLE_SUFFIX   = ", cinematic lighting, smooth camera motion, high detail"
WAN_NEGATIVE       = "blurry, low quality, static, overexposed, watermark, text, subtitles, deformed, extra fingers, jpeg artifacts, ugly"
GPUS               = [0, 1]   # GPU indices to use (capped automatically per model, see PROFILES)
# NOTE: each ComfyUI instance loads the text encoder into system RAM. If Kaggle kills the
# kernel for RAM, set GPUS = [0].

# --- Captions / audio ---
CAPTIONS       = True
WORDS_PER_CAPTION = 6         # 3 for portrait Shorts, 6 for landscape
MUSIC_PATH     = ""           # e.g. "/kaggle/input/my-music/loop.mp3" (use royalty-free!)
MUSIC_VOLUME   = 0.08

# --- Misc ---
RESUME         = False        # True = reuse existing work files after a crash / time-guard stop (same session or committed run)
START_NGROK_UI = False        # expose ComfyUI UI of GPU0 via ngrok
STOP_COMFY_AFTER = True

# ---- derived ----
W, H = (1080, 1920) if ORIENTATION == "portrait" else (1920, 1080)
ROOT       = "/kaggle/working"
COMFY_DIR  = f"{ROOT}/ComfyUI"
WORK       = f"{ROOT}/work"
FINAL_DIR  = f"{ROOT}/final"
# Models live OUTSIDE /kaggle/working: that folder is capped at ~20 GB and is saved as notebook output,
# so putting ~10 GB of weights there slows down commits and can hit the cap.
MODEL_STORE = ("/kaggle/temp" if os.path.isdir("/kaggle/temp") else "/tmp") + "/models"
os.makedirs(MODEL_STORE, exist_ok=True)
os.environ["HF_HOME"] = f"{MODEL_STORE}/hf"      # diffusers / huggingface_hub cache
MAX_SOURCE_CHARS = 14000
AVG_SHOT_SECONDS = 5.0
DEADLINE = NB_T0 + TIME_BUDGET_MIN * 60 if TIME_BUDGET_MIN else NB_T0 + 1e9

# Wan 2.1 files
UNET = "wan2.1_t2v_1.3B_fp16.safetensors"
CLIP = "umt5_xxl_fp8_e4m3fn_scaled.safetensors"
VAE  = "wan_2.1_vae.safetensors"
LORA = "Wan21_CausVid_bidirect2_T2V_1_3B_lora_rank32.safetensors"
LORA_URL = "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/" + LORA
# Wan 2.2 files (TI2V-5B text-to-video; shares the umt5 encoder above)
UNET22 = "wan2.2_ti2v_5B_fp16.safetensors"
VAE22  = "wan2.2_vae.safetensors"
# LTX-Video files
LTX_CKPT = "ltxv-2b-0.9.8-distilled.safetensors"
LTX_T5   = "t5xxl_fp8_e4m3fn_scaled.safetensors"

if VIDEO_MODEL == "hunyuan":
    print("HunyuanVideo is not offered: the 13B transformer plus its 8B LLM text encoder do not run at a usable "
          "speed on a 15 GB T4. Falling back to wan21.")
    VIDEO_MODEL = "wan21"

def _sz(land, port):
    return land if ORIENTATION == "landscape" else port

# kind: comfy (ComfyUI workflow) | diffusers (worker subprocess per GPU)
# est = rough seconds per clip on one T4 (wan21 is measured from your log; the others are estimates)
PROFILES = {
    "wan21":  dict(kind="comfy", label="Wan 2.1 1.3B + CausVid LoRA", size=_sz((832, 480), (480, 832)),
                   frames=WAN_FRAMES, fps=WAN_FPS, max_gpus=2, est=270, max_shots=6),
    "ltxv":   dict(kind="comfy", label="LTX-Video 2B 0.9.8 distilled", size=_sz((768, 448), (448, 768)),
                   frames=LTX_FRAMES, fps=24, max_gpus=2, est=150, max_shots=8),
    "wan22":  dict(kind="comfy", label="Wan 2.2 TI2V-5B", size=_sz((832, 480), (480, 832)),
                   frames=WAN22_FRAMES, fps=24, max_gpus=1, est=600, max_shots=3),
    "cogvideox_2b": dict(kind="diffusers", label="CogVideoX-2B", size=(720, 480), repo="zai-org/CogVideoX-2b",
                   frames=COGX_FRAMES, fps=8, steps=COGX_STEPS, max_gpus=1, est=420, max_shots=3),
    "cogvideox_5b": dict(kind="diffusers", label="CogVideoX-5B", size=(720, 480), repo="zai-org/CogVideoX-5b",
                   frames=COGX_FRAMES, fps=8, steps=COGX_STEPS, max_gpus=1, est=1500, max_shots=1),
    "animatediff_sd15":  dict(kind="diffusers", label="AnimateDiff SD1.5", size=_sz((768, 432), (432, 768)),
                   frames=ANIM_FRAMES, fps=8, steps=ANIM_STEPS, max_gpus=2, est=60, max_shots=8),
    "animatediff_sdxl":  dict(kind="diffusers", label="AnimateDiff SDXL beta", size=_sz((1024, 576), (576, 1024)),
                   frames=ANIM_FRAMES, fps=8, steps=20, max_gpus=1, est=240, max_shots=4),
}
if VIDEO_MODEL not in PROFILES:
    raise ValueError(f"VIDEO_MODEL must be one of {list(PROFILES)} (or 'hunyuan' which falls back to wan21)")
PROFILE = PROFILES[VIDEO_MODEL]
if MAX_WAN_SHOTS is None:
    MAX_WAN_SHOTS = PROFILE["max_shots"]
GPUS  = GPUS[:PROFILE["max_gpus"]]
PORTS = [8188 + k for k in range(len(GPUS))]
print(f"Video model: {PROFILE['label']} | backend: {PROFILE['kind']} | GPUs: {GPUS} | max AI clips: {MAX_WAN_SHOTS}")

# %% ============================================================
# CELL 1 - GPU CHECK
# ===============================================================
import torch
print("PyTorch:", torch.__version__, "| CUDA:", torch.cuda.is_available())
for i in range(torch.cuda.device_count()):
    p = torch.cuda.get_device_properties(i)
    print(f"GPU {i}: {p.name} - {p.total_memory/1024**3:.1f} GB")
if torch.cuda.device_count() < len(GPUS):
    print("WARNING: fewer GPUs than GPUS config; set accelerator to GPU T4 x2 or edit GPUS.")

# %% ============================================================
# CELL 2 - HELPERS
# ===============================================================
def sh(cmd, check=True):
    """Run a command, streaming output into the notebook cell."""
    p = subprocess.Popen(cmd, shell=isinstance(cmd, str), stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, bufsize=1)
    for line in p.stdout:
        print(line.rstrip())
    p.wait()
    if check and p.returncode != 0:
        raise RuntimeError(f"Command failed ({p.returncode}): {cmd}")
    return p.returncode

def secret(name, default=""):
    try:
        from kaggle_secrets import UserSecretsClient
        return UserSecretsClient().get_secret(name)
    except Exception:
        return os.environ.get(name, default)

# Optional: add a free HF_TOKEN secret (huggingface.co/settings/tokens) for faster model downloads
_hf = secret("HF_TOKEN")
if _hf:
    os.environ["HF_TOKEN"] = _hf

ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p"]

def ff(args):
    r = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + [str(a) for a in args],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg failed:\n" + r.stderr[-1500:])

def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", path], capture_output=True, text=True).stdout.strip()
    return float(out)

def minutes_used():
    return (time.time() - NB_T0) / 60

def out_of_time(extra_seconds=0):
    """True when starting another job of `extra_seconds` would eat into the final-render reserve."""
    return time.time() + extra_seconds > DEADLINE - RENDER_RESERVE_MIN * 60

_hb_stop = threading.Event()
def _heartbeat():
    while not _hb_stop.wait(HEARTBEAT_SECONDS):
        print(f"      [heartbeat] {minutes_used():.0f} min elapsed", flush=True)

# %% ============================================================
# CELL 3 - INSTALL PACKAGES
# ===============================================================
sh("apt-get update -qq && apt-get install -y -qq git wget ffmpeg espeak-ng fonts-liberation fonts-dejavu-core")
sh("pip install -q -U huggingface_hub anthropic google-genai edge-tts faster-whisper trafilatura pypdf pillow requests pyngrok diffusers transformers accelerate safetensors sentencepiece protobuf")
if TTS_ENGINE == "kokoro":
    sh("pip install -q kokoro soundfile")
if ENABLE_SCREEN_RECORDING:
    sh("pip install -q playwright && playwright install --with-deps chromium")

# %% ============================================================
# CELL 4 - INSTALL VIDEO MODEL (ComfyUI + weights, or diffusers weights)
# ===============================================================
HF21 = "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files"
HF22 = "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files"
HF_LTX = "https://huggingface.co/Lightricks/LTX-Video/resolve/main"
HF_T5 = "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main"

def fetch(urls, dest, required=True):
    """Download the first URL that works (resumable). Optional files may fail silently."""
    if os.path.exists(dest) and os.path.getsize(dest) > 1_000_000:
        print("have", os.path.basename(dest)); return True
    for u in ([urls] if isinstance(urls, str) else urls):
        if sh(["wget", "-nv", "-c", u, "-O", dest], check=False) == 0:
            return True
        if os.path.exists(dest):
            os.remove(dest)
    if required:
        raise RuntimeError(f"Could not download {os.path.basename(dest)}")
    print("Optional file failed:", os.path.basename(dest))
    return False

USE_LORA = False
if PROFILE["kind"] == "comfy":
    if not os.path.exists(f"{COMFY_DIR}/main.py"):
        sh(f"cd {ROOT} && git clone --depth 1 https://github.com/Comfy-Org/ComfyUI.git")
        sh(f"cd {COMFY_DIR} && pip install -q -r requirements.txt")
    # weights go to MODEL_STORE (outside /kaggle/working); ComfyUI sees them through symlinks
    for d in ["diffusion_models", "text_encoders", "vae", "loras", "checkpoints"]:
        real, link = f"{MODEL_STORE}/{d}", f"{COMFY_DIR}/models/{d}"
        os.makedirs(real, exist_ok=True)
        if not os.path.islink(link):
            shutil.rmtree(link, ignore_errors=True)
            os.symlink(real, link)
    M = MODEL_STORE
    if VIDEO_MODEL == "wan21":
        fetch(f"{HF21}/diffusion_models/{UNET}", f"{M}/diffusion_models/{UNET}")
        fetch(f"{HF21}/text_encoders/{CLIP}",    f"{M}/text_encoders/{CLIP}")
        fetch(f"{HF21}/vae/{VAE}",               f"{M}/vae/{VAE}")
        fetch(LORA_URL, f"{M}/loras/{LORA}", required=False)
        USE_LORA = USE_FAST_LORA and os.path.exists(f"{M}/loras/{LORA}")
        print("Fast LoRA:", "ON (6 steps, cfg 1)" if USE_LORA else "OFF (25 steps, cfg 6 - slow)")
    elif VIDEO_MODEL == "wan22":
        fetch(f"{HF22}/diffusion_models/{UNET22}", f"{M}/diffusion_models/{UNET22}")
        fetch(f"{HF21}/text_encoders/{CLIP}",      f"{M}/text_encoders/{CLIP}")
        fetch(f"{HF22}/vae/{VAE22}",               f"{M}/vae/{VAE22}")
    elif VIDEO_MODEL == "ltxv":
        fetch(f"{HF_LTX}/{LTX_CKPT}", f"{M}/checkpoints/{LTX_CKPT}")
        fetch([f"{HF_T5}/{LTX_T5}", f"{HF_T5}/t5xxl_fp8_e4m3fn.safetensors"], f"{M}/text_encoders/{LTX_T5}")
else:
    if VIDEO_MODEL.startswith("cogvideox"):
        from huggingface_hub import snapshot_download
        print("Downloading", PROFILE["repo"], "(~14 GB for 2B, ~20 GB for 5B; stored outside /kaggle/working)")
        snapshot_download(PROFILE["repo"])
    # animatediff weights are fetched by the worker on first use (small: ~2-5 GB)

# %% ============================================================
# CELL 5 - COMFYUI: ONE INSTANCE PER GPU  (only used by comfy-backend models)
# ===============================================================
import requests
CLIENT_ID = str(uuid.uuid4())
_comfy_procs = []

def comfy_up(port):
    try:
        return requests.get(f"http://127.0.0.1:{port}/system_stats", timeout=3).ok
    except Exception:
        return False

def start_comfy():
    if all(comfy_up(p) for p in PORTS):
        return
    subprocess.run(["pkill", "-f", "main.py --listen"], capture_output=True)
    time.sleep(2)
    for gpu, port in zip(GPUS, PORTS):
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = str(gpu)
        log = open(f"{ROOT}/comfy_{gpu}.log", "w")
        _comfy_procs.append(subprocess.Popen(
            ["python", "main.py", "--listen", "127.0.0.1", "--port", str(port),
             "--use-pytorch-cross-attention"],
            cwd=COMFY_DIR, env=env, stdout=log, stderr=subprocess.STDOUT))
    for port in PORTS:
        for _ in range(90):
            if comfy_up(port):
                print(f"ComfyUI ready on :{port}"); break
            time.sleep(2)
        else:
            raise RuntimeError(f"ComfyUI on :{port} did not start. See {ROOT}/comfy_*.log")

def stop_comfy():
    for p in _comfy_procs:
        p.terminate()
    subprocess.run(["pkill", "-f", "main.py --listen"], capture_output=True)

def open_ngrok_ui():
    from pyngrok import ngrok
    tok = secret("NGROK_TOKEN")
    if not tok:
        print("Add NGROK_TOKEN to Kaggle Secrets"); return
    ngrok.set_auth_token(tok)
    ngrok.kill()
    print("ComfyUI UI (GPU0):", ngrok.connect(PORTS[0]).public_url)

# %% ============================================================
# CELL 6 - VIDEO GENERATION BACKENDS (ComfyUI workflows + diffusers workers)
# ===============================================================
def _txt(wf, key, text, clip):
    wf[key] = {"class_type": "CLIPTextEncode", "inputs": {"text": text, "clip": clip}}

def build_workflow(prompt, seed, prefix):
    """ComfyUI API-format graph for the selected comfy-backend model."""
    w, h = PROFILE["size"]
    frames = PROFILE["frames"]
    full_prompt = prompt + WAN_STYLE_SUFFIX
    wf = {}
    if VIDEO_MODEL == "wan21":
        wf["1"] = {"class_type": "UNETLoader", "inputs": {"unet_name": UNET, "weight_dtype": "default"}}
        wf["2"] = {"class_type": "CLIPLoader", "inputs": {"clip_name": CLIP, "type": "wan", "device": "default"}}
        wf["3"] = {"class_type": "VAELoader", "inputs": {"vae_name": VAE}}
        model = ["1", 0]
        if USE_LORA:
            wf["4"] = {"class_type": "LoraLoaderModelOnly",
                       "inputs": {"model": model, "lora_name": LORA, "strength_model": 1.0}}
            model = ["4", 0]
        wf["5"] = {"class_type": "ModelSamplingSD3", "inputs": {"model": model, "shift": 8.0}}
        _txt(wf, "6", full_prompt, ["2", 0]); _txt(wf, "7", WAN_NEGATIVE, ["2", 0])
        wf["8"] = {"class_type": "EmptyHunyuanLatentVideo",
                   "inputs": {"width": w, "height": h, "length": frames, "batch_size": 1}}
        wf["9"] = {"class_type": "KSampler", "inputs": {
            "model": ["5", 0], "seed": seed, "steps": 6 if USE_LORA else 25,
            "cfg": 1.0 if USE_LORA else 6.0, "sampler_name": "uni_pc", "scheduler": "simple",
            "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["8", 0], "denoise": 1.0}}
        wf["10"] = {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["3", 0]}}
        wf["11"] = {"class_type": "SaveImage", "inputs": {"images": ["10", 0], "filename_prefix": prefix}}
    elif VIDEO_MODEL == "wan22":
        # TI2V-5B: single model, 16x16x4 VAE (width/height must be multiples of 32), 24 fps
        wf["1"] = {"class_type": "UNETLoader", "inputs": {"unet_name": UNET22, "weight_dtype": "default"}}
        wf["2"] = {"class_type": "CLIPLoader", "inputs": {"clip_name": CLIP, "type": "wan", "device": "default"}}
        wf["3"] = {"class_type": "VAELoader", "inputs": {"vae_name": VAE22}}
        wf["5"] = {"class_type": "ModelSamplingSD3", "inputs": {"model": ["1", 0], "shift": 8.0}}
        _txt(wf, "6", full_prompt, ["2", 0]); _txt(wf, "7", WAN_NEGATIVE, ["2", 0])
        wf["8"] = {"class_type": "Wan22ImageToVideoLatent",
                   "inputs": {"vae": ["3", 0], "width": w, "height": h, "length": frames, "batch_size": 1}}
        wf["9"] = {"class_type": "KSampler", "inputs": {
            "model": ["5", 0], "seed": seed, "steps": WAN22_STEPS, "cfg": 5.0,
            "sampler_name": "uni_pc", "scheduler": "simple",
            "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["8", 0], "denoise": 1.0}}
        wf["10"] = {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["3", 0]}}
        wf["11"] = {"class_type": "SaveImage", "inputs": {"images": ["10", 0], "filename_prefix": prefix}}
    elif VIDEO_MODEL == "ltxv":
        # distilled 2B: 8 steps, cfg 1. width/height multiples of 32, frames = 8k+1
        wf["1"] = {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": LTX_CKPT}}
        wf["2"] = {"class_type": "CLIPLoader", "inputs": {"clip_name": LTX_T5, "type": "ltxv", "device": "default"}}
        _txt(wf, "6", full_prompt, ["2", 0]); _txt(wf, "7", WAN_NEGATIVE, ["2", 0])
        wf["8"] = {"class_type": "LTXVConditioning",
                   "inputs": {"positive": ["6", 0], "negative": ["7", 0], "frame_rate": float(PROFILE["fps"])}}
        wf["9"] = {"class_type": "EmptyLTXVLatentVideo",
                   "inputs": {"width": w, "height": h, "length": frames, "batch_size": 1}}
        wf["10"] = {"class_type": "LTXVScheduler", "inputs": {
            "steps": LTX_STEPS, "max_shift": 2.05, "base_shift": 0.95, "stretch": True,
            "terminal": 0.1, "latent": ["9", 0]}}
        wf["11"] = {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}}
        wf["12"] = {"class_type": "SamplerCustom", "inputs": {
            "model": ["1", 0], "add_noise": True, "noise_seed": seed, "cfg": 1.0,
            "positive": ["8", 0], "negative": ["8", 1], "sampler": ["11", 0],
            "sigmas": ["10", 0], "latent_image": ["9", 0]}}
        wf["13"] = {"class_type": "VAEDecode", "inputs": {"samples": ["12", 0], "vae": ["1", 2]}}
        wf["14"] = {"class_type": "SaveImage", "inputs": {"images": ["13", 0], "filename_prefix": prefix}}
    else:
        raise ValueError("build_workflow called for non-comfy model " + VIDEO_MODEL)
    return wf

def comfy_generate(port, prompt, seed, prefix, timeout=3600):
    wf = build_workflow(prompt, seed, prefix)
    r = requests.post(f"http://127.0.0.1:{port}/prompt", json={"prompt": wf, "client_id": CLIENT_ID})
    if r.status_code != 200:
        raise RuntimeError(f"ComfyUI rejected workflow: {r.text[:800]}")
    pid = r.json()["prompt_id"]
    t0 = time.time()
    while time.time() - t0 < timeout:
        h = requests.get(f"http://127.0.0.1:{port}/history/{pid}").json()
        if pid in h:
            st = h[pid].get("status", {})
            if st.get("status_str") == "error":
                raise RuntimeError("ComfyUI error: " + json.dumps(st.get("messages"))[-800:])
            return
        time.sleep(4)
    raise TimeoutError("video generation timed out")

def comfy_clip(port, idx, prompt):
    out_mp4 = f"{WORK}/vid_{idx:03d}.mp4"
    if RESUME and os.path.exists(out_mp4):
        return out_mp4
    prefix = f"shot{idx:03d}"
    for f in glob.glob(f"{COMFY_DIR}/output/{prefix}_*.png"):
        os.remove(f)
    comfy_generate(port, prompt, seed=idx * 1000 + 7, prefix=prefix)
    ff(["-framerate", PROFILE["fps"], "-i", f"{COMFY_DIR}/output/{prefix}_%05d_.png",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", out_mp4])
    for f in glob.glob(f"{COMFY_DIR}/output/{prefix}_*.png"):   # free disk (/kaggle/working is capped)
        os.remove(f)
    return out_mp4

# ---- diffusers backend: one worker subprocess per GPU (isolated VRAM, freed when it exits) ----
WORKER_SRC = r'''
import sys, json, time, os, subprocess, shutil
import torch

cfg = json.load(open(sys.argv[1]))
model, W, H, F, FPS = cfg["model"], cfg["w"], cfg["h"], cfg["frames"], cfg["fps"]
steps, neg, deadline, est = cfg["steps"], cfg["negative"], cfg["deadline"], cfg["est"]
f16 = torch.float16

if model.startswith("cogvideox"):
    from diffusers import CogVideoXPipeline
    pipe = CogVideoXPipeline.from_pretrained(cfg["repo"], torch_dtype=f16)
    pipe.enable_model_cpu_offload()
    pipe.vae.enable_tiling(); pipe.vae.enable_slicing()
    def run(prompt, seed):
        return pipe(prompt=prompt, num_frames=F, num_inference_steps=steps, guidance_scale=6.0,
                    generator=torch.Generator("cpu").manual_seed(seed)).frames[0]
elif model == "animatediff_sd15":
    from diffusers import AnimateDiffPipeline, MotionAdapter, DDIMScheduler, AutoencoderKL
    adapter = MotionAdapter.from_pretrained("guoyww/animatediff-motion-adapter-v1-5-3", torch_dtype=f16)
    pipe = AnimateDiffPipeline.from_pretrained("SG161222/Realistic_Vision_V5.1_noVAE",
                                               motion_adapter=adapter, torch_dtype=f16)
    pipe.vae = AutoencoderKL.from_pretrained("stabilityai/sd-vae-ft-mse", torch_dtype=f16)
    pipe.scheduler = DDIMScheduler.from_config(pipe.scheduler.config, clip_sample=False,
                                               timestep_spacing="linspace", beta_schedule="linear", steps_offset=1)
    pipe.enable_vae_slicing(); pipe.to("cuda")
    def run(prompt, seed):
        return pipe(prompt=prompt, negative_prompt=neg, num_frames=F, guidance_scale=7.5,
                    num_inference_steps=steps, width=W, height=H,
                    generator=torch.Generator("cpu").manual_seed(seed)).frames[0]
elif model == "animatediff_sdxl":
    from diffusers import AnimateDiffSDXLPipeline, MotionAdapter, DDIMScheduler
    sid = "stabilityai/stable-diffusion-xl-base-1.0"
    adapter = MotionAdapter.from_pretrained("guoyww/animatediff-motion-adapter-sdxl-beta", torch_dtype=f16)
    sched = DDIMScheduler.from_pretrained(sid, subfolder="scheduler", clip_sample=False,
                                          timestep_spacing="linspace", beta_schedule="linear", steps_offset=1)
    pipe = AnimateDiffSDXLPipeline.from_pretrained(sid, motion_adapter=adapter, scheduler=sched,
                                                   torch_dtype=f16, variant="fp16")
    pipe.enable_vae_slicing(); pipe.enable_vae_tiling(); pipe.enable_model_cpu_offload()
    def run(prompt, seed):
        return pipe(prompt=prompt, negative_prompt=neg, num_frames=F, guidance_scale=8.0,
                    num_inference_steps=steps, width=W, height=H,
                    generator=torch.Generator("cpu").manual_seed(seed)).frames[0]
else:
    raise SystemExit("unknown model " + model)

def encode(frames, out):
    d = out + "_frames"
    shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    for k, fr in enumerate(frames):
        fr.save(f"{d}/{k:05d}.png")
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-framerate", str(FPS),
                    "-i", f"{d}/%05d.png", "-c:v", "libx264", "-pix_fmt", "yuv420p", out], check=True)
    shutil.rmtree(d, ignore_errors=True)

for idx, prompt, out in cfg["jobs"]:
    if time.time() + est > deadline:
        print(f"WORKER skip shot {idx}: time budget", flush=True)
        continue
    t0 = time.time()
    try:
        encode(run(prompt, idx * 1000 + 7), out)
        print(f"WORKER shot {idx} done in {time.time()-t0:.0f}s", flush=True)
    except Exception as e:
        print(f"WORKER shot {idx} FAILED: {e!r}", flush=True)
    torch.cuda.empty_cache()
'''

def smooth_fps(src, out, target=24):
    """Motion-interpolate low-fps clips (8 fps models) so they don't look choppy after the 30 fps conversion."""
    try:
        ff(["-i", src, "-vf", f"minterpolate=fps={target}:mi_mode=mci:mc_mode=aobmc:vsbmc=1",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", out])
        return out
    except Exception as e:
        print("      interpolation failed, using raw clip:", str(e)[:120])
        return src

def diffusers_batch(items):
    """items: {shot_idx: prompt}. Returns {shot_idx: mp4 path} for the clips that were produced."""
    P = PROFILE
    out, todo = {}, {}
    for i, p in items.items():
        path = f"{WORK}/vid_{i:03d}.mp4"
        if RESUME and os.path.exists(path):
            out[i] = path
        else:
            todo[i] = (p, path)
    if not todo:
        return out
    open(f"{WORK}/vid_worker.py", "w").write(WORKER_SRC)
    n = max(1, min(len(GPUS), len(todo)))
    ids, procs = list(todo), []

    def pump(proc, k):
        for line in proc.stdout:
            print(f"      [gpu{k}] {line.rstrip()}")

    for k in range(n):
        cfg = {"model": VIDEO_MODEL, "repo": P.get("repo", ""), "w": P["size"][0], "h": P["size"][1],
               "frames": P["frames"], "fps": P["fps"], "steps": P.get("steps", 25),
               "negative": WAN_NEGATIVE, "deadline": DEADLINE - RENDER_RESERVE_MIN * 60, "est": P["est"],
               "jobs": [[i, todo[i][0] + WAN_STYLE_SUFFIX, todo[i][1]] for i in ids[k::n]]}
        cf = f"{WORK}/vid_jobs_{k}.json"
        json.dump(cfg, open(cf, "w"))
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = str(GPUS[k])
        pr = subprocess.Popen([sys.executable, f"{WORK}/vid_worker.py", cf], env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        threading.Thread(target=pump, args=(pr, GPUS[k]), daemon=True).start()
        procs.append(pr)
        if n > 1:
            time.sleep(20)      # stagger model loading so system RAM does not spike twice at once
    for pr in procs:
        pr.wait()
    for i, (p, path) in todo.items():
        if os.path.exists(path):
            if P["fps"] <= 12 and INTERPOLATE_LOW_FPS:
                path = smooth_fps(path, path.replace(".mp4", "_i.mp4"))
            out[i] = path
    return out

# %% ============================================================
# CELL 7 - SOURCE TEXT + LLM SCRIPT PLANNER
# ===============================================================
def get_source_text():
    if INPUT_TYPE == "topic":
        return INPUT
    if INPUT_TYPE == "text":
        return INPUT[:MAX_SOURCE_CHARS]
    if INPUT_TYPE == "url":
        import trafilatura
        html = trafilatura.fetch_url(INPUT)
        txt = trafilatura.extract(html) if html else None
        if not txt:
            raise RuntimeError("Could not extract the page. Paste the text and use INPUT_TYPE='text'.")
        return txt[:MAX_SOURCE_CHARS]
    if INPUT_TYPE == "pdf_url":
        from pypdf import PdfReader
        pdf = f"{WORK}/source.pdf"
        with open(pdf, "wb") as f:
            f.write(requests.get(INPUT, timeout=60).content)
        reader = PdfReader(pdf)
        txt = "\n".join((pg.extract_text() or "") for pg in reader.pages[:25])
        return txt[:MAX_SOURCE_CHARS]
    raise ValueError("INPUT_TYPE must be topic | url | pdf_url | text")

CONTENT_GUIDE = {
    "short": "Fast hook in the first sentence, punchy, one idea, end with a call to action.",
    "explainer": "Hook, then context, then how it works step by step, then takeaway. Use analogies.",
    "news": "Neutral tone. Lead with the key fact, then context, who/what/when/why. Attribute claims to the source.",
    "research": "Problem, method, key results, limitations, why it matters. Do not overstate findings.",
    "app_demo": "Problem, quick tour of 3-5 features, who it's for. Use 'screen' visuals ONLY for URLs given in the source.",
    "tech_review": "Specs and positives/negatives drawn ONLY from the source. Never invent benchmarks.",
    "car_review": "Specs and impressions drawn ONLY from the source. Never invent numbers or test results.",
    "movie_review": "Spoiler-free opinion and themes. Do not describe specific scenes as if shown; use generic atmospheric visuals.",
}

def list_free_openrouter_models():
    """Live list of free text models from OpenRouter (public endpoint), best candidates first."""
    r = requests.get("https://openrouter.ai/api/v1/models", timeout=30)
    r.raise_for_status()
    free = []
    for m in r.json().get("data", []):
        p = m.get("pricing", {})
        try:
            is_free = float(p.get("prompt", 1)) == 0 and float(p.get("completion", 1)) == 0
        except (TypeError, ValueError):
            continue
        outs = (m.get("architecture") or {}).get("output_modalities") or ["text"]
        if (is_free and outs == ["text"] and (m.get("context_length") or 0) >= 16000
                and m["id"].endswith(":free") and "stealth" not in m["id"].lower()):
            free.append(m)

    def rank(m):
        mid = m["id"].lower()
        pref = next((i for i, frag in enumerate(OPENROUTER_PREFER) if frag in mid), len(OPENROUTER_PREFER))
        slow = any(t in mid for t in ("r1", "thinking", "reasoning"))   # reasoning models are slower / messier for JSON
        return (slow, pref, -(m.get("context_length") or 0))
    return sorted(free, key=rank)

def extract_json(text):
    """Pull the first JSON object that contains 'shots' out of messy LLM output (think tags, fences, trailing commas)."""
    if not text or not text.strip():
        raise ValueError("empty response")
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    text = re.sub(r"```(?:json)?", "", text)
    dec = json.JSONDecoder()
    for m in re.finditer(r"\{", text):
        chunk = text[m.start():]
        for candidate in (chunk, re.sub(r",\s*([}\]])", r"\1", chunk)):
            try:
                obj, _ = dec.raw_decode(candidate)
            except ValueError:
                continue
            if isinstance(obj, dict) and obj.get("shots"):
                return obj
    raise ValueError("no valid JSON with 'shots'; response starts: " + text.strip()[:120].replace("\n", " "))

def _openrouter_chat(model, system, user, key):
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    base = {"model": model, "temperature": 0.7, "max_tokens": 8000,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    # First try with JSON mode + low reasoning effort (many free models support them); fall back to plain on HTTP 400
    extras = {"response_format": {"type": "json_object"}, "reasoning": {"effort": "low", "exclude": True}}
    r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers,
                      json={**base, **extras}, timeout=300)
    if r.status_code == 400:
        r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=base, timeout=300)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    data = r.json()
    if data.get("error"):
        raise RuntimeError(str(data["error"])[:300])
    msg = data["choices"][0]["message"]
    return msg.get("content") or msg.get("reasoning") or ""   # some reasoning models leave content empty

PLAN_SCHEMA = {   # Ollama enforces this structure while generating, which helps small local models a lot
    "type": "object",
    "properties": {
        "title": {"type": "string"}, "description": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "visual_anchor": {"type": "string"},
        "shots": {"type": "array", "items": {"type": "object", "properties": {
            "narration": {"type": "string"},
            "visual": {"type": "string", "enum": ["wan", "stock", "kenburns", "card", "screen"]},
            "wan_prompt": {"type": "string"}, "stock_query": {"type": "string"},
            "stock_queries": {"type": "array", "items": {"type": "string"}},
            "specific": {"type": "boolean"}, "image_prompt": {"type": "string"},
            "on_screen_text": {"type": "string"}, "url": {"type": "string"}},
            "required": ["narration", "visual"]}}},
    "required": ["title", "shots"]}

_ollama_proc = None

def _ollama_up():
    try:
        return requests.get("http://127.0.0.1:11434/api/tags", timeout=3).ok
    except Exception:
        return False

def ensure_ollama():
    """Install (first run), start and pull the model for local Ollama."""
    global _ollama_proc
    if not _ollama_up():
        if shutil.which("ollama") is None:
            sh("apt-get install -y -qq zstd")                      # the installer needs zstd
            sh("curl -fsSL https://ollama.com/install.sh | sh")
        _ollama_proc = subprocess.Popen(["ollama", "serve"], stdout=open(f"{ROOT}/ollama.log", "w"),
                                        stderr=subprocess.STDOUT)
        for _ in range(60):
            if _ollama_up():
                break
            time.sleep(1)
        else:
            raise RuntimeError(f"Ollama server did not start. See {ROOT}/ollama.log")
    have = [m["name"] for m in requests.get("http://127.0.0.1:11434/api/tags", timeout=10).json().get("models", [])]
    if not any(n == OLLAMA_MODEL or n.startswith(OLLAMA_MODEL + ":") for n in have):
        sh(["ollama", "pull", OLLAMA_MODEL])

def stop_ollama():
    global _ollama_proc
    if _ollama_proc:
        _ollama_proc.terminate()
        _ollama_proc = None
    subprocess.run(["pkill", "-f", "ollama serve"], capture_output=True)

def _call_provider(provider, system, user):
    """Send the prompt to one provider (OpenRouter, Ollama local/cloud, Gemini or Claude) and return JSON text."""
    if provider == "openrouter":
        key = secret("OPENROUTER_API_KEY")
        if not key:
            raise RuntimeError("Add OPENROUTER_API_KEY (openrouter.ai/keys) to Kaggle Secrets, or set MANUAL_PLAN.")
        free = [m["id"] for m in list_free_openrouter_models()]
        print("      free models available:", len(free), "| top:", free[:5])
        if OPENROUTER_MODEL != "auto":
            candidates = [OPENROUTER_MODEL] + ([m for m in free if m != OPENROUTER_MODEL] if OPENROUTER_FALLBACK else [])
        else:
            candidates = free
        last_err = None
        for model in candidates[:OPENROUTER_MAX_TRIES]:
            for attempt in range(2):
                try:
                    print(f"      LLM: {model}" + (" (retry)" if attempt else ""))
                    return json.dumps(extract_json(_openrouter_chat(model, system, user, key)))
                except Exception as e:
                    last_err = e
                    msg = str(e)
                    print(f"      {model} failed: {msg[:220]}")
                    if attempt == 0 and any(x in msg for x in ("429", "502", "503", "overloaded", "empty response")):
                        time.sleep(8)      # transient provider problem: retry the same model once
                        continue
                    break
        raise RuntimeError(f"All OpenRouter models failed. Last error: {last_err}. "
                           "Try again later, pick a model in OPENROUTER_MODEL, or set MANUAL_PLAN.")
    if provider in ("ollama", "ollama_cloud"):
        payload = {"stream": False, "format": PLAN_SCHEMA,
                   "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                   "options": {"temperature": 0.7, "num_ctx": OLLAMA_NUM_CTX, "num_predict": 8192}}
        try:
            if provider == "ollama":
                ensure_ollama()
                url, headers = "http://127.0.0.1:11434/api/chat", {}
                payload["model"], payload["keep_alive"] = OLLAMA_MODEL, 0     # unload from VRAM after answering
            else:
                key = secret("OLLAMA_API_KEY")
                if not key:
                    raise RuntimeError("Add OLLAMA_API_KEY (ollama.com/settings/keys) to Kaggle Secrets.")
                url, headers = "https://ollama.com/api/chat", {"Authorization": f"Bearer {key}"}
                payload["model"] = OLLAMA_CLOUD_MODEL
            print(f"      Ollama model: {payload['model']}")
            r = requests.post(url, json=payload, headers=headers, timeout=1200)
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
            return json.dumps(extract_json(r.json().get("message", {}).get("content", "")))
        finally:
            if provider == "ollama" and OLLAMA_STOP_AFTER:
                stop_ollama()
    if provider == "gemini":
        from google import genai
        from google.genai import types
        key = secret("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("Add GEMINI_API_KEY (from aistudio.google.com/apikey) to Kaggle Secrets, or set MANUAL_PLAN.")
        client = genai.Client(api_key=key)
        resp = client.models.generate_content(
            model=GEMINI_MODEL, contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",   # forces valid JSON output
                max_output_tokens=8000,
                temperature=0.7))
        return resp.text
    import anthropic
    key = secret("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("Add ANTHROPIC_API_KEY to Kaggle Secrets, or set MANUAL_PLAN.")
    msg = anthropic.Anthropic(api_key=key).messages.create(
        model=CLAUDE_MODEL, max_tokens=8000, system=system,
        messages=[{"role": "user", "content": user}])
    return "".join(b.text for b in msg.content if b.type == "text")

def call_llm(system, user):
    chain = [LLM_PROVIDER] + ([LLM_FALLBACK] if LLM_FALLBACK and LLM_FALLBACK != LLM_PROVIDER else [])
    last = None
    for prov in chain:
        try:
            print(f"      LLM provider: {prov}")
            return _call_provider(prov, system, user)
        except Exception as e:
            last = e
            print(f"      provider '{prov}' failed: {str(e)[:250]}")
    raise RuntimeError(f"All LLM providers failed ({chain}). Last error: {last}. Set MANUAL_PLAN to skip the LLM.")

def make_plan(source):
    """
    Returns dict:
      {"title","description","tags":[...],
       "shots":[{"narration","visual":"wan|stock|kenburns|card|screen",
                 "wan_prompt","stock_query","on_screen_text","url"}]}
    ("wan" = AI video clip from whichever VIDEO_MODEL is selected.)
    Pass your own dict as MANUAL_PLAN to skip the LLM.
    """
    n_shots = max(4, round(TARGET_SECONDS / AVG_SHOT_SECONDS))
    words_per_shot = int(AVG_SHOT_SECONDS * 2.6)

    system = f"""You are a YouTube producer. You write the narration script and plan visuals.
Return ONLY one JSON object, no markdown fences, with this shape:
{{"title": str, "description": str, "tags": [str], "visual_anchor": str, "shots": [{{"narration": str,
"visual": "wan"|"stock"|"kenburns"|"card"|"screen", "wan_prompt": str,
"stock_query": str, "stock_queries": [str], "specific": bool, "image_prompt": str,
"on_screen_text": str, "url": str}}]}}

Rules:
- Exactly about {n_shots} shots; each narration about {words_per_shot} words, in language "{LANGUAGE}".
- Content type: {CONTENT_TYPE}. {CONTENT_GUIDE.get(CONTENT_TYPE, '')}
- Use ONLY facts from the provided source (or well-established general knowledge for a plain topic). Do not invent statistics, quotes or specs.
- "wan" = AI-generated clip: use for at most {MAX_WAN_SHOTS} shots, ONLY for abstract/atmospheric/metaphorical imagery
  (no readable text, no specific real people, no real products, no logos). wan_prompt: one vivid English sentence describing subject, setting, motion, lighting.
- "stock" = real stock footage, ONLY for generic real-world scenes (people working, nature, traffic, offices, crowds).
  Give stock_queries: 3 English search queries ordered from most specific (3-4 words naming the actual subject)
  to most generic (1-2 words), and also stock_query = the first one. Set "specific": true if the narration depicts
  a particular concept, product, event or technology that stock footage is unlikely to match; those shots will be
  generated as images instead.
- "kenburns" = a still image with slow zoom; give stock_query AND image_prompt (one vivid English sentence for an
  image generator: subject, setting, lighting; no readable text, no real people, no logos or real products).
- "card" = text card; put a short title/stat (max 10 words) in on_screen_text.
- "screen" = screen recording; ONLY if a URL appears in the source; put it in url.
- visual_anchor: one phrase (max 15 words) naming the video's main subject plus one consistent visual style,
  e.g. "neural network diagrams, glowing blue circuitry, dark background". It is appended to every generated prompt.
- RELEVANCE: every shot's visual must literally illustrate what THAT shot's narration says. Put the concrete subject,
  object or action from the narration into wan_prompt / image_prompt (e.g. "a robot translating a sentence between
  two languages"), never generic filler like "abstract technology", "glowing data" or "city skyline".
- Prefer "kenburns" (generated image) or "wan" over "stock" whenever the subject is specific.
- Vary visual types; use cards for numbers/key points.
- First shot must be a strong hook. Last shot: takeaway or call to action.
- description: 2-3 sentences plus a line listing the source if one was given."""

    user = f"Source ({INPUT_TYPE}):\n\n{source}\n\nTarget length: {TARGET_SECONDS} seconds."
    text = call_llm(system, user)
    return extract_json(text)

def normalize_plan(plan, stock_mode):
    """stock_mode: 'api' (download real stock) or 'ai' (generate stills with SDXL, no stock key needed)."""
    wan_used = 0
    fallback_visual = "kenburns" if stock_mode == "ai" else "stock"
    for s in plan["shots"]:
        s.setdefault("visual", "card")
        for k in ("wan_prompt", "stock_query", "image_prompt", "on_screen_text", "url"):
            s.setdefault(k, "")
        s.setdefault("specific", False)
        v = s["visual"]
        if v == "wan":
            wan_used += 1
            if wan_used > MAX_WAN_SHOTS or not s["wan_prompt"]:
                v = fallback_visual
                s["image_prompt"] = s["image_prompt"] or s["wan_prompt"]
                s["stock_query"] = s["stock_query"] or " ".join(s["wan_prompt"].split()[:3])
        if v == "screen" and not (ENABLE_SCREEN_RECORDING and s["url"].startswith("http")):
            v = fallback_visual
        if stock_mode == "ai" and v == "stock":
            v = "kenburns"                      # no stock footage without a key: use a generated still instead
        if v == "stock" and s.get("specific") and SPECIFIC_USES_AI:
            v = "kenburns"                      # specific subject: generate it instead of hoping stock matches
        sq = s.get("stock_queries") or []
        if isinstance(sq, str):
            sq = [sq]
        sq = [q for q in sq if q]
        if not s["stock_query"]:
            s["stock_query"] = (sq[0] if sq else " ".join(re.findall(r"[A-Za-z]+", s["narration"])[:3])) or "abstract"
        s["stock_queries"] = sq or [s["stock_query"]]
        if v == "kenburns" and not s["image_prompt"]:
            s["image_prompt"] = s["wan_prompt"] or s["stock_query"]
        anchor = (plan.get("visual_anchor") or "").strip()
        for key in ("wan_prompt", "image_prompt"):   # keep the subject + style consistent across all generated shots
            if anchor and s[key] and anchor.lower() not in s[key].lower():
                s[key] = s[key].rstrip(". ") + ". " + anchor
        s["visual"] = v
    plan.setdefault("title", "Untitled")
    plan.setdefault("description", "")
    plan.setdefault("tags", [])
    return plan

# %% ============================================================
# CELL 8 - NARRATION (TTS) + WORD TIMESTAMPS
# ===============================================================
_kokoro = None
_whisper = None

def tts(text, out_wav, idx):
    raw = f"{WORK}/tts_{idx:03d}"
    if TTS_ENGINE == "edge":
        txt = raw + ".txt"
        open(txt, "w", encoding="utf-8").write(text)
        sh(["edge-tts", "--file", txt, "--voice", EDGE_VOICE, f"--rate={EDGE_RATE}",
            "--write-media", raw + ".mp3"])
        src = raw + ".mp3"
    else:
        global _kokoro
        import numpy as np, soundfile as sf
        from kokoro import KPipeline
        if _kokoro is None:
            _kokoro = KPipeline(lang_code="a")
        chunks = [a.numpy() if hasattr(a, "numpy") else a for _, _, a in _kokoro(text, voice=KOKORO_VOICE)]
        sf.write(raw + ".wav", np.concatenate(chunks), 24000)
        src = raw + ".wav"
    # 44.1k stereo + 0.35s trailing pause so shots breathe
    ff(["-i", src, "-ar", 44100, "-ac", 2, "-af", "apad=pad_dur=0.35", out_wav])

def transcribe_words(wav, narration):
    """Word-level timestamps. Falls back to even spacing if whisper finds nothing."""
    global _whisper
    from faster_whisper import WhisperModel
    if _whisper is None:
        _whisper = WhisperModel("base", device="cpu", compute_type="int8")  # CPU: keeps both GPUs free
    # Decode with ffmpeg ourselves: faster-whisper's built-in PyAV decoding breaks on some PyAV versions
    import numpy as np
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", wav, "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                       capture_output=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg decode failed: " + r.stderr.decode()[-500:])
    audio = np.frombuffer(r.stdout, dtype=np.float32)
    segs, _ = _whisper.transcribe(audio, word_timestamps=True, language=LANGUAGE)
    words = [(w.word.strip(), w.start, w.end) for s in segs for w in (s.words or []) if w.word.strip()]
    if words:
        return words
    toks, dur = narration.split(), max(probe(wav) - 0.35, 0.5)
    step = dur / max(len(toks), 1)
    return [(t, i * step, (i + 1) * step) for i, t in enumerate(toks)]

# %% ============================================================
# CELL 9 - VISUAL SOURCES (stock, cards, screen recording)
# ===============================================================
PEXELS_KEY = ""
PIXABAY_KEY = ""
STOCK_SRC = "ai"     # resolved in main(): pexels | pixabay | ai
STOCK_MODE = "ai"    # "api" (download real stock) or "ai" (generate images)
_used_stock = set()
_stock_lock = threading.Lock()

def pexels(kind, query, idx):
    orient = "portrait" if ORIENTATION == "portrait" else "landscape"
    url = "https://api.pexels.com/videos/search" if kind == "video" else "https://api.pexels.com/v1/search"
    r = requests.get(url, headers={"Authorization": PEXELS_KEY},
                     params={"query": query, "orientation": orient, "per_page": 10}, timeout=30)
    r.raise_for_status()
    items = r.json().get("videos" if kind == "video" else "photos", [])
    if not items:
        raise RuntimeError(f"No Pexels {kind} results for '{query}'")
    with _stock_lock:   # avoid reusing the same asset across shots
        for it in items:
            if it["id"] not in _used_stock:
                _used_stock.add(it["id"]); break
        else:
            it = items[idx % len(items)]
    if kind == "video":
        files = [f for f in it["video_files"] if f.get("file_type") == "video/mp4"]
        files.sort(key=lambda f: abs((f.get("width") or 0) - (W if ORIENTATION == "landscape" else 1080)))
        link, ext = files[0]["link"], "mp4"
    else:
        link, ext = it["src"].get("large2x") or it["src"]["original"], "jpg"
    dest = f"{WORK}/stock_{idx:03d}.{ext}"
    if not (RESUME and os.path.exists(dest)):
        with open(dest, "wb") as f:
            f.write(requests.get(link, timeout=120).content)
    return dest

def pixabay(kind, query, idx, terms=None, strict=False):
    """Free key at pixabay.com (shown on https://pixabay.com/api/docs/ after sign-up)."""
    portrait = ORIENTATION == "portrait"
    if kind == "video":
        r = requests.get("https://pixabay.com/api/videos/",
                         params={"key": PIXABAY_KEY, "q": query, "per_page": 20}, timeout=30)
    else:
        r = requests.get("https://pixabay.com/api/",
                         params={"key": PIXABAY_KEY, "q": query, "image_type": "photo", "per_page": 20,
                                 "orientation": "vertical" if portrait else "horizontal"}, timeout=30)
    r.raise_for_status()
    hits = r.json().get("hits", [])
    if not hits:
        raise RuntimeError(f"No Pixabay {kind} results for '{query}'")
    if terms:   # rank by how many query words appear in the asset's tags; reject irrelevant results when strict
        score = lambda h: sum(t in h.get("tags", "").lower() for t in terms)
        hits.sort(key=lambda h: -score(h))
        if strict and score(hits[0]) == 0:
            raise RuntimeError(f"No relevant Pixabay {kind} for '{query}'")

    def media(hit):
        if kind == "photo":
            return hit.get("largeImageURL") or hit["webformatURL"], None
        for q in ("large", "medium", "small"):
            v = hit["videos"].get(q, {})
            if v.get("url"):
                return v["url"], (v.get("width", 0), v.get("height", 0))
        return None, None

    pick = None
    with _stock_lock:
        for want_orient in (True, False):          # prefer matching orientation, then anything
            for hit in hits:
                link, size = media(hit)
                if not link or hit["id"] in _used_stock:
                    continue
                if want_orient and size and ((size[1] > size[0]) != portrait):
                    continue
                pick = link; _used_stock.add(hit["id"]); break
            if pick: break
    if not pick:
        pick = media(hits[idx % len(hits)])[0]
    dest = f"{WORK}/stock_{idx:03d}.{'mp4' if kind == 'video' else 'jpg'}"
    if not (RESUME and os.path.exists(dest)):
        with open(dest, "wb") as f:
            f.write(requests.get(pick, timeout=120).content)
    return dest

def stock_fetch(kind, queries, idx):
    """Try queries from most specific to most generic; Pixabay results must match the query tags until the last try."""
    queries = [queries] if isinstance(queries, str) else [q for q in queries if q]
    last_err = None
    for n, q in enumerate(queries):
        final = n == len(queries) - 1
        try:
            if STOCK_SRC == "pexels":
                return pexels(kind, q, idx)
            terms = [t for t in re.findall(r"[a-z]+", q.lower()) if len(t) > 3]
            return pixabay(kind, q, idx, terms=terms, strict=not final)
        except Exception as e:
            last_err = e
    raise last_err or RuntimeError("no stock queries")

def generate_ai_images(items):
    """
    items: {shot_idx: prompt}. Generates stills with SDXL base 1.0 (OpenRAIL++ license, commercial use allowed)
    on GPU 0. Must run BEFORE ComfyUI / the video workers start so the GPU is free; VRAM is released afterwards.
    """
    import gc
    from diffusers import StableDiffusionXLPipeline, AutoencoderKL
    portrait = ORIENTATION == "portrait"
    w, h = (768, 1344) if portrait else (1344, 768)
    out, todo = {}, {}
    for i, p in items.items():
        path = f"{WORK}/ai_{i:03d}.png"
        if RESUME and os.path.exists(path):
            out[i] = path
        else:
            todo[i] = (p, path)
    if not todo:
        return out
    vae = AutoencoderKL.from_pretrained("madebyollin/sdxl-vae-fp16-fix", torch_dtype=torch.float16)
    pipe = StableDiffusionXLPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-base-1.0", vae=vae, torch_dtype=torch.float16,
        variant="fp16", use_safetensors=True).to("cuda:0")
    for i, (p, path) in todo.items():
        t0 = time.time()
        img = pipe(prompt=p + AI_IMAGE_STYLE, negative_prompt=AI_IMAGE_NEG, width=w, height=h,
                   num_inference_steps=25, guidance_scale=6.5,
                   generator=torch.Generator("cuda:0").manual_seed(i * 1000 + 7)).images[0]
        img.save(path)
        out[i] = path
        print(f"      shot {i} [ai image] done in {time.time()-t0:.0f}s")
    del pipe, vae
    gc.collect(); torch.cuda.empty_cache()
    return out

def make_card(text, path, idx):
    from PIL import Image, ImageDraw, ImageFont
    palettes = [((18, 24, 56), (60, 20, 90)), ((8, 50, 60), (10, 20, 40)),
                ((60, 25, 25), (20, 15, 35)), ((20, 45, 30), (10, 20, 25))]
    c1, c2 = palettes[idx % len(palettes)]
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(c1[k] + (c2[k] - c1[k]) * t) for k in range(3)))
    fs = W // 11 if ORIENTATION == "portrait" else H // 9
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", fs)
    except Exception:
        font = ImageFont.load_default()
    max_w, lines, cur = int(W * 0.82), [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if d.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            lines.append(cur); cur = word
    lines.append(cur)
    lh = int(fs * 1.25)
    y = (H - lh * len(lines)) // 2
    for ln in lines:
        d.text(((W - d.textlength(ln, font=font)) / 2, y), ln, font=font, fill=(255, 255, 255))
        y += lh
    img.save(path)
    return path

def screen_record(url, duration, idx):
    """Records a scrolling browser session. Runs in a worker thread (Playwright sync API needs no running asyncio loop)."""
    from playwright.sync_api import sync_playwright
    vp = {"width": 540, "height": 960} if ORIENTATION == "portrait" else {"width": 1280, "height": 720}
    tmp = f"{WORK}/rec_{idx:03d}"
    shutil.rmtree(tmp, ignore_errors=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport=vp, record_video_dir=tmp, record_video_size=vp)
        page = ctx.new_page()
        page.goto(url, wait_until="load", timeout=60000)
        t0 = time.time()
        while time.time() - t0 < duration + 1.0:
            page.mouse.wheel(0, 110)
            page.wait_for_timeout(200)
        vid = page.video.path()
        ctx.close(); b.close()
    return vid

# %% ============================================================
# CELL 10 - NORMALIZE VISUALS TO EXACT-LENGTH CLIPS
# ===============================================================
VF = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps=30,format=yuv420p"

def fit_video(src, dur, out, boomerang=False):
    """Loop/trim a clip to exactly `dur` seconds at WxH, 30fps. Boomerang = forward+reverse (smoother loops for AI clips)."""
    if boomerang and probe(src) < dur:
        bm = out + ".bm.mp4"
        ff(["-i", src, "-filter_complex", "[0:v]split[a][b];[b]reverse[r];[a][r]concat=n=2:v=1[v]",
            "-map", "[v]", "-an", bm])
        src = bm
    ff(["-stream_loop", "-1", "-i", src, "-t", f"{dur:.3f}", "-vf", VF, "-an", "-r", 30, *ENC, out])

def fit_image(img, dur, out, zoom=True):
    frames = int(dur * 30) + 2
    if zoom:
        vf = (f"scale={2*W}:{2*H}:force_original_aspect_ratio=increase,crop={2*W}:{2*H},"
              f"zoompan=z='min(zoom+{0.2/frames:.6f},1.3)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
              f":d={frames}:s={W}x{H}:fps=30,format=yuv420p")
    else:
        vf = VF
    ff(["-i", img, "-t", f"{dur:.3f}", "-vf", vf, "-r", 30, *ENC, out])

def mux(vid, wav, out):
    ff(["-i", vid, "-i", wav, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-ar", 44100, "-ac", 2, "-shortest", out])

# %% ============================================================
# CELL 11 - CAPTIONS (ASS, word highlight) + FINAL RENDER
# ===============================================================
def ass_time(t):
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"

def make_ass(words, path):
    portrait = ORIENTATION == "portrait"
    fs, mv, outline = (96, 430, 7) if portrait else (64, 70, 4)
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Liberation Sans,{fs},&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,{outline},2,2,60,60,{mv},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    n = WORDS_PER_CAPTION
    for c in range(0, len(words), n):
        chunk = words[c:c + n]
        for i, (w, st, en) in enumerate(chunk):
            end = chunk[i + 1][1] if i + 1 < len(chunk) else en + 0.05
            parts = []
            for j, (ww, _, _) in enumerate(chunk):
                ww = ww.upper() if portrait else ww
                parts.append("{\\c&H0000FFFF&}" + ww + "{\\c&HFFFFFF&}" if j == i else ww)
            lines.append(f"Dialogue: 0,{ass_time(st)},{ass_time(max(end, st + 0.05))},Default,,0,0,0,,{' '.join(parts)}")
    open(path, "w", encoding="utf-8").write(head + "\n".join(lines) + "\n")

def final_render(concat_mp4, ass, out):
    music = MUSIC_PATH and os.path.exists(MUSIC_PATH)
    cmd = ["-i", concat_mp4]
    if music:
        cmd += ["-stream_loop", "-1", "-i", MUSIC_PATH]
    fc = f"[0:v]subtitles={ass}[v]" if (CAPTIONS and ass) else "[0:v]null[v]"
    if music:
        fc += (f";[1:a]volume={MUSIC_VOLUME}[m];[0:a][m]amix=inputs=2:duration=first:"
               f"dropout_transition=0:normalize=0[a]")
    cmd += ["-filter_complex", fc, "-map", "[v]", "-map", "[a]" if music else "0:a",
            *ENC, "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out]
    ff(cmd)

# %% ============================================================
# CELL 12 - MAIN ORCHESTRATOR
# ===============================================================
def main():
    global PEXELS_KEY, PIXABAY_KEY, STOCK_SRC, STOCK_MODE
    PEXELS_KEY = secret("PEXELS_API_KEY")
    PIXABAY_KEY = secret("PIXABAY_API_KEY")
    STOCK_SRC = STOCK_PROVIDER
    if STOCK_SRC == "auto":
        STOCK_SRC = "pexels" if PEXELS_KEY else "pixabay" if PIXABAY_KEY else "ai"
    if (STOCK_SRC == "pexels" and not PEXELS_KEY) or (STOCK_SRC == "pixabay" and not PIXABAY_KEY):
        print(f"      no key for {STOCK_SRC}; using AI-generated images instead")
        STOCK_SRC = "ai"
    STOCK_MODE = "ai" if STOCK_SRC == "ai" else "api"
    print(f"Stock source: {STOCK_SRC} | video model: {PROFILE['label']}")
    if not RESUME:
        shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(WORK, exist_ok=True)
    os.makedirs(FINAL_DIR, exist_ok=True)
    t_start = time.time()
    _hb_stop.clear()
    threading.Thread(target=_heartbeat, daemon=True).start()
    skipped = []

    # 1) script + shot list
    print("[1/6] Writing script...")
    plan_file = f"{WORK}/plan.json"
    if RESUME and os.path.exists(plan_file):
        plan = json.load(open(plan_file))
    else:
        plan = normalize_plan(MANUAL_PLAN or make_plan(get_source_text()), STOCK_MODE)
    shots = plan["shots"]
    print(f"      '{plan['title']}' - {len(shots)} shots:",
          {v: sum(1 for s in shots if s['visual'] == v) for v in {s['visual'] for s in shots}})

    # 2) narration + word timings (CPU)
    print("[2/6] Narration + word timing...")
    for i, s in enumerate(shots):
        wav = f"{WORK}/aud_{i:03d}.wav"
        if not (RESUME and os.path.exists(wav)):
            tts(s["narration"], wav, i)
        s["wav"], s["dur"] = wav, probe(wav)
        s["words"] = transcribe_words(wav, s["narration"]) if CAPTIONS else []
    json.dump(plan, open(plan_file, "w"), indent=2)
    print(f"      total narration: {sum(s['dur'] for s in shots):.1f}s")

    # 3) visuals: AI video on GPUs in parallel with stock/cards/screen on CPU threads
    print(f"[3/6] Generating visuals... ({minutes_used():.0f} min used)")
    raw = {}   # idx -> dict(kind, path, boomerang)

    def make_card_visual(i):
        s = shots[i]
        txt = s["on_screen_text"] or " ".join(s["narration"].split()[:8])
        return {"kind": "image", "path": make_card(txt, f"{WORK}/card_{i:03d}.png", i), "zoom": False}

    def stock_visual(i, kind):
        s = shots[i]
        path = stock_fetch(kind, s.get("stock_queries") or s["stock_query"], i)
        return ({"kind": "video", "path": path, "boomerang": False} if kind == "video"
                else {"kind": "image", "path": path, "zoom": True})

    def fallback(i):
        try:
            if STOCK_MODE == "api":
                return stock_visual(i, "video")
        except Exception as e:
            print(f"      shot {i}: stock fallback failed ({e})")
        return make_card_visual(i)

    def cpu_job(i):
        s, v = shots[i], shots[i]["visual"]
        try:
            if v == "stock":    raw[i] = stock_visual(i, "video")
            elif v == "kenburns":
                raw[i] = ({"kind": "image", "path": ai_imgs[i], "zoom": True} if i in ai_imgs
                          else stock_visual(i, "photo"))
            elif v == "card":   raw[i] = make_card_visual(i)
            elif v == "screen":
                raw[i] = {"kind": "video", "path": screen_record(s["url"], s["dur"], i), "boomerang": False}
            print(f"      shot {i} [{v}] done")
        except Exception as e:
            print(f"      shot {i} [{v}] failed: {e} -> fallback")
            raw[i] = fallback(i)

    # AI stills (SDXL) run first, while both GPUs are still free; video backends start afterwards
    ai_imgs = {}
    if STOCK_MODE == "ai" or AI_IMAGES_FOR_KENBURNS:
        wanted = {i: s["image_prompt"] for i, s in enumerate(shots) if s["visual"] == "kenburns"}
        if wanted:
            print(f"      generating {len(wanted)} AI images with SDXL...")
            try:
                ai_imgs = generate_ai_images(wanted)
            except Exception as e:
                print(f"      AI image generation failed ({e}); those shots become text cards")
                ai_imgs = {}

    wan_q = queue.Queue()
    for i, s in enumerate(shots):
        if s["visual"] == "wan":
            wan_q.put(i)
    use_comfy = PROFILE["kind"] == "comfy"
    if not wan_q.empty() and use_comfy:
        start_comfy()
        if START_NGROK_UI:
            open_ngrok_ui()

    def gpu_worker(port):                      # comfy backend: one thread per GPU/port
        while True:
            try:
                i = wan_q.get_nowait()
            except queue.Empty:
                return
            if out_of_time(PROFILE["est"]):
                print(f"      shot {i} [video] skipped: time budget nearly used -> fallback")
                skipped.append(i); raw[i] = fallback(i)
                continue
            t0 = time.time()
            try:
                raw[i] = {"kind": "video", "path": comfy_clip(port, i, shots[i]["wan_prompt"]), "boomerang": True}
                print(f"      shot {i} [{VIDEO_MODEL} @:{port}] done in {time.time()-t0:.0f}s")
            except Exception as e:
                print(f"      shot {i} [{VIDEO_MODEL} @:{port}] failed: {e} -> fallback")
                raw[i] = fallback(i)

    def diffusers_job():                       # diffusers backend: worker subprocess per GPU
        items = {}
        while True:
            try:
                i = wan_q.get_nowait()
            except queue.Empty:
                break
            items[i] = shots[i]["wan_prompt"]
        try:
            res = diffusers_batch(items)
        except Exception as e:
            print(f"      video workers failed: {e}")
            res = {}
        for i in items:
            if i in res:
                raw[i] = {"kind": "video", "path": res[i], "boomerang": True}
            else:
                print(f"      shot {i} [{VIDEO_MODEL}] no clip -> fallback")
                skipped.append(i); raw[i] = fallback(i)

    cpu_ids = [i for i, s in enumerate(shots) if s["visual"] != "wan"]
    has_video = not wan_q.empty()
    n_gpu = len(PORTS) if (has_video and use_comfy) else 0
    with ThreadPoolExecutor(max_workers=max(n_gpu, 1) + 3) as ex:
        futs = [ex.submit(gpu_worker, p) for p in PORTS[:n_gpu]]
        if has_video and not use_comfy:
            futs.append(ex.submit(diffusers_job))
        futs += [ex.submit(cpu_job, i) for i in cpu_ids]
        for f in futs:
            f.result()
    if STOP_COMFY_AFTER and n_gpu:
        stop_comfy()

    # 4) per-shot clips with exact narration length, muxed with audio
    print(f"[4/6] Fitting clips to narration... ({minutes_used():.0f} min used)")
    shot_files = []
    for i, s in enumerate(shots):
        r = raw[i]
        vid = f"{WORK}/fit_{i:03d}.mp4"
        if r["kind"] == "image":
            fit_image(r["path"], s["dur"], vid, zoom=r.get("zoom", True))
        else:
            fit_video(r["path"], s["dur"], vid, boomerang=r.get("boomerang", False))
        out = f"{WORK}/shot_{i:03d}.mp4"
        mux(vid, s["wav"], out)
        shot_files.append(out)

    # 5) concat + captions + music
    print("[5/6] Rendering final video...")
    lst = f"{WORK}/concat.txt"
    open(lst, "w").write("".join(f"file '{p}'\n" for p in shot_files))
    concat = f"{WORK}/concat.mp4"
    ff(["-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", concat])

    ass = None
    if CAPTIONS:
        all_words, offset = [], 0.0
        for s in shots:
            all_words += [(w, st + offset, en + offset) for w, st, en in s["words"]]
            offset += s["dur"]
        ass = f"{WORK}/captions.ass"
        make_ass(all_words, ass)
    final = f"{FINAL_DIR}/final.mp4"
    final_render(concat, ass, final)

    # 6) metadata
    meta = {
        "title": plan["title"], "description": plan["description"], "tags": plan["tags"],
        "duration_seconds": round(probe(final), 1), "video_model": PROFILE["label"],
        "upload_notes": [
            "Disclose realistic AI-generated/altered content in YouTube Studio where required.",
            "Only publish stock/music you are licensed to use; credit sources in the description.",
            "Verify every factual claim against the source before publishing.",
        ],
    }
    json.dump(meta, open(f"{FINAL_DIR}/metadata.json", "w"), indent=2)
    shutil.copy(plan_file, f"{FINAL_DIR}/plan.json")
    _hb_stop.set()
    print(f"[6/6] Done in {(time.time()-t_start)/60:.1f} min -> {final} ({meta['duration_seconds']}s)")
    if skipped:
        print(f"      NOTE: shots {sorted(set(skipped))} got a fallback visual (no time or a failed clip). "
              "Set RESUME=True and run main() again in the same session (or in a new committed run that "
              "keeps /kaggle/working) to generate only the missing clips.")
    return final

# %% ============================================================
# CELL 13 - RUN
# ===============================================================
final_path = main()

# Preview inside the notebook:
# from IPython.display import Video; Video(final_path, embed=True, width=360)
# Download from the Output tab, or: !cd /kaggle/working && zip -r final.zip final

# %% ============================================================
# EXAMPLE MANUAL_PLAN (set in CELL 0 to skip the LLM)
# ===============================================================
# MANUAL_PLAN = {
#   "title": "Test video", "description": "demo", "tags": ["ai"],
#   "shots": [
#     {"narration": "Imagine a machine that reads every book ever written.",
#      "visual": "wan", "wan_prompt": "A glowing library of floating books in a dark cosmic hall, slow camera push-in"},
#     {"narration": "That idea started with a single research paper.",
#      "visual": "card", "on_screen_text": "2017: Attention Is All You Need"},
#     {"narration": "Today it powers search, chat, and code.",
#      "visual": "stock", "stock_query": "server room"},
#   ]}