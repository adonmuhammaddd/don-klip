# ─── Stage 1: build whisper.cpp (statically linked → single binary) ──────────
FROM debian:bookworm-slim AS whisper-builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        git cmake build-essential ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt
RUN git clone --depth 1 https://github.com/ggml-org/whisper.cpp.git
WORKDIR /opt/whisper.cpp
# -Wno-stringop-overflow: false-positive GCC 12 di ggml-cpu/repack.cpp yang nge-fatal build.
# GGML_NATIVE=OFF: jangan -march=native (biar binary portabel). -j4: hindari OOM saat compile.
RUN cmake -B build \
        -DCMAKE_BUILD_TYPE=Release \
        -DBUILD_SHARED_LIBS=OFF \
        -DGGML_NATIVE=OFF \
        -DGGML_FATAL_WARNINGS=OFF \
        -DCMAKE_C_FLAGS="-Wno-stringop-overflow -Wno-array-bounds" \
        -DCMAKE_CXX_FLAGS="-Wno-stringop-overflow -Wno-array-bounds" \
    && cmake --build build --config Release -j4 --target whisper-cli

# ─── Stage 2: runtime ────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# ffmpeg buat cut/encode/crop; yt-dlp di-install via pip (lihat pyproject sprint 2).
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=whisper-builder /opt/whisper.cpp/build/bin/whisper-cli /usr/local/bin/whisper-cli

WORKDIR /app

# Install dependencies dari pyproject (single source of truth).
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir ".[dev]"

EXPOSE 8000

# Default command; di docker-compose dev di-override dengan --reload.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
