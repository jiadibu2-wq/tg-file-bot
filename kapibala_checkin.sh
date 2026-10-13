#!/usr/bin/env bash
# 卡皮巴拉 API 站点每日签到脚本
# 用法: bash /workspace/kapibala_checkin.sh

set -uo pipefail

BASE_URL="https://api.kapibala.asia"
USERNAME="布加迪"
PASSWORD="givhyj-jostos-fyGmu1"
API_USER="6898"

echo "[1/2] 登录中..."
LOGIN_RESP=$(curl -s -X POST "${BASE_URL}/api/user/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"${USERNAME}\",\"password\":\"${PASSWORD}\"}")

ACCESS_TOKEN=$(printf '%s' "${LOGIN_RESP}" | grep -o '"access_token":"[^"]*"' | head -n1 | cut -d'"' -f4)

if [ -z "${ACCESS_TOKEN}" ]; then
  echo "登录失败，返回内容："
  echo "${LOGIN_RESP}"
  exit 1
fi
echo "     登录成功。"

echo "[2/2] 签到中..."
CHECKIN_RESP=$(curl -s -X POST "${BASE_URL}/api/user/checkin" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "New-Api-User: ${API_USER}")

echo "${CHECKIN_RESP}"

if printf '%s' "${CHECKIN_RESP}" | grep -q '"success":true'; then
  QUOTA=$(printf '%s' "${CHECKIN_RESP}" | grep -o '"quota_awarded":[0-9]*' | cut -d':' -f2)
  echo "签到成功，本次获得额度: ${QUOTA:-未知}"
  exit 0
elif printf '%s' "${CHECKIN_RESP}" | grep -q '今日已签到'; then
  echo "今日已签到，当天额度已领取。"
  exit 0
else
  echo "签到未成功，请查看上方返回内容。"
  exit 1
fi
