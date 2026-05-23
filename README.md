# Video Clipper

Aplikasi web buat ekstrak klip menarik (hype moments, quotes bagus) dari video panjang (stream gaming, podcast). Single-user, deploy lokal via `docker-compose`.

> Spesifikasi lengkap ada di [`HANDOFF.md`](./HANDOFF.md). Dokumen ini cuma quickstart; README lengkap menyusul di Sprint 5.

## Stack

- **Frontend:** Next.js 15 (App Router, TS strict) · Tailwind v4 · shadcn/ui · TanStack Query · Zustand
- **Backend:** FastAPI (async) · SQLAlchemy 2.0 · Alembic · PostgreSQL 16 · Pydantic v2
- **Processing:** ffmpeg · yt-dlp · whisper.cpp (`base.en`)
- **LLM:** provider abstraction (default Gemini, swap-able ke Ollama/Claude/OpenAI)

## Prasyarat

- Docker + Docker Compose
- Model whisper.cpp (lihat di bawah — **tidak** auto-download)

## Quickstart

```bash
cp .env.example .env
# isi GEMINI_API_KEY (kalau pakai Gemini) dan sesuaikan setting lain

docker compose up --build
```

- Frontend: http://localhost:3000
- Backend (OpenAPI docs): http://localhost:8000/docs
- Postgres: `localhost:5432`

## Whisper model

Image backend mem-bundle binary `whisper-cli`, tapi **file model tidak ikut di-bundle** (ukurannya besar). Download manual ke `./models` (di-mount ke `/data/models`):

```bash
mkdir -p models
# base.en (~150MB) — default
curl -L -o models/ggml-base.en.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin
```

Ganti `WHISPER_MODEL` di `.env` kalau mau `small`/`medium` (lebih akurat, lebih lambat).

## Catatan

- **Job processing pakai FastAPI BackgroundTasks (in-process).** Kalau backend di-restart saat job jalan, job hilang. Fine untuk single-user dev; migrasi ke ARQ/Celery kalau butuh durability.
- `uploads/`, `outputs/`, `models/` adalah volume mount dan di-gitignore.
