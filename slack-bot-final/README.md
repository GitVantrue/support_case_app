# AWS Support KB Slack Bot

AWS Support 과거 케이스를 검색하여 Slack에서 답변하는 봇입니다.

## 주요 기능

- 🔍 AWS Support 과거 케이스 검색
- 💬 Slack에서 자연어로 질문
- 📋 구조화된 답변 제공 (케이스 제목, ID, 심각도, 질문, 답변, 해결 방법)
- 🤖 Amazon Q CLI + MCP를 활용한 고품질 검색

## 필수 요구사항

### 1. AWS 설정
- AWS Bedrock Knowledge Base (Support 케이스 데이터 포함)
- IAM 권한: Bedrock Knowledge Base 접근 권한

### 2. Slack App 설정
- Bot Token Scopes:
  - `app_mentions:read`
  - `chat:write`
  - `channels:history`
  - `groups:history`
  - `im:history`
- Socket Mode 활성화
- App-Level Token 생성

### 3. 소프트웨어
- Python 3.9+
- Amazon Q CLI
- uv (Python 패키지 관리자)

## 빠른 시작 (Quick Start)

### 자동 설치 및 실행

```bash
# 1. 저장소 클론
git clone <repository-url>
cd slack-bot-final

# 2. 자동 설치
chmod +x setup.sh
./setup.sh

# 3. 환경 변수 설정
vi .env
# SLACK_BOT_TOKEN, SLACK_APP_TOKEN, KB_ID 입력

# 4. 실행
chmod +x run.sh
./run.sh
```

자세한 내용은 [QUICKSTART.md](QUICKSTART.md)를 참조하세요.

## 수동 설치 방법

### 1. 의존성 설치

```bash
# Python 패키지 설치
pip3 install -r requirements.txt

# uv 설치 (MCP 서버용)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Amazon Q CLI 설치
# https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line-getting-started-installing.html
```

### 2. 환경 변수 설정

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집
vi .env
```

### 3. 환경 변수 로드 및 실행

```bash
# 환경 변수 로드
source .env
export Q_MCP_CONFIG_PATH=$(pwd)/mcp_config.json

# 봇 실행
python3 bot.py
```

또는 `run.sh` 스크립트 사용:

```bash
./run.sh
```

## 사용 방법

Slack에서 봇을 멘션하고 질문합니다:

```
@AWS Support KB Bot RDS 접속 오류
```

봇이 Knowledge Base에서 관련 케이스를 검색하여 답변합니다:

```
🔍 AWS Support 케이스 검색 결과

질문: RDS 접속 오류

---

📋 케이스 제목
RDS 데이터베이스 연결 타임아웃 문제

🆔 케이스 ID
case-12345678

⚠️ 심각도
high

❓ 고객 질문
RDS 인스턴스에 연결할 수 없습니다...

✅ AWS 공식 답변
보안 그룹 설정을 확인해주세요...

💡 해결 방법
1. 보안 그룹 인바운드 규칙 확인
2. ...

📅 케이스 생성일: 2024-01-15
```

## 배포 (EC2)

### 1. EC2 인스턴스 설정

```bash
# 필수 패키지 설치
sudo yum update -y
sudo yum install python3 python3-pip git -y

# 프로젝트 클론
git clone <repository-url>
cd slack-bot-final

# 의존성 설치
pip3 install -r requirements.txt
```

### 2. 백그라운드 실행

```bash
# nohup으로 실행
nohup python3 bot.py > bot.log 2>&1 &

# 또는 systemd 서비스로 등록
sudo cp aws-support-kb-bot.service /etc/systemd/system/
sudo systemctl enable aws-support-kb-bot
sudo systemctl start aws-support-kb-bot
```

## 문제 해결

### Q CLI가 MCP 도구를 인식하지 못함

```bash
# MCP 설정 확인
q chat --no-interactive "list available MCP tools"

# 환경 변수 확인
echo $Q_MCP_CONFIG_PATH
```

### Slack 토큰 오류

```bash
# 토큰 유효성 확인
curl -X POST https://slack.com/api/auth.test \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN"
```

## 라이선스

MIT License
