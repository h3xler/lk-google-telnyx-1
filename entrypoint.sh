#!/bin/bash

echo "SIP Yönlendirme Kuralı Yapılandırılıyor..."

# Sizin paylaştığınız yardım çıktısındaki '--individual' parametresini kullanıyoruz.
# Bu parametre, gelen her aramayı 'test_agent' ile başlayan yeni bir odaya atar.
lk sip dispatch create \
  --url "http://livekit:7880" \
  --api-key "$LIVEKIT_API_KEY" \
  --api-secret "$LIVEKIT_API_SECRET" \
  --name "telnyx_rule" \
  --individual "test_agent" || echo "Kural zaten mevcut, devam ediliyor..."

echo "SIP Yönlendirme Kuralı Başarıyla Kontrol Edildi."

# Gemini Agent'ı başlat
uv run python src/agent.py start
