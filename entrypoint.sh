#!/bin/bash

# LiveKit Sunucusuna SIP kuralını otomatik kaydet
# Hata alsa bile (zaten varsa) devam etmesi için || true ekledik
lk sip dispatch create \
  --url "http://livekit:7880" \
  --api-key "$LIVEKIT_API_KEY" \
  --api-secret "$LIVEKIT_API_SECRET" \
  --name "telnyx_rule" \
  --room-preset "test_agent" || true

echo "SIP Dispatch Rule checked/created."

# Agent'ı başlat
uv run python src/agent.py start
