FROM python:3.11-slim

# Sistem bağımlılıkları
RUN apt-get update && apt-get install -y curl build-essential jq tar gzip && rm -rf /var/lib/apt/lists/*

# uv paket yöneticisini kur
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# LiveKit CLI kur (Agent başlangıçta SIP kuralı oluşturabilsin diye)
RUN curl -sSL https://get.livekit.io/cli | bash

WORKDIR /app
COPY . .

# Bağımlılıkları kur ve model dosyalarını indir
RUN uv sync
RUN uv run python src/agent.py download-files

# Başlangıç betiğine yetki ver
RUN chmod +x entrypoint.sh

# Başlangıç betiğini çalıştır
ENTRYPOINT ["./entrypoint.sh"]
