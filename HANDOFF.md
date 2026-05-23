# Video Clipper App — Handoff for Claude Code

> Aplikasi web buat ekstrak klip menarik (hype moments, quotes bagus) dari video panjang (stream gaming, podcast). Single-user, deploy lokal via docker-compose.

---

## 1. Tech Stack (FINAL — jangan diganti tanpa konfirmasi)

### Frontend
- **Next.js 15** (App Router, TypeScript strict)
- **Tailwind CSS v4**
- **shadcn/ui** untuk komponen dasar (Button, Dialog, Slider, Progress, dll)
- **TanStack Query** untuk data fetching + polling job status
- **Zustand** untuk client state (kandidat klip yang sedang di-trim)
- **react-player** atau **video.js** untuk preview video + scrubbing

### Backend
- **Python 3.11+**
- **FastAPI** (async)
- **SQLAlchemy 2.0** (async) + **Alembic** untuk migration
- **PostgreSQL 16**
- **Pydantic v2** untuk DTO/validation
- **FastAPI BackgroundTasks** untuk job processing (NO Celery, NO Redis)

### Processing Tools (system dependencies)
- **ffmpeg** — pemotong video, ekstrak audio, encode output, crop aspect ratio
- **yt-dlp** — download dari YouTube / Twitch VOD
- **whisper.cpp** — transcription lokal (CPU-friendly, bundled binary)
- **Twitch GQL / Twitch chat replay scraper** — buat ambil chat density (lihat §6)

### LLM Layer
- **Default provider: Google Gemini API** (`gemini-2.0-flash`, free tier)
- **Wajib pakai abstraction layer** — provider pattern, swap-able ke Ollama, Claude, OpenAI tanpa ubah business logic. Lihat §7.

### Deployment
- **docker-compose** dengan service: `frontend`, `backend`, `postgres`
- ffmpeg, yt-dlp, whisper.cpp di-bundle di image backend
- Volume mounts: `./uploads`, `./outputs`, `./models` (whisper model files)

---

## 2. Folder Structure

```
video-clipper/
├── docker-compose.yml
├── .env.example
├── README.md
│
├── frontend/                          # Next.js
│   ├── app/
│   │   ├── (main)/
│   │   │   ├── page.tsx               # Dashboard: list job
│   │   │   ├── new/page.tsx           # Buat job baru (upload / URL)
│   │   │   └── jobs/[id]/page.tsx     # Detail job + review klip
│   │   ├── api/                       # API routes (proxy ke backend kalau perlu)
│   │   └── layout.tsx
│   ├── components/
│   │   ├── ui/                        # shadcn/ui generated
│   │   ├── job/
│   │   │   ├── job-list.tsx
│   │   │   ├── job-form.tsx
│   │   │   ├── job-progress.tsx
│   │   │   └── job-detail.tsx
│   │   ├── clip/
│   │   │   ├── clip-list.tsx
│   │   │   ├── clip-card.tsx
│   │   │   ├── clip-trim-editor.tsx   # KEY: trim manual UI
│   │   │   └── clip-export-dialog.tsx
│   │   └── shared/
│   ├── lib/
│   │   ├── api/                       # Typed API client (gunakan openapi-typescript)
│   │   ├── hooks/                     # useJob, useClips, useJobProgress
│   │   └── utils.ts
│   ├── types/                         # Mirror dari Pydantic schemas
│   └── tsconfig.json (strict)
│
├── backend/                           # FastAPI
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py                  # Settings via pydantic-settings
│   │   ├── db/
│   │   │   ├── base.py
│   │   │   ├── session.py
│   │   │   └── models/                # SQLAlchemy models
│   │   │       ├── job.py
│   │   │       ├── clip.py
│   │   │       └── transcript.py
│   │   ├── schemas/                   # Pydantic DTOs
│   │   ├── api/
│   │   │   ├── deps.py
│   │   │   └── routes/
│   │   │       ├── jobs.py
│   │   │       ├── clips.py
│   │   │       └── health.py
│   │   ├── services/
│   │   │   ├── pipeline/              # Orchestrator
│   │   │   │   ├── pipeline.py        # Main pipeline runner
│   │   │   │   └── stages.py
│   │   │   ├── source/                # Video acquisition
│   │   │   │   ├── base.py            # SourceProvider abstract
│   │   │   │   ├── local_upload.py
│   │   │   │   └── ytdlp_downloader.py
│   │   │   ├── transcription/
│   │   │   │   ├── base.py
│   │   │   │   └── whisper_cpp.py
│   │   │   ├── detection/             # Lihat §5
│   │   │   │   ├── base.py            # MomentDetector abstract
│   │   │   │   ├── audio_spike.py
│   │   │   │   ├── llm_transcript.py
│   │   │   │   ├── twitch_chat.py
│   │   │   │   ├── manual_marker.py
│   │   │   │   └── aggregator.py      # Merge & dedupe kandidat
│   │   │   ├── ffmpeg/
│   │   │   │   ├── cutter.py          # Cut clip dari source
│   │   │   │   ├── crop.py            # 9:16, 1:1 smart crop
│   │   │   │   └── probe.py           # ffprobe wrapper
│   │   │   ├── llm/                   # Lihat §7
│   │   │   │   ├── base.py            # LLMProvider abstract
│   │   │   │   ├── providers/
│   │   │   │   │   ├── gemini.py
│   │   │   │   │   ├── ollama.py
│   │   │   │   │   ├── claude.py
│   │   │   │   │   └── openai.py
│   │   │   │   ├── prompts/
│   │   │   │   └── factory.py
│   │   │   ├── storage/
│   │   │   │   ├── base.py            # StorageProvider abstract (siap migrasi S3)
│   │   │   │   └── local_fs.py
│   │   │   └── progress/
│   │   │       └── tracker.py         # Update job progress di DB
│   │   ├── workers/
│   │   │   └── job_runner.py          # Entry point untuk BackgroundTasks
│   │   └── utils/
│   ├── alembic/
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
│
├── uploads/                           # Video input (mounted volume)
├── outputs/                           # Klip hasil + .srt (mounted volume)
└── models/                            # whisper.cpp models (mounted volume)
```

---

## 3. Data Model (PostgreSQL)

### `jobs`
| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| source_type | enum(`upload`, `url`) | |
| source_url | text nullable | YouTube/Twitch URL kalau type=url |
| source_path | text nullable | Path video setelah download/upload |
| original_filename | text | |
| duration_seconds | float nullable | Diisi setelah probe |
| status | enum(`pending`, `downloading`, `transcribing`, `detecting`, `ready_for_review`, `exporting`, `completed`, `failed`) | |
| progress_pct | int default 0 | 0–100 |
| progress_message | text | Human-readable status message |
| detection_config | jsonb | Pilihan strategies + params |
| error_message | text nullable | |
| created_at, updated_at | timestamp | |

### `transcripts`
| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| job_id | UUID (FK) | unique |
| segments | jsonb | `[{ start, end, text, confidence }]` (Whisper output) |
| language | text | |
| created_at | timestamp | |

### `clip_candidates`
| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| job_id | UUID (FK) | |
| start_seconds | float | Awal kandidat |
| end_seconds | float | Akhir kandidat |
| user_start_seconds | float nullable | Setelah user trim |
| user_end_seconds | float nullable | Setelah user trim |
| detection_strategy | enum(`audio_spike`, `llm_transcript`, `twitch_chat`, `manual`) | |
| score | float | 0–1, confidence dari detector |
| reason | text | Kenapa dianggap menarik (dari LLM atau strategy) |
| transcript_excerpt | text nullable | Snippet transcript di rentang ini |
| status | enum(`pending`, `selected`, `rejected`, `exporting`, `exported`, `failed`) | |
| exported_paths | jsonb default '{}' | `{ "9_16": "path", "1_1": "path", "srt": "path" }` |
| created_at, updated_at | timestamp | |

**Index:** `(job_id, status)`, `(job_id, start_seconds)`.

---

## 4. API Surface (FastAPI)

Semua respons pakai Pydantic schema. Generate OpenAPI → konsumsi di Next.js via `openapi-typescript` biar fully typed end-to-end.

```
POST   /api/jobs                     # Buat job (multipart upload ATAU JSON dengan URL)
GET    /api/jobs                     # List job (paginated)
GET    /api/jobs/{id}                # Detail job + progress
DELETE /api/jobs/{id}                # Hapus job + files
POST   /api/jobs/{id}/cancel         # Cancel job berjalan

GET    /api/jobs/{id}/transcript     # Transcript hasil Whisper
GET    /api/jobs/{id}/clips          # List kandidat klip
PATCH  /api/clips/{id}               # Update user_start/user_end/status (trim & approve/reject)
POST   /api/clips/{id}/export        # Trigger export (9:16, 1:1, srt) sebagai background task
GET    /api/clips/{id}/preview       # Stream preview (range request) untuk player

GET    /api/files/{path:path}        # Serve output files (validated path traversal)
```

**Job creation flow:**
- `POST /api/jobs` accept dua mode:
  - `multipart/form-data` → field `file` + `detection_config` (JSON string)
  - `application/json` → `{ source_url, detection_config }`
- Validasi `detection_config` pakai Pydantic schema dengan discriminated union per strategy.
- Setelah create, langsung enqueue `BackgroundTasks` untuk `run_pipeline(job_id)`.
- Return job ID. Frontend polling `GET /api/jobs/{id}` setiap 2 detik via TanStack Query.

**Polling vs SSE:** Mulai dengan polling (simple). Kalau jadi laggy, upgrade ke SSE di endpoint `GET /api/jobs/{id}/events`.

---

## 5. Detection Strategies (the heart of the app)

Empat strategi, semua implement interface `MomentDetector`:

```python
class MomentDetector(ABC):
    @abstractmethod
    async def detect(self, ctx: DetectionContext) -> list[ClipCandidate]: ...
```

`DetectionContext` berisi: `video_path`, `audio_path`, `transcript`, `chat_log` (kalau ada), `manual_markers` (kalau ada), `config`.

### 5.1 Audio Spike Detector
- Ekstrak audio mono 16kHz pakai ffmpeg.
- Pakai **librosa** atau **pydub** buat ngitung RMS energy per window (500ms).
- Smoothing pakai moving average.
- Cari spike: window dengan RMS > `mean + N * std` (default N=2).
- Merge spike yang berdekatan (< 3 detik gap) jadi satu klip.
- Padding: extend 8 detik sebelum, 4 detik sesudah spike (configurable).
- Score = normalized intensity.

### 5.2 LLM Transcript Detector
- Chunk transcript jadi window ~2 menit dengan overlap 15 detik.
- Untuk tiap chunk, panggil LLM dengan prompt yang minta:
  - Apakah ada quote bagus / punchline / momen menarik?
  - Output JSON: `{ "moments": [{ "start_sec", "end_sec", "reason", "score" }] }`
- Pakai **structured output** (Gemini JSON mode / response_schema).
- Aggregate ke kandidat klip, dedupe overlapping.

### 5.3 Twitch Chat Density Detector
- Ambil chat replay pakai Twitch GQL API (endpoint `https://gql.twitch.tv/gql` dengan operation `VideoCommentsByOffsetOrCursor`) — open, gak butuh OAuth user, tapi butuh Client-ID.
- Hitung messages-per-second dalam window 5 detik.
- Spike = window > `mean + N * std`. Plus bonus kalau ada banyak emote/Pog/LULW.
- Padding sama kayak audio spike.

### 5.4 Manual Marker
- User input list timestamp via UI (modal sebelum mulai job, atau bisa juga form di detail page kalau auto-detection udah jalan).
- Setiap marker jadi 1 klip dengan default 30 detik (15 sebelum marker, 15 sesudah).

### 5.5 Aggregator
- Jalankan semua strategy yang aktif → list kandidat.
- Dedupe: kalau dua kandidat dari strategi berbeda overlap >50%, merge jadi satu, tag multi-strategy, sum score (weighted).
- Sort by score desc.
- Cap di N kandidat (default 50, configurable).

---

## 6. Source Acquisition

```python
class SourceProvider(ABC):
    @abstractmethod
    async def acquire(self, job: Job) -> AcquiredSource: ...
```

- **LocalUploadProvider:** validate ekstensi (mp4, mkv, mov, webm), max size dari config. Pindah ke `uploads/{job_id}/source.<ext>`.
- **YtDlpDownloader:** wrap `yt-dlp` (gunakan Python binding `yt_dlp` module, jangan subprocess kalau bisa). Download best quality ≤1080p (configurable). Untuk Twitch VOD, ekstrak juga `video_id` buat chat replay.

Setelah acquire, jalankan `ffprobe` buat dapetin `duration_seconds`, simpan di job.

---

## 7. LLM Provider Abstraction

```python
class LLMProvider(ABC):
    @abstractmethod
    async def complete_json(
        self,
        prompt: str,
        schema: dict,
        *,
        model: str | None = None,
        temperature: float = 0.3,
    ) -> dict: ...
```

### Providers wajib di-implement (semua, biar handoff complete):
- **GeminiProvider** (default) — pakai `google-genai` SDK, `gemini-2.0-flash`, native JSON mode via `response_schema`.
- **OllamaProvider** — HTTP call ke `http://ollama:11434/api/chat` (atau host.docker.internal kalau Ollama jalan di host), model default `llama3.1:8b`, JSON mode via `format: "json"`.
- **ClaudeProvider** — `anthropic` SDK, `claude-haiku-4-5`, tool use untuk structured output.
- **OpenAIProvider** — `openai` SDK, `gpt-4o-mini`, response_format JSON schema.

### Factory pattern:
```python
def get_llm_provider(settings: Settings) -> LLMProvider:
    match settings.llm_provider:
        case "gemini": return GeminiProvider(api_key=settings.gemini_api_key)
        case "ollama": return OllamaProvider(base_url=settings.ollama_url, model=settings.ollama_model)
        case "claude": return ClaudeProvider(api_key=settings.anthropic_api_key)
        case "openai": return OpenAIProvider(api_key=settings.openai_api_key)
        case _: raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
```

Konfigurasi via env: `LLM_PROVIDER=gemini`, `GEMINI_API_KEY=...`.

### Prompt strategy
Simpan prompt sebagai template file di `services/llm/prompts/*.txt` atau pakai class-based prompt builder. Jangan inline string di service code.

---

## 8. FFmpeg Operations

### Cutting clip (fast, no re-encode untuk preview):
```
ffmpeg -ss {start} -to {end} -i {input} -c copy {output}
```
**Catatan:** `-c copy` cepet tapi cuts di nearest keyframe. Akurasi cukup buat preview.

### Export final dengan re-encode (akurat + format target):

**9:16 vertical (smart crop, focus center)**:
```
ffmpeg -ss {start} -to {end} -i {input} \
  -vf "crop='ih*9/16':ih:(iw-ih*9/16)/2:0,scale=1080:1920" \
  -c:v libx264 -preset fast -crf 23 \
  -c:a aac -b:a 128k \
  {output_9_16}
```

**1:1 square (center crop)**:
```
ffmpeg -ss {start} -to {end} -i {input} \
  -vf "crop=ih:ih:(iw-ih)/2:0,scale=1080:1080" \
  -c:v libx264 -preset fast -crf 23 \
  -c:a aac -b:a 128k \
  {output_1_1}
```

**Stretch goal (nice-to-have, not MVP):** Face detection / saliency-based smart crop pakai OpenCV alih-alih hard center crop. Implement sebagai opsi `crop_mode: "center" | "smart"` di clip export request. Tambahkan kalau ada waktu, jangan blokir MVP.

### SRT generation
Generate dari `transcript.segments` yang ada di rentang `[user_start, user_end]`. Offset timestamp ke 0 (relatif ke awal klip), bukan ke awal source video. Format SRT standar.

### Wrapper class
```python
class FfmpegRunner:
    async def cut(self, input: Path, output: Path, start: float, end: float, copy_codec: bool = True) -> None: ...
    async def export_vertical(self, ...) -> None: ...
    async def export_square(self, ...) -> None: ...
    async def probe(self, input: Path) -> ProbeResult: ...
```
Gunakan `asyncio.create_subprocess_exec`, capture stderr, parse progress dari `-progress pipe:1` kalau perlu update progress granular saat export.

---

## 9. Pipeline Stages (Orchestrator)

```python
async def run_pipeline(job_id: UUID):
    # Stage 1: Source acquisition (downloading or move upload)
    # Stage 2: Probe (duration, codec info)
    # Stage 3: Extract audio (untuk transcription + audio spike detection)
    # Stage 4: Transcribe (whisper.cpp) → simpan ke transcripts table
    # Stage 5: Fetch chat (kalau Twitch URL & strategy aktif)
    # Stage 6: Run detectors (parallel via asyncio.gather)
    # Stage 7: Aggregate & dedupe → simpan ke clip_candidates
    # Stage 8: Set status = ready_for_review
```

Tiap stage update `job.progress_pct` & `job.progress_message`. Bungkus dengan try/except, set `status=failed` + `error_message` kalau gagal.

**Cancellation:** Cek `job.status == "cancelled"` di awal tiap stage; kalau iya, raise `JobCancelledError` dan cleanup.

---

## 10. Frontend Key UX

### `/new` — Create Job page
- Tab: "Upload File" / "From URL"
- Detection config: 4 checkbox (audio spike, LLM, Twitch chat, manual), masing-masing dengan accordion buat tweak params.
- Kalau URL bukan Twitch, "Twitch chat" disabled otomatis.
- Manual marker: kalau dicentang, muncul textarea buat input timestamp (format `HH:MM:SS, comment`).

### `/jobs/[id]` — Job detail
- Header: progress bar realtime (polling 2s).
- Kalau status `ready_for_review`:
  - Video player di kiri (sticky), playback awal di `source_path`.
  - List klip kandidat di kanan, sortable by score / start time / strategy.
  - Tiap klip card: thumbnail (generate via ffmpeg), badge strategy, score, reason snippet, transcript excerpt.
  - Klik card → load video player ke rentang klip + buka **Trim Editor**.

### Trim Editor (the KEY component)
- Dual-handle slider di timeline klip (range ±10 detik dari kandidat awal).
- Live preview di video player saat handle digeser.
- Tombol: "Save trim", "Approve", "Reject", "Export".
- Export dialog: cek aspect ratio target (9:16 wajib, 1:1 wajib — dua-duanya by default), tombol export.

### Setelah export
- Card berubah jadi state `exported`, tampilin download links untuk tiap file.

---

## 11. Configuration (.env.example)

```
# Database
DATABASE_URL=postgresql+asyncpg://app:app@postgres:5432/clipper

# Storage
UPLOADS_DIR=/data/uploads
OUTPUTS_DIR=/data/outputs
WHISPER_MODELS_DIR=/data/models

# Whisper
WHISPER_MODEL=base.en          # atau small, medium
WHISPER_BIN=/usr/local/bin/whisper-cli

# LLM
LLM_PROVIDER=gemini            # gemini | ollama | claude | openai
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.0-flash
OLLAMA_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.1:8b
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

# Twitch (untuk chat replay)
TWITCH_CLIENT_ID=kimne78kx3ncx6brgo4mv6wki5h1ko    # public web client id, no secret needed

# Detection defaults
AUDIO_SPIKE_STD_MULTIPLIER=2.0
MAX_CANDIDATES_PER_JOB=50

# Limits
MAX_UPLOAD_MB=4096
MAX_VIDEO_DURATION_SEC=14400   # 4 jam
```

---

## 12. Implementation Order (untuk Claude Code, kerjain berurutan)

**Sprint 1 — Foundation**
1. Setup repo: docker-compose, dockerfiles, .env.example, pyproject.toml, package.json.
2. FastAPI skeleton + health check + Postgres connection + Alembic init.
3. Models + initial migration.
4. Next.js skeleton + Tailwind + shadcn/ui init + base layout.

**Sprint 2 — Core pipeline (single strategy untuk validate flow)**
5. Source providers (upload + yt-dlp).
6. FFmpeg wrapper + probe.
7. Whisper.cpp wrapper + transcription stage.
8. **Audio spike detector saja** (paling cepet validasi).
9. Pipeline orchestrator + BackgroundTasks integration.
10. Job CRUD API + create job flow di frontend.

**Sprint 3 — Review & Export**
11. Clip candidate API + list UI.
12. Video player + trim editor.
13. FFmpeg export (9:16 + 1:1) + SRT generation.
14. Export endpoint + download links.

**Sprint 4 — Detection strategies remaining**
15. LLM abstraction layer + Gemini provider.
16. LLM transcript detector.
17. Twitch chat fetcher + chat density detector.
18. Manual marker handling.
19. Aggregator + dedupe.

**Sprint 5 — Polish**
20. Cancel job.
21. Error states + retry.
22. Other LLM providers (Ollama, Claude, OpenAI).
23. README + run docs.

---

## 13. Non-negotiables / Code Quality

- **TypeScript strict mode** di frontend. No `any`.
- **Python type hints everywhere** di backend. Pakai `mypy` strict.
- **All I/O async.** Jangan campur sync DB calls di async route handler.
- **DTO/Schema separation** — DB models ≠ API schemas. Mapper di service layer.
- **Path traversal protection** di endpoint serve file. Pakai `Path.resolve().is_relative_to(allowed_dir)`.
- **Validate semua input** dengan Pydantic. Jangan terima raw dict di endpoint.
- **Idempotency** untuk export — kalau klip udah punya `exported_paths.9_16` dan file ada, skip re-encode.
- **Cleanup** — pas delete job, hapus semua file di `uploads/{job_id}` dan `outputs/{job_id}`.
- **Tests:** Unit test untuk detector logic (audio spike algorithm, aggregator dedupe), integration test untuk pipeline dengan video sample pendek.

---

## 14. Known Pitfalls — Hindari

- **Whisper.cpp model size:** `base.en` ~150MB, `small` ~500MB, `medium` ~1.5GB. Jangan auto-download di container start; bikin entrypoint script yang cek + download kalau belum ada, atau dokumentasikan manual download.
- **FastAPI BackgroundTasks limitation:** Dia jalan in-process. Kalau backend di-restart, job berjalan ilang. Untuk single-user dev ini fine, tapi catat di README — kalau nanti perlu durability, migrasi ke ARQ atau Celery.
- **yt-dlp 403/rate limit:** YouTube/Twitch suka block IP. Sediakan opsi cookies file di config (`YT_DLP_COOKIES=/data/cookies.txt`) buat workaround.
- **FFmpeg `-c copy` inaccuracy:** Klip mulai di keyframe terdekat, bisa meleset 1-3 detik. Buat preview oke; buat export final wajib re-encode (yang udah otomatis terjadi pas crop ke 9:16/1:1).
- **Twitch chat GQL:** Endpoint unofficial, bisa berubah sewaktu-waktu. Bungkus di adapter, easy to swap.
- **CORS:** Backend default `http://localhost:3000` allowed origin. Atur via env.

---

## 15. Pertanyaan untuk dikonfirmasi sebelum mulai

Claude Code, sebelum mulai sprint 1, konfirmasi ke user:
1. Whisper model preference (`base.en` sebagai default — okay buat akurasi vs speed tradeoff?).
2. Gemini API key — udah ada di Google AI Studio? Kalau belum, arahkan ke https://aistudio.google.com.
3. Apakah ada preferensi versi Postgres / Node / Python yang berbeda dari default di handoff ini?

Setelah konfirmasi, mulai dari Sprint 1 step 1. Commit per logical chunk, jangan satu commit besar di akhir.
