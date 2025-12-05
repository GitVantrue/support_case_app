# 빠른 시작 가이드

## 1분 안에 시작하기

### 1. 저장소 클론

```bash
git clone <repository-url>
cd slack-bot-final
```

### 2. 자동 설치

```bash
chmod +x setup.sh
./setup.sh
```

### 3. 환경 변수 설정

```bash
vi .env
```

다음 값들을 입력:
- `SLACK_BOT_TOKEN`: Slack Bot User OAuth Token (xoxb-로 시작)
- `SLACK_APP_TOKEN`: Slack App-Level Token (xapp-로 시작)
- `KB_ID`: AWS Bedrock Knowledge Base ID

### 4. 실행

```bash
chmod +x run.sh
./run.sh
```

또는

```bash
# 환경 변수 로드
source .env
export Q_MCP_CONFIG_PATH=$(pwd)/mcp_config.json

# 봇 실행
python3 bot.py
```

## 백그라운드 실행

```bash
nohup ./run.sh > bot.log 2>&1 &
```

## 로그 확인

```bash
tail -f bot.log
```

## 중지

```bash
# 프로세스 ID 찾기
ps aux | grep bot.py

# 종료
kill <PID>
```

## 문제 해결

### 환경 변수가 로드되지 않음

```bash
# 수동으로 로드
source .env
export Q_MCP_CONFIG_PATH=$(pwd)/mcp_config.json

# 확인
echo $SLACK_BOT_TOKEN
echo $Q_MCP_CONFIG_PATH
```

### Q CLI가 MCP를 인식하지 못함

```bash
# MCP 도구 확인
q chat --no-interactive "list available MCP tools"

# 환경 변수 확인
env | grep Q_MCP
```

### Slack 연결 실패

```bash
# 토큰 테스트
curl -X POST https://slack.com/api/auth.test \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN"
```

## Systemd 서비스로 등록 (선택사항)

```bash
sudo tee /etc/systemd/system/aws-support-kb-bot.service > /dev/null <<EOF
[Unit]
Description=AWS Support KB Slack Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=$(pwd)/.env
ExecStart=/usr/bin/python3 $(pwd)/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 서비스 시작
sudo systemctl daemon-reload
sudo systemctl enable aws-support-kb-bot
sudo systemctl start aws-support-kb-bot

# 상태 확인
sudo systemctl status aws-support-kb-bot

# 로그 확인
sudo journalctl -u aws-support-kb-bot -f
```
