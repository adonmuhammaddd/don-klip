# Video Clipper

Aplikasi web buat ekstrak klip menarik (hype moments, quotes bagus) dari video panjang (stream gaming, podcast). Single-user, deploy lokal via `docker compose`.

Alur: **upload / URL → download → transcribe → deteksi momen (4 strategi) → review & trim → export 9:16 + 1:1 + SRT**.

> Spesifikasi desain lengkap ada di [`HANDOFF.md`](./HANDOFF.md).

## Stack

- **Frontend:** Next.js 15 (App Router, TS strict) · Tailwind v4 · shadcn/ui · TanStack Query · Zustand
- **Backend:** FastAPI (async) · SQLAlchemy 2.0 · Alembic · PostgreSQL 16 · Pydantic v2
- **Processing:** ffmpeg · yt-dlp · whisper.cpp (`base.en`)
- **LLM:** provider abstraction — Gemini (default), Ollama, Claude, OpenAI

## Arsitektur

```
frontend (Next.js :3000) ──HTTP──> backend (FastAPI :8000) ──> PostgreSQL :5432
                                          │
                                          └── pipeline (BackgroundTasks):
                                              source → ffprobe → extract audio →
                                              whisper.cpp → detektor → aggregator →
                                              simpan clip_candidates
```

Pipeline jalan in-process via FastAPI `BackgroundTasks` (lihat [Catatan](#catatan--limitasi)).

## Prasyarat

- Docker + Docker Compose
- Model whisper.cpp (**tidak** auto-download — lihat [Whisper model](#whisper-model))
- Opsional: API key LLM (Gemini/Claude/OpenAI) atau Ollama lokal untuk strategi `llm_transcript`

## Quickstart

```bash
# 1. Konfigurasi
cp .env.example .env
#    Edit .env: isi GEMINI_API_KEY (kalau pakai Gemini), sesuaikan setting lain.

# 2. Download model whisper (~150MB untuk base.en)
mkdir -p models
curl -L -o models/ggml-base.en.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin

# 3. Build + jalankan (build backend pertama kali meng-compile whisper.cpp, beberapa menit)
docker compose up --build

# 4. Migrasi DB (terminal lain, sekali di awal / setelah ganti schema)
docker compose exec backend alembic upgrade head
```

- Frontend: <http://localhost:3000>
- Backend (OpenAPI docs): <http://localhost:8000/docs>
- Postgres: `localhost:5432`

Buka <http://localhost:3000/new>, upload video / paste URL, pilih strategi deteksi, lalu tunggu status `ready_for_review` untuk review + trim + export.

## Whisper model

Image backend mem-bundle binary `whisper-cli`, tapi **file model tidak ikut di-bundle**. Download manual ke `./models` (di-mount ke `/data/models`). Nama file mengikuti pola `ggml-<model>.bin`:

| `WHISPER_MODEL` | File | Ukuran | Catatan |
|---|---|---|---|
| `base.en` (default) | `ggml-base.en.bin` | ~150MB | English, cepat |
| `small` | `ggml-small.bin` | ~500MB | multilingual, lebih akurat |
| `medium` | `ggml-medium.bin` | ~1.5GB | paling akurat, berat di CPU |

## Strategi deteksi

Dipilih per-job di form create (`detection_config.strategies`):

| Strategi | Cara kerja |
|---|---|
| `audio_spike` | Lonjakan energi audio (RMS) per window 0.5s, threshold `mean + Nσ`. |
| `llm_transcript` | Transcript di-chunk ~2 menit, LLM cari quote/punchline/momen menarik. |
| `twitch_chat` | Kepadatan chat replay Twitch (msgs/5s), bonus emote — hanya untuk VOD Twitch. |
| `manual` | Marker timestamp manual (`HH:MM:SS, komentar`) → klip 30 detik. |

Aggregator menggabungkan kandidat lintas-strategi yang overlap >50% (score weighted-sum), sort, dan cap `MAX_CANDIDATES_PER_JOB`. Kalau satu detektor gagal (mis. kuota LLM habis), detektor lain tetap jalan.

## Konfigurasi LLM provider

`.env`: `LLM_PROVIDER` ∈ `gemini` | `ollama` | `claude` | `openai`.

| Provider | Variabel | Default model |
|---|---|---|
| `gemini` | `GEMINI_API_KEY`, `GEMINI_MODEL` | `gemini-2.0-flash` |
| `ollama` | `OLLAMA_URL`, `OLLAMA_MODEL` | `llama3.1:8b` (lokal, tanpa API key) |
| `claude` | `ANTHROPIC_API_KEY` | `claude-haiku-4-5` |
| `openai` | `OPENAI_API_KEY` | `gpt-4o-mini` |

## Referensi environment

Lihat [`.env.example`](./.env.example) untuk daftar lengkap. Yang penting:

| Var | Default | Keterangan |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://app:app@postgres:5432/clipper` | Koneksi DB async |
| `WHISPER_MODEL` / `WHISPER_BIN` | `base.en` / `/usr/local/bin/whisper-cli` | Model + binary whisper.cpp |
| `LLM_PROVIDER` | `gemini` | Provider LLM aktif |
| `AUDIO_SPIKE_STD_MULTIPLIER` | `2.0` | Sensitivitas audio spike (makin kecil makin sensitif) |
| `MAX_CANDIDATES_PER_JOB` | `50` | Cap jumlah kandidat klip |
| `MAX_UPLOAD_MB` | `4096` | Limit ukuran upload |
| `TWITCH_CLIENT_ID` | (public web id) | Untuk fetch chat replay Twitch GQL |
| `CORS_ORIGINS` | `http://localhost:3000` | Origin yang diizinkan |

## API surface (ringkas)

| Method | Path | Fungsi |
|---|---|---|
| `POST` | `/api/jobs` | Buat job (multipart upload / JSON url) |
| `GET` | `/api/jobs` | List job (paginated) |
| `GET` | `/api/jobs/{id}` | Detail + progress |
| `DELETE` | `/api/jobs/{id}` | Hapus job + file |
| `POST` | `/api/jobs/{id}/cancel` | Batalkan job yang sedang berjalan |
| `POST` | `/api/jobs/{id}/retry` | Ulang job failed/cancelled |
| `GET` | `/api/jobs/{id}/clips` | List kandidat klip |
| `GET` | `/api/jobs/{id}/transcript` | Transcript |
| `PATCH` | `/api/clips/{id}` | Trim / approve / reject |
| `GET` | `/api/clips/{id}/preview` | Stream source video (Range) |
| `POST` | `/api/clips/{id}/export` | Export 9:16 + 1:1 + SRT |
| `GET` | `/api/files/{path}` | Download hasil export |

## Development

Cek kualitas (di dalam container backend, atau venv lokal Python 3.11+):

```bash
cd backend
pip install -e ".[dev]"
mypy app          # strict, no any
ruff check app    # lint
pytest -q         # unit + integration (butuh DATABASE_URL/ffmpeg/key untuk yang ditandai)
```

Frontend:

```bash
cd frontend
npm install
npm run typecheck   # tsc --noEmit (strict)
npm run build
```

Migrasi baru setelah ubah model:

```bash
docker compose exec backend alembic revision --autogenerate -m "deskripsi"
docker compose exec backend alembic upgrade head
```

## Catatan & limitasi

- **Job processing in-process (FastAPI BackgroundTasks).** Kalau backend di-restart saat job jalan, job hilang. Cukup untuk single-user dev; migrasi ke ARQ/Celery kalau butuh durability.
- **Twitch chat** pakai endpoint GQL unofficial (persisted query) — bisa berubah sewaktu-waktu; di-wrap adapter (`services/chat/twitch.py`) supaya gampang diganti.
- **Cancel** tidak menghentikan subprocess yang sedang jalan secara paksa — job berhenti di batas stage berikutnya.
- `uploads/`, `outputs/`, `models/` adalah volume mount dan di-gitignore.
