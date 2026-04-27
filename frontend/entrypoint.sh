#!/bin/sh
set -eu

: "${FRONTEND_API_BASE:=http://localhost:8000}"
: "${FRONTEND_INGEST_BASE:=http://localhost:8030}"

cat > /app/config.js <<EOF
window.APP_CONFIG = {
  apiBase: "${FRONTEND_API_BASE}",
  ingestBase: "${FRONTEND_INGEST_BASE}",
};
EOF

exec python -m http.server 8080 --bind 0.0.0.0
