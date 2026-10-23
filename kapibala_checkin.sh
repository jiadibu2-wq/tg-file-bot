#!/usr/bin/env bash
# 卡皮巴拉 API 每日签到脚本
set -uo pipefail

BASE="https://api.kapibala.asia"
USERNAME="布加迪"
PASSWORD="givhyj-jostos-fyGmu1"
USER_ID="6898"

login_resp=$(curl -sS -m 30 -X POST "$BASE/api/user/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}")

token=$(printf '%s' "$login_resp" | python3 -c \
  'import sys,json;print(json.load(sys.stdin).get("data",{}).get("access_token",""))' 2>/dev/null)

if [ -z "$token" ]; then
  echo "LOGIN_FAILED: $login_resp"
  exit 1
fi

echo "LOGIN_OK"

checkin_resp=$(curl -sS -m 30 -X POST "$BASE/api/user/checkin" \
  -H "Authorization: Bearer $token" \
  -H "New-Api-User: $USER_ID" \
  -H "Content-Type: application/json" \
  -d '{}')

echo "CHECKIN_RESPONSE: $checkin_resp"
