#!/bin/bash

echo "SIP Yönlendirme Kuralı Yapılandırılıyor..."

# --room-name-prefix yerine --room-prefix kullanıyoruz
# Ayrıca kuralın zaten var olması durumunda hata vermemesi için || true ekli
lk sip dispatch create \
  --url "http://livekit:7880" \
  --api-key "$LIVEKIT_API_KEY" \
  --api-secret "$LIVEKIT_API_SECRET" \
  --name "telnyx_rule" \
  --room-prefix "test_agent" || echo "Kural zaten mevcut veya bir hata oluştu, devam ediliyor..."

echo "SIP Yönlendirme Kuralı Kontrol Edildi."

# Gemini Agent'ı başlat
uv run python src/agent.py start
