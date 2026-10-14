#!/usr/bin/env bash
# 卡皮巴拉 API 每日签到脚本
# 用法: bash /workspace/kapibala_checkin.sh
set -euo pipefail

BASE_URL="https://api.kapibala.asia"
USERNAME="布加迪"
PASSWORD="givhyj-jostos-fyGmu1"
NEW_API_USER="6898"

# 1. 登录获取 access_token
login_resp=$(curl -sS -X POST "$BASE_URL/api/user/login" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}")

access_token=$(printf '%s' "$login_resp" | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"]["access_token"])' 2>/dev/null || true)

if [ -z "$access_token" ]; then
  echo "登录失败，原始响应：$login_resp" >&2
  exit 1
fi

# 2. 携带 token 完成签到
curl -sS -X POST "$BASE_URL/api/user/checkin" \
  -H "Authorization: Bearer $access_token" \
  -H "New-Api-User: $NEW_API_USER" \
  -H 'Content-Type: application/json'
echo
