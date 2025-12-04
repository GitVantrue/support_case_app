# Implementation Plan

## Phase 1: AWS 리소스 생성 (사용자 수동)

- [ ] 1.1 S3 버킷 생성
  - support-bot-state 버킷 생성 (ap-northeast-2)
  - support-knowledge-base 버킷 생성 (ap-northeast-2)
  - 서버 측 암호화 (SSE-S3) 활성화
  - _Requirements: 3.5, 4.3_

- [ ] 1.2 EC2 인스턴스 생성
  - 인스턴스 타입: t3.small
  - 리전: ap-northeast-2
  - Public IP 할당
  - Security Group: SSH(22), HTTPS(443) 허용
  - _Requirements: 2.1, 6.1_

- [ ] 1.3 IAM 역할 생성
  - EC2용 역할: Support API, S3, Bedrock 권한
  - Lambda용 역할: Support API, S3, Bedrock, CloudWatch Logs 권한
  - 최소 권한 원칙 적용
  - _Requirements: 3.3, 7.1_

- [ ] 1.4 EventBridge Rule 생성
  - Rule 이름: SupportCaseUpdateRule
  - 리전: us-east-1
  - Event Pattern: Support Case Update, ResolveCase
  - _Requirements: 3.1, 3.2_

- [ ] 1.5 Lambda 함수 생성
  - 함수 이름: ProcessResolvedCase
  - 런타임: Python 3.12
  - 메모리: 512MB
  - 타임아웃: 120초
  - IAM 역할 연결
  - _Requirements: 3.2_

- [ ] 1.6 Bedrock Knowledge Base 생성
  - Knowledge Base 이름: support-case-kb
  - 리전: ap-northeast-2
  - 데이터 소스: S3 (support-knowledge-base)
  - 임베딩 모델: Amazon Titan Embeddings
  - _Requirements: 1.1, 2.1_

## Phase 2: Lambda 함수 구현

- [ ] 2.1 Lambda 기본 구조 작성
  - lambda_handler 함수 정의
  - EventBridge 이벤트 파싱
  - 환경 변수 설정 (KB_ID, DS_ID, BUCKET_NAME)
  - _Requirements: 3.2_

- [ ] 2.2 Support API 연동 구현
  - boto3 Support 클라이언트 생성
  - describe_cases 호출
  - describe_communications 호출
  - 에러 처리 및 로깅
  - _Requirements: 3.3_

- [ ] 2.3 Bedrock 요약 로직 구현
  - boto3 Bedrock Runtime 클라이언트 생성
  - Claude 3 Sonnet 모델 호출
  - 프롬프트 작성 (케이스 분석 및 요약)
  - JSON 파싱 및 검증
  - 재시도 로직 (최대 3회)
  - _Requirements: 3.4, 4.1, 4.2, 7.2_

- [ ] 2.4 S3 저장 로직 구현
  - S3 경로 생성 ({category}/{service}/{date}/{case-id}.json)
  - JSON 직렬화
  - S3 put_object 호출
  - 에러 처리
  - _Requirements: 3.5, 4.3, 4.4_

- [ ] 2.5 Bedrock KB 동기화 구현
  - boto3 Bedrock Agent 클라이언트 생성
  - start_ingestion_job 호출
  - 성공 로깅
  - _Requirements: 3.6, 3.7_

- [ ] 2.6 Lambda 배포 및 테스트
  - 코드 패키징 (dependencies 포함)
  - Lambda 함수 업데이트
  - EventBridge Rule과 연결
  - 테스트 이벤트로 실행 확인
  - CloudWatch Logs 확인
  - _Requirements: 3.2, 7.1_

## Phase 3: EC2 Slack Bot 구현

- [ ] 3.1 Slack App 생성 및 설정 (사용자 수동)
  - Slack App 생성 (api.slack.com)
  - Bot Token Scopes 설정 (app_mentions:read, chat:write)
  - Socket Mode 활성화
  - App-Level Token 생성
  - 워크스페이스에 설치
  - _Requirements: 6.1_

- [ ] 3.2 Slack Bot 서버 코드 작성
  - slack-bolt 프레임워크 사용
  - Socket Mode Handler 구현
  - app_mention 이벤트 핸들러
  - 환경 변수 설정 (SLACK_BOT_TOKEN, SLACK_APP_TOKEN)
  - _Requirements: 6.1, 6.2_

- [ ] 3.3 Q CLI 연동 로직 구현
  - subprocess로 Q CLI 실행
  - 사용자 메시지를 Q CLI에 전달
  - Q CLI 출력 캡처
  - 타임아웃 처리 (10초)
  - _Requirements: 2.1, 2.2, 6.4, 7.4_

- [ ] 3.4 Slack 응답 포맷팅 구현
  - Q CLI 출력을 Slack 메시지로 변환
  - 스레드 응답 처리
  - "검색 중..." 임시 메시지 표시
  - 에러 메시지 포맷팅
  - _Requirements: 1.3, 6.2, 6.3_

- [ ] 3.5 systemd 서비스 설정 작성
  - 서비스 파일 작성 (/etc/systemd/system/slack-bot.service)
  - 자동 시작 설정
  - 재시작 정책 설정
  - _Requirements: 6.1_

- [ ] 3.6 EC2 배포 스크립트 작성
  - 의존성 설치 스크립트
  - 환경 변수 설정 가이드
  - 서비스 시작 명령어
  - 로그 확인 방법
  - _Requirements: 6.1_

## Phase 4: EC2 환경 설정 (사용자 수동)

- [ ] 4.1 EC2 기본 설정
  - SSH 접속
  - Python 3.12 설치 확인
  - pip 업그레이드
  - 필요한 패키지 설치 (boto3, slack-bolt)
  - _Requirements: 2.1, 6.1_

- [ ] 4.2 Q CLI 설치
  - Q CLI 다운로드 및 설치
  - PATH 설정
  - 설치 확인 (q --version)
  - _Requirements: 2.1_

- [ ] 4.3 MCP 서버 설정
  - uv 설치 (Python 패키지 매니저)
  - mcp.json 파일 작성 (~/.aws/q/mcp.json)
  - Support Case MCP 설정
  - Bedrock KB Retrieval MCP 설정
  - MCP 연결 테스트
  - _Requirements: 2.1, 2.2_

- [ ] 4.4 Slack Bot 배포
  - 코드 업로드 (scp 또는 git clone)
  - 환경 변수 설정 (.env 파일)
  - systemd 서비스 등록
  - 서비스 시작 및 상태 확인
  - _Requirements: 6.1_

- [ ] 4.5 AWS Support App 설치
  - Slack 워크스페이스에 AWS Support App 추가
  - AWS 계정 연결
  - 채널에 앱 추가
  - 테스트 케이스 생성
  - _Requirements: 케이스 생성 기능_

## Phase 5: 과거 케이스 마이그레이션

- [ ] 5.1 마이그레이션 스크립트 작성
  - migrate_cases.py 파일 생성
  - Support API 케이스 목록 조회 로직
  - 페이지네이션 처리
  - _Requirements: 5.1, 5.2_

- [ ] 5.2 케이스 처리 로직 구현
  - 케이스별 처리 함수
  - S3 중복 확인 로직
  - Bedrock 요약 호출
  - S3 저장
  - _Requirements: 5.2, 5.3_

- [ ] 5.3 에러 처리 및 재시도 구현
  - Bedrock API 재시도 로직 (최대 3회)
  - Rate Limit 방지 (1초 대기)
  - 에러 로깅 (migration_errors.log)
  - 진행 상황 표시
  - _Requirements: 5.4, 5.5, 5.7_

- [ ] 5.4 마이그레이션 실행 (사용자 수동)
  - EC2에 스크립트 업로드
  - 백그라운드 실행 (nohup)
  - 진행 상황 모니터링 (tail -f)
  - 완료 확인 및 통계 확인
  - _Requirements: 5.1, 5.6_

- [ ] 5.5 Bedrock KB 인덱싱 확인
  - 인덱싱 작업 상태 확인
  - 검색 테스트
  - 결과 검증
  - _Requirements: 3.6, 3.7_

## Phase 6: 통합 테스트 및 검증

- [ ] 6.1 Lambda 자동 동기화 테스트
  - 테스트 케이스 생성 (AWS Support App)
  - 케이스 해결 처리
  - EventBridge 이벤트 확인
  - Lambda 실행 로그 확인
  - S3 저장 확인
  - Bedrock KB 인덱싱 확인
  - _Requirements: 3.1, 3.2, 3.5, 3.6_

- [ ] 6.2 Slack Bot 검색 테스트
  - Slack에서 KB Bot 멘션
  - 다양한 검색 쿼리 테스트
  - 응답 시간 측정
  - 검색 결과 정확도 확인
  - 에러 케이스 테스트
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2_

- [ ] 6.3 전체 플로우 테스트
  - 케이스 생성 → 해결 → 자동 저장 → 검색 전체 플로우
  - 여러 카테고리 케이스 테스트 (technical, billing)
  - 여러 서비스 케이스 테스트 (ec2, rds, lambda)
  - 동시 요청 처리 테스트
  - _Requirements: 전체_

- [ ] 6.4 성능 및 비용 모니터링
  - Lambda 실행 시간 및 비용 확인
  - Bedrock API 호출 횟수 및 비용 확인
  - S3 스토리지 사용량 확인
  - EC2 리소스 사용률 확인
  - _Requirements: 성능 및 비용_

- [ ] 6.5 문서화
  - README.md 작성 (프로젝트 개요, 설치 방법)
  - 운영 가이드 작성 (모니터링, 트러블슈팅)
  - 아키텍처 다이어그램 업데이트
  - 코드 주석 정리
  - _Requirements: 전체_

## Phase 7: 프로덕션 배포 준비 (선택)

- [ ] 7.1 보안 강화
  - EC2를 Private Subnet으로 이동
  - Application Load Balancer 추가
  - Security Group 규칙 최소화
  - Secrets Manager로 토큰 관리
  - _Requirements: 보안_

- [ ] 7.2 고가용성 설정
  - EC2 Auto Scaling Group 구성
  - Multi-AZ 배포
  - Health Check 설정
  - _Requirements: 가용성_

- [ ] 7.3 모니터링 및 알림
  - CloudWatch 대시보드 생성
  - Lambda 에러 알림 설정
  - Slack Bot 다운타임 알림
  - 비용 알림 설정
  - _Requirements: 7.1_
