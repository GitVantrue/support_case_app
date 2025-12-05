#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AWS Support KB Bot - Q CLI + MCP 버전"""

import os
import subprocess
import re
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# .env 파일 로드
load_dotenv()

# 환경 변수
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
KB_ID = os.environ.get("KB_ID", "BECRJQ5RLE")

# Slack App 초기화
app = App(token=SLACK_BOT_TOKEN)

# 스레드 풀 생성 (최대 10개 동시 처리)
executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="slack-bot")

def clean_qcli_output(text: str) -> str:
    """Q CLI 응답에서 불필요한 로그 및 메타 정보 제거"""
    # ANSI 이스케이프 코드 제거
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    clean_text = ansi_escape.sub('', text)
    
    # 제거할 패턴들
    skip_patterns = [
        r'🛠️.*',
        r'●\s+.*',
        r'✓\s+.*',
        r'↳.*',
        r'⋮.*',
        r'Service name:.*',
        r'Operation name:.*',
        r'Parameters:.*',
        r'Region:.*',
        r'Label:.*',
        r'^>.*',
        r'.*검색해드리겠습니다.*',
        r'.*확인하겠습니다.*',
        r'.*조회.*시도.*',
        r'.*MCP 도구.*',
        r'.*Knowledge Base.*확인.*',
        r'I\'ll.*',
        r'Let me.*',
    ]
    
    lines = clean_text.split('\n')
    filtered_lines = []
    
    for line in lines:
        stripped = line.strip()
        
        if not stripped:
            filtered_lines.append('')
            continue
        
        skip_line = False
        for pattern in skip_patterns:
            if re.search(pattern, stripped, re.IGNORECASE):
                skip_line = True
                break
        
        if not skip_line:
            filtered_lines.append(stripped)
    
    result = '\n'.join(filtered_lines)
    result = re.sub(r'\n{3,}', '\n\n', result)
    
    return result.strip()

def format_response_blocks(query: str, response: str):
    """응답을 Slack Block Kit 형식으로 포맷팅 (3000자 제한 처리)"""
    header = f":mag: *AWS Support 케이스 검색 결과*\n\n*질문:* {query}\n\n"
    
    # Slack Block 텍스트 최대 길이 (3000자)
    MAX_BLOCK_LENGTH = 2900  # 여유 공간 확보
    
    # 헤더 + 응답이 제한을 초과하는 경우
    if len(header + response) > MAX_BLOCK_LENGTH:
        # 긴 응답은 여러 블록으로 분할
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": header
                }
            }
        ]
        
        # 응답을 청크로 분할
        remaining = response
        while remaining:
            chunk_size = MAX_BLOCK_LENGTH
            chunk = remaining[:chunk_size]
            
            # 마크다운이 깨지지 않도록 줄바꿈 위치에서 자르기
            if len(remaining) > chunk_size:
                last_newline = chunk.rfind('\n')
                if last_newline > chunk_size * 0.7:  # 70% 이상 위치에 줄바꿈이 있으면
                    chunk = chunk[:last_newline]
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": chunk
                }
            })
            
            remaining = remaining[len(chunk):].lstrip()
        
        return blocks
    else:
        # 짧은 응답은 하나의 블록으로
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": header + response
                }
            }
        ]

def query_with_qcli(user_message: str) -> str:
    """Q CLI를 사용하여 질문에 답변"""
    try:
        # 명확한 출력 형식 지정
        enhanced_prompt = f"""다음 질문에 대해 QueryKnowledgeBases 도구를 사용하여 Knowledge Base '{KB_ID}'에서 검색하고 답변하세요:

질문: {user_message}

답변 형식 (반드시 이 형식으로만 답변하고, 여러 케이스가 있으면 각각 이 형식으로 나열):

---

*📋 케이스 제목*
[케이스 제목]

*🆔 케이스 ID*
[케이스 ID]

*⚠️ 심각도*
[케이스 심각도 - urgent/high/normal/low]

*❓ 고객 질문*
[고객이 문의한 내용]

*✅ AWS 공식 답변*
[AWS Support 팀의 답변 내용]

*💡 해결 방법*
[문제 해결 방법 또는 권장 사항]

_📅 케이스 생성일: [YYYY-MM-DD]_

---

주의사항:
- 도구 사용 과정이나 메타 정보는 절대 포함하지 마세요
- 위 형식의 내용만 출력하세요
- 각 케이스는 --- 구분선으로 구분하세요"""

        # Q CLI 명령어 구성
        cmd = ['q', 'chat', '--no-interactive', '--trust-all-tools', enhanced_prompt]
        
        print(f"[Q CLI 실행] 질문: {user_message}")
        
        # Q CLI 실행
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            env=os.environ.copy()
        )
        
        print(f"[반환 코드] {result.returncode}")
        
        if result.returncode != 0:
            error_msg = result.stderr or "Unknown error"
            print(f"[에러] {error_msg}")
            return "죄송합니다. 답변을 생성할 수 없습니다."
        
        response = result.stdout.strip()
        
        if not response:
            return "응답을 받지 못했습니다."
        
        print(f"[응답 길이] {len(response)}")
        
        # 응답 정리
        cleaned = clean_qcli_output(response)
        return cleaned if cleaned else response
        
    except subprocess.TimeoutExpired:
        print("[타임아웃] 60초")
        return "응답 시간이 초과되었습니다."
    except Exception as e:
        print(f"[실행 실패] {str(e)}")
        import traceback
        traceback.print_exc()
        return "예상치 못한 오류가 발생했습니다."

@app.event("app_mention")
def handle_mention(event, say):
    """봇 멘션 이벤트 처리 (비동기)"""
    text = event.get("text", "")
    user = event.get("user")
    
    # 봇 멘션 제거
    query = text.split(">", 1)[-1].strip()
    
    if not query:
        say(text="안녕하세요! 👋 AWS Support 케이스에 대해 질문해주세요.")
        return
    
    print(f"[수신] {user}: {query}")
    
    # 비동기 처리 함수
    def process_async():
        try:
            print(f"[처리 시작] {user}: {query}")
            
            # Q CLI로 질문 처리
            response = query_with_qcli(query)
            
            # Slack Block Kit으로 포맷팅된 응답
            blocks = format_response_blocks(query, response)
            
            # Slack에 응답 (채널에 바로 답변)
            say(blocks=blocks, text=response)
            
            print(f"[완료] {user}")
            
        except Exception as e:
            print(f"[에러] {user}: {str(e)}")
            import traceback
            traceback.print_exc()
            say(text=f"<@{user}> 죄송합니다. 처리 중 오류가 발생했습니다.")
    
    # 스레드 풀에 작업 제출 (즉시 리턴하여 다음 요청 받을 수 있음)
    executor.submit(process_async)

@app.event("message")
def handle_message_events(body, logger):
    """일반 메시지 이벤트 처리 (무시)"""
    pass

if __name__ == "__main__":
    print("="*80)
    print("🤖 AWS Support KB Bot (Q CLI + MCP) 시작")
    print(f"📚 Knowledge Base ID: {KB_ID}")
    print("="*80)
    
    try:
        result = subprocess.run(['q', '--version'], capture_output=True, text=True)
        print(f"Q CLI: {result.stdout.strip()}")
    except FileNotFoundError:
        print("⚠️  Q CLI 미설치")
    
    print("="*80)
    
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
