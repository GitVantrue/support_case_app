#!/bin/bash
# AWS Support KB Slack Bot 설치 스크립트

set -e

echo "=================================="
echo "AWS Support KB Slack Bot 설치"
echo "=================================="

# 1. Python 버전 확인
echo ""
echo "1. Python 버전 확인..."
python3 --version || { echo "Python 3.9+ 필요"; exit 1; }

# 2. pip 업그레이드
echo ""
echo "2. pip 업그레이드..."
python3 -m pip install --upgrade pip

# 3. 의존성 설치
echo ""
echo "3. Python 패키지 설치..."
pip3 install -r requirements.txt

# 4. uv 설치 확인
echo ""
echo "4. uv (Python 패키지 관리자) 확인..."
if ! command -v uvx &> /dev/null; then
    echo "uv가 설치되지 않았습니다. 설치 중..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi
uvx --version

# 5. Amazon Q CLI 확인
echo ""
echo "5. Amazon Q CLI 확인..."
if ! command -v q &> /dev/null; then
    echo "⚠️  Amazon Q CLI가 설치되지 않았습니다."
    echo "설치 방법: https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line-getting-started-installing.html"
    echo ""
    read -p "계속하시겠습니까? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    q --version
fi

# 6. .env 파일 생성
echo ""
echo "6. 환경 변수 설정..."
if [ ! -f .env ]; then
    echo ".env 파일이 없습니다. .env.example에서 복사합니다."
    cp .env.example .env
    echo ""
    echo "⚠️  중요: .env 파일을 편집하여 실제 토큰을 입력하세요!"
    echo "   vi .env"
    echo ""
else
    echo ".env 파일이 이미 존재합니다."
fi

# 7. MCP 설정 확인
echo ""
echo "7. MCP 설정 확인..."
if [ -f mcp_config.json ]; then
    echo "mcp_config.json 파일 확인됨"
    cat mcp_config.json
else
    echo "⚠️  mcp_config.json 파일이 없습니다!"
    exit 1
fi

# 8. 환경 변수 영구 설정 (선택사항)
echo ""
echo "8. 환경 변수 영구 설정 (선택사항)..."
read -p "환경 변수를 ~/.bashrc에 추가하시겠습니까? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    CURRENT_DIR=$(pwd)
    
    # .bashrc에 추가
    if ! grep -q "AWS Support KB Bot" ~/.bashrc; then
        cat >> ~/.bashrc << EOF

# AWS Support KB Bot 환경 변수
export Q_MCP_CONFIG_PATH="$CURRENT_DIR/mcp_config.json"
source "$CURRENT_DIR/.env"
EOF
        echo "~/.bashrc에 환경 변수가 추가되었습니다."
        echo "다음 명령어로 적용하세요: source ~/.bashrc"
    else
        echo "이미 ~/.bashrc에 설정되어 있습니다."
    fi
fi

# 9. 완료
echo ""
echo "=================================="
echo "✅ 설치 완료!"
echo "=================================="
echo ""
echo "다음 단계:"
echo "1. .env 파일 편집: vi .env"
echo "2. Slack 토큰 입력 (SLACK_BOT_TOKEN, SLACK_APP_TOKEN)"
echo "3. 환경 변수 로드: source ~/.bashrc (또는 새 터미널)"
echo "4. 봇 실행: python3 bot.py"
echo ""
