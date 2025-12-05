#!/bin/bash
# AWS Support KB Slack Bot 실행 스크립트

# 환경 변수 로드
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# MCP 설정 경로
export Q_MCP_CONFIG_PATH="$(pwd)/mcp_config.json"

# 봇 실행
echo "🤖 AWS Support KB Bot 시작..."
echo "📚 Knowledge Base ID: $KB_ID"
echo "🔧 MCP Config: $Q_MCP_CONFIG_PATH"
echo ""

python3 bot.py
