#!/bin/bash

echo "SIP Yönlendirme Kuralı Yapılandırılıyor..."

# --individual parametresinden "test_agent" değerini kaldırdık.
# Artık gelen aramalar doğrudan odaya düşecek ve isimsiz asistanımız onu yakalayacak.
lk sip dispatch create \
  --url "http://livekit:7880" \
  --api-key "$LIVEKIT_API_KEY" \
  --api-secret "$LIVEKIT_API_SECRET" \
  --name "telnyx_rule" \
  --individual "" || echo "Kural zaten mevcut, devam ediliyor..."

echo "SIP Yönlendirme Kuralı Başarıyla Kontrol Edildi."

uv run python src/agent.py start
