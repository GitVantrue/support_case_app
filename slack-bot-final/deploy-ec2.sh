#!/bin/bash
# EC2에 AWS Support KB Slack Bot 배포 스크립트

set -e

echo "=================================="
echo "EC2 배포 시작"
echo "=================================="

# 1. 현재 디렉터리 확인
INSTALL_DIR="/home/ec2-user/slack-bot-final"
echo ""
echo "1. 설치 디렉터리: $INSTALL_DIR"

# 2. 기존 서비스 중지 (있다면)
echo ""
echo "2. 기존 서비스 확인 및 중지..."
if sudo systemctl is-active --quiet aws-support-kb-bot; then
    echo "기존 서비스를 중지합니다..."
    sudo systemctl stop aws-support-kb-bot
fi

# 3. 의존성 설치
echo ""
echo "3. 의존성 설치..."
pip3 install -r requirements.txt --user

# 4. uv 설치 확인
echo ""
echo "4. uv 설치 확인..."
if ! command -v uvx &> /dev/null; then
    echo "uv 설치 중..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# 5. .env 파일 확인
echo ""
echo "5. 환경 변수 파일 확인..."
if [ ! -f .env ]; then
    echo "⚠️  .env 파일이 없습니다!"
    echo "   .env.example을 복사하여 .env를 생성하고 토큰을 입력하세요."
    cp .env.example .env
    echo ""
    echo "   다음 명령어로 편집: vi .env"
    echo ""
    read -p "계속하시겠습니까? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 6. Systemd 서비스 파일 업데이트
echo ""
echo "6. Systemd 서비스 설정..."

# 서비스 파일에 실제 경로 적용
sudo tee /etc/systemd/system/aws-support-kb-bot.service > /dev/null <<EOF
[Unit]
Description=AWS Support KB Slack Bot
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=$INSTALL_DIR
Environment="PATH=/usr/local/bin:/usr/bin:/bin:/home/ec2-user/.local/bin:/home/ec2-user/.cargo/bin"
Environment="Q_MCP_CONFIG_PATH=$INSTALL_DIR/mcp_config.json"
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=/usr/bin/python3 $INSTALL_DIR/bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 7. Systemd 리로드 및 서비스 활성화
echo ""
echo "7. 서비스 활성화..."
sudo systemctl daemon-reload
sudo systemctl enable aws-support-kb-bot

# 8. 서비스 시작
echo ""
echo "8. 서비스 시작..."
sudo systemctl start aws-support-kb-bot

# 9. 상태 확인
echo ""
echo "9. 서비스 상태 확인..."
sleep 2
sudo systemctl status aws-support-kb-bot --no-pager

# 10. 완료
echo ""
echo "=================================="
echo "✅ 배포 완료!"
echo "=================================="
echo ""
echo "유용한 명령어:"
echo "  서비스 상태:   sudo systemctl status aws-support-kb-bot"
echo "  로그 확인:     sudo journalctl -u aws-support-kb-bot -f"
echo "  서비스 재시작: sudo systemctl restart aws-support-kb-bot"
echo "  서비스 중지:   sudo systemctl stop aws-support-kb-bot"
echo ""
