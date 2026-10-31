#!/usr/bin/env bash
# github-speedup.sh —— 免费 GitHub 加速工具（电脑 + 手机通用）
#
# 用法：
#   bash github-speedup.sh          自动测速并启用加速
#   bash github-speedup.sh status   查看当前加速配置
#   bash github-speedup.sh off      取消加速，恢复直连
#
# 原理：给 git 的 https://github.com/ 地址自动加一个免费镜像前缀，
#       只影响 clone / fetch / pull，不影响 SSH 方式推送。
# 注意：请勿用它访问私有仓库（镜像站点无法认证），私有仓库请用 SSH。

set -uo pipefail

MIRRORS=(
  "https://gh-proxy.com/https://github.com/"
  "https://ghfast.top/https://github.com/"
  "https://ghproxy.net/https://github.com/"
  "https://hub.gitmirror.com/https://github.com/"
  "https://ghproxy.cc/https://github.com/"
)

TEST_PATH="octocat/Hello-World.git/info/refs?service=git-upload-pack"

for cmd in git curl awk; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "缺少 $cmd，请先安装（Termux: pkg install git curl）"; exit 1; }
done

probe() {
  local prefix="$1" out code time
  out=$(curl -s -o /dev/null -m 8 -w '%{http_code} %{time_total}' "${prefix}${TEST_PATH}" 2>/dev/null) || return 1
  code=${out%% *}
  time=${out##* }
  [[ "$code" == "200" ]] || return 1
  printf '%s' "$time"
}

pick_fastest() {
  local best="" best_time=999 mirror t
  for mirror in "${MIRRORS[@]}"; do
    printf '  测试 %-52s' "$mirror" >&2
    if t=$(probe "$mirror"); then
      printf '%0.2fs\n' "$t" >&2
      if awk "BEGIN{exit !($t < $best_time)}"; then
        best_time=$t
        best=$mirror
      fi
    else
      printf '不可用\n' >&2
    fi
  done
  printf '%s' "$best"
}

enable() {
  local prefix="$1" m
  for m in "${MIRRORS[@]}"; do
    git config --global --unset-all "url.${m}.insteadOf" >/dev/null 2>&1
  done
  git config --global "url.${prefix}.insteadOf" "https://github.com/"
  echo "已启用加速：${prefix}"
  echo "之后 git clone / pull 会自动走该镜像；如需推送私有仓库请用 SSH 地址。"
  echo "取消加速：bash github-speedup.sh off"
}

case "${1:-on}" in
  on)
    echo "正在测试免费镜像节点..."
    fastest=$(pick_fastest)
    if [[ -z "$fastest" ]]; then
      echo "所有镜像当前都不可用，已保持直连。稍后重试或手动更换镜像列表。"
      exit 1
    fi
    enable "$fastest"
    ;;
  status)
    if git config --global --get-regexp '^url\..*\.insteadof' 2>/dev/null; then
      :
    else
      echo "当前未启用镜像加速（直连 GitHub）。"
    fi
    ;;
  off)
    for m in "${MIRRORS[@]}"; do
      git config --global --unset-all "url.${m}.insteadOf" >/dev/null 2>&1
    done
    echo "已取消加速，恢复直连 GitHub。"
    ;;
  *)
    echo "用法：bash $0 [on|status|off]"
    exit 1
    ;;
esac
