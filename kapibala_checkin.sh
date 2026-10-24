#!/usr/bin/env bash
# 卡皮巴拉 API 站点每日签到脚本
set -uo pipefail

BASE_URL="https://api.kapibala.asia"
USERNAME="布加迪"
PASSWORD="givhyj-jostos-fyGmu1"
NEW_API_USER="6898"

LOGIN_RESP="$(curl -sS -m 30 -X POST "$BASE_URL/api/user/login" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}")" || {
  echo "LOGIN_REQUEST_FAILED"
  exit 2
}

TOKEN="$(printf '%s' "$LOGIN_RESP" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    print(""); sys.exit(0)
print((d.get("data") or {}).get("access_token", ""))
')"

if [ -z "$TOKEN" ]; then
  echo "LOGIN_FAILED: $LOGIN_RESP"
  exit 3
fi

CHECKIN_RESP="$(curl -sS -m 30 -X POST "$BASE_URL/api/user/checkin" \
  -H "Authorization: Bearer $TOKEN" \
  -H "New-Api-User: $NEW_API_USER" \
  -H 'Content-Type: application/json')" || {
  echo "CHECKIN_REQUEST_FAILED"
  exit 4
}

echo "$CHECKIN_RESP"
