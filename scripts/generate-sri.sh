#!/bin/bash
# scripts/generate-sri.sh

urls=(
    "https://cdn.jsdelivr.net/npm/alpinejs@3.14.3/dist/cdn.min.js"
    "https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"
)

for url in "${urls[@]}"; do
    echo "=== $url ==="
    hash=$(curl -sL "$url" | openssl dgst -sha384 -binary | openssl base64 -A)
    echo "integrity=\"sha384-$hash\""
    echo ""
done