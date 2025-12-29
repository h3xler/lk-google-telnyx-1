#!/bin/bash

# LiveKit Sunucusuna bağlanıp telefon yönlendirme kuralını oluşturur
# Parametre hatasını gidermek için --room-name-prefix kullanıyoruz
lk sip dispatch create \
  --url "http://livekit:7880" \
  --api-key "$LIVEKIT_API_KEY" \
  --api-secret "$LIVEKIT_API_SECRET" \
  --name "telnyx_rule" \
  --rule-type individual \
  --room-name-prefix "test_agent" || true

echo "SIP Yönlendirme Kuralı Kontrol Edildi."

# Gemini Agent'ı başlat
uv run python src/agent.py start
