#!/usr/bin/env bash
# 卡皮巴拉API (api.kapibala.asia) 自动签到脚本
set -euo pipefail

BASE="https://api.kapibala.asia"
USERNAME="布加迪"
PASSWORD="givhyj-jostos-fyGmu1"
USER_ID="6898"

# 1. 登录获取 access_token
LOGIN_RESP=$(curl -s -m 30 -X POST "$BASE/api/user/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}")

TOKEN=$(printf '%s' "$LOGIN_RESP" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')

if [ -z "$TOKEN" ]; then
  echo "登录失败: $LOGIN_RESP"
  exit 1
fi

# 2. 执行签到
CHECKIN_RESP=$(curl -s -m 30 -X POST "$BASE/api/user/checkin" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "New-Api-User: $USER_ID")

echo "签到结果: $CHECKIN_RESP"

# 3. 查询签到状态
STATUS_RESP=$(curl -s -m 30 "$BASE/api/user/checkin" \
  -H "Authorization: Bearer $TOKEN" \
  -H "New-Api-User: $USER_ID")
echo "签到状态: $STATUS_RESP"