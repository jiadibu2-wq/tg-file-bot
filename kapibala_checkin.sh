#!/usr/bin/env bash
# 卡皮巴拉 API 站点每日签到脚本
set -euo pipefail

BASE_URL="https://api.kapibala.asia"
USERNAME="布加迪"
PASSWORD="givhyj-jostos-fyGmu1"
NEW_API_USER="6898"

# 1. 登录获取 access_token
LOGIN_RESP=$(curl -s -X POST "${BASE_URL}/api/user/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"${USERNAME}\",\"password\":\"${PASSWORD}\"}")

echo "登录响应: ${LOGIN_RESP}"

ACCESS_TOKEN=$(echo "${LOGIN_RESP}" | grep -o '"access_token":"[^"]*"' | head -n1 | cut -d'"' -f4)

if [ -z "${ACCESS_TOKEN}" ]; then
  echo "错误: 登录失败，未能获取 access_token"
  exit 1
fi

echo "获取到 access_token"

# 2. 执行签到
CHECKIN_RESP=$(curl -s -X POST "${BASE_URL}/api/user/checkin" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "New-Api-User: ${NEW_API_USER}" \
  -H "Content-Type: application/json")

echo "签到响应: ${CHECKIN_RESP}"
