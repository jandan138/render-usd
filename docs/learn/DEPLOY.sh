#!/usr/bin/env bash
# Render-USD Learning Guide — 全自动部署脚本
# 用法: export GH_TOKEN=ghp_xxxxxxxxxxxx; bash DEPLOY.sh

set -euo pipefail

REPO="jandan138/render-usd"
BRANCH="main"
TOKEN="${GH_TOKEN:-${GITHUB_TOKEN:-}}"

if [ -z "$TOKEN" ]; then
    echo "❌ 错误: 未设置 GH_TOKEN 或 GITHUB_TOKEN"
    echo ""
    echo "请按以下步骤获取 Token："
    echo "1. 打开 https://github.com/settings/tokens/new"
    echo "2. Token name: render-usd-deploy"
    echo "3. 勾选 'repo' (Full control of private repositories)"
    echo "4. 点击 Generate token"
    echo "5. 复制 token 并执行: export GH_TOKEN=ghp_xxxxxxxxxxxxx"
    echo "6. 重新运行本脚本"
    exit 1
fi

echo "🚀 开始部署 Render-USD Learning Guide..."

# 1. 配置带 Token 的 remote
ORIGIN_URL="https://${TOKEN}@github.com/${REPO}.git"
git remote set-url origin "$ORIGIN_URL"

# 2. Push
echo "📤 推送代码到 origin/main..."
if git push origin main; then
    echo "✅ 推送成功"
else
    echo "❌ 推送失败，请检查 token 权限"
    exit 1
fi

# 3. 通过 GitHub API 启用 Pages (从 docs 文件夹)
echo "⚙️  配置 GitHub Pages (Source: main /docs)..."
API_URL="https://api.github.com/repos/${REPO}/pages"
HTTP_CODE=$(curl -s -o /tmp/gh_pages_resp.json -w "%{http_code}" \
    -H "Authorization: token ${TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    "${API_URL}" 2>/dev/null || echo "000")

if [ "$HTTP_CODE" = "404" ] || [ "$HTTP_CODE" = "400" ]; then
    # Pages 未启用，先创建
    curl -s -o /tmp/gh_pages_post.json -w "%{http_code}" \
        -X POST \
        -H "Authorization: token ${TOKEN}" \
        -H "Accept: application/vnd.github+json" \
        -H "Content-Type: application/json" \
        -d '{"source":{"branch":"main","path":"/docs"}}' \
        "https://api.github.com/repos/${REPO}/pages" > /tmp/gh_pages_post.code
    POST_CODE=$(cat /tmp/gh_pages_post.code)
    if [ "$POST_CODE" = "201" ] || [ "$POST_CODE" = "204" ]; then
        echo "✅ GitHub Pages 已启用 (source: main /docs)"
    else
        echo "⚠️  Pages API 返回 ${POST_CODE}，可能已在设置中手动启用过"
        cat /tmp/gh_pages_post.json 2>/dev/null || true
    fi
else
    echo "ℹ️  Pages 似乎已配置 (HTTP ${HTTP_CODE})"
fi

# 4. 等待并验证
echo ""
echo "⏳ 等待 GitHub Pages 部署生效 (约 30-60 秒)..."
sleep 5

SITE_URL="https://${REPO%/*}.github.io/${REPO#*/}/learn/"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 部署完成！"
echo ""
echo "📖 教程首页: ${SITE_URL}"
echo ""
echo "如果页面 404，请确认："
echo "   1. 仓库 Settings → Pages → Source 是否已设为 'main /docs'"
echo "   2. 等待 1-2 分钟后刷新"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 恢复 remote（移除 token 避免留在 .git/config）
git remote set-url origin "https://github.com/${REPO}.git"
