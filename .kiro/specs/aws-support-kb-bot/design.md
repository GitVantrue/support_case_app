# Design Document

## Overview

AWS Support KB Bot은 Slack 기반의 지능형 Support 케이스 관리 시스템입니다. 사용자는 Slack에서 과거 케이스를 검색하고 AI 답변을 받으며, AWS Support App을 통해 새로운 케이스를 생성할 수 있습니다. 해결된 케이스는 EventBridge와 Lambda를 통해 자동으로 Bedrock Knowledge Base에 저장되어 향후 검색에 활용됩니다.

## Architecture

### System Architecture Diagram

```
┌─────────────────────────────────────────┐
│ Slack Workspace                          │
│                                          │
│ ┌────────────────────────────────────┐  │
│ │ AWS Support App (공식)              │  │
│ │ - 케이스 생성/조회                  │  │
│ │ - 실시간 알림                       │  │
│ └────────────────────────────────────┘  │
│                                          │
│ ┌────────────────────────────────────┐  │
│ │ KB Bot (커스텀)                     │  │
│ │ - KB 검색                           │  │
│ │ - AI 답변                           │  │
│ └────────────────────────────────────┘  │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ EC2 Instance (ap-northeast-2)            │
│                                          │
│ ┌────────────────────────────────────┐  │
│ │ Slack Bot Server                    │  │
│ │ - Socket Mode Handler               │  │
│ │ - Event Processing                  │  │
│ └────────────────────────────────────┘  │
│                                          │
│ ┌────────────────────────────────────┐  │
│ │ Q CLI + MCP Servers                 │  │
│ │ ├── Support Case MCP                │  │
│ │ └── Bedrock KB Retrieval MCP        │  │
│ └────────────────────────────────────┘  │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ AWS Support API                          │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ EventBridge                              │
│ Rule: Support Case Update                │
│ Pattern: ResolveCase                     │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Lambda: ProcessResolvedCase              │
│ ├── Support API 호출                     │
│ ├── Bedrock Claude 요약                  │
│ ├── S3 저장                              │
│ └── Bedrock KB 동기화                    │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ S3 Buckets                               │
│ ├── support-bot-state                    │
│ └── support-knowledge-base               │
│     ├── technical/                       │
│     │   ├── ec2/                         │
│     │   ├── rds/                         │
│     │   └── lambda/                      │
│     ├── billing/                         │
│     └── account/                         │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Amazon Bedrock Knowledge Base            │
│ - Vector Search                          │
│ - Automatic Indexing                     │
└─────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Slack Interface

#### AWS Support App (공식 앱)
- **역할**: 케이스 생성, 조회, 실시간 알림
- **인터페이스**: Slack 명령어 (`/awssupport create`, `/awssupport list`)
- **특징**: AWS에서 제공하는 공식 앱으로 별도 개발 불필요

#### KB Bot (커스텀 봇)
- **역할**: Knowledge Base 검색 및 AI 답변 제공
- **인터페이스**: Slack 멘션 (`@KB Bot [질문]`)
- **통신**: Socket Mode를 통한 실시간 이벤트 수신
- **응답 시간**: 평균 2-3초

### 2. EC2 Instance

#### Slack Bot Server
- **언어**: Python 3.12
- **프레임워크**: slack-bolt
- **역할**: Slack 이벤트 수신 및 Q CLI 실행
- **실행 방식**: systemd 서비스로 항상 실행

#### Q CLI + MCP Servers
- **Q CLI**: Amazon Q Command Line Interface
- **MCP 서버**:
  - Support Case MCP: AWS Support API 연동
  - Bedrock KB Retrieval MCP: Knowledge Base 검색
- **설정 파일**: `~/.aws/q/mcp.json`

### 3. Lambda Functions

#### ProcessResolvedCase
- **트리거**: EventBridge (ResolveCase 이벤트)
- **런타임**: Python 3.12
- **메모리**: 512MB
- **타임아웃**: 120초
- **역할**:
  1. Support API로 케이스 정보 수집
  2. Bedrock Claude로 요약 및 분류
  3. S3에 구조화된 JSON 저장
  4. Bedrock KB 인덱싱 트리거

### 4. EventBridge

#### Rule: SupportCaseUpdateRule
```json
{
  "source": ["aws.support"],
  "detail-type": ["Support Case Update"],
  "detail": {
    "event-name": ["ResolveCase"]
  }
}
```
- **리전**: us-east-1 (Support API 리전)
- **타겟**: Lambda (ProcessResolvedCase)

### 5. S3 Buckets

#### support-bot-state
- **용도**: 봇 상태 관리 (향후 확장용)
- **구조**: 단순 JSON 파일

#### support-knowledge-base
- **용도**: Knowledge Base 데이터 저장
- **구조**: 
  ```
  {category}/{service}/{YYYY-MM}/{case-id}.json
  ```
- **예시**:
  ```
  technical/ec2/2025-12/12345.json
  billing/2025-12/12346.json
  ```

### 6. Amazon Bedrock

#### Bedrock Runtime (Claude 3 Sonnet)
- **용도**: 케이스 요약 및 분류
- **모델**: anthropic.claude-3-sonnet-20240229-v1:0
- **입력**: 케이스 제목 + 대화 내역
- **출력**: 구조화된 JSON (category, service, question, solution, steps, tags)

#### Bedrock Knowledge Base
- **데이터 소스**: S3 (support-knowledge-base)
- **임베딩**: Amazon Titan Embeddings
- **검색 방식**: 벡터 유사도 검색
- **결과 수**: 최대 5개

## Data Models

### 케이스 JSON 구조 (S3 저장)

```json
{
  "case_id": "case-986719740728-muen-2022-c5a3adcdde2ee229",
  "display_id": "12345",
  "category": "technical",
  "service": "ec2",
  "severity": "high",
  "created_at": "2025-12-04T10:00:00Z",
  "resolved_at": "2025-12-04T15:30:00Z",
  "question": "EC2 인스턴스에 SSH로 연결할 수 없음",
  "solution": "보안 그룹 인바운드 규칙에 SSH 포트(22)를 추가하여 해결",
  "steps": [
    "1. EC2 콘솔에서 인스턴스의 보안 그룹 확인",
    "2. 보안 그룹의 인바운드 규칙 편집",
    "3. SSH(22) 포트 추가, 소스를 내 IP로 제한",
    "4. 변경 사항 저장 후 SSH 재시도"
  ],
  "tags": ["ec2", "ssh", "security-group", "connectivity"]
}
```

### EventBridge 이벤트 구조

```json
{
  "version": "0",
  "id": "93274b19-a740-0c83-d087-f96dc185f9d5",
  "region": "us-east-1",
  "time": "2025-12-04T18:43:48Z",
  "source": "aws.support",
  "detail-type": "Support Case Update",
  "detail": {
    "case-id": "case-986719740728-muen-2022-c5a3adcdde2ee229",
    "display-id": "12345",
    "communication-id": "",
    "event-name": "ResolveCase",
    "origin": ""
  }
}
```

### MCP 설정 파일 (mcp.json)

```json
{
  "mcpServers": {
    "aws-support": {
      "command": "uvx",
      "args": ["aws-support-mcp"],
      "env": {
        "AWS_REGION": "us-east-1"
      }
    },
    "bedrock-kb": {
      "command": "uvx",
      "args": ["bedrock-kb-retrieval-mcp"],
      "env": {
        "AWS_REGION": "ap-northeast-2",
        "KNOWLEDGE_BASE_ID": "kb-xxxxx"
      }
    }
  }
}
```

## Workflows

### Workflow 1: 사용자 검색

```
1. 사용자가 Slack에서 "@KB Bot RDS 연결 안됨" 입력
2. Slack Bot Server가 이벤트 수신
3. Q CLI 실행: q chat --message "RDS 연결 안됨"
4. Q CLI가 Bedrock KB MCP를 통해 Knowledge Base 검색
5. 유사 케이스 발견 및 AI 답변 생성
6. Slack Bot이 응답을 포맷팅하여 Slack에 전송
7. 사용자가 응답 확인
```

### Workflow 2: 케이스 해결 시 자동 동기화

```
1. AWS Support 팀이 케이스를 해결 상태로 변경
2. EventBridge가 ResolveCase 이벤트 감지
3. Lambda (ProcessResolvedCase) 트리거
4. Lambda가 Support API로 케이스 정보 수집
   - describe_cases(caseIdList=[case_id])
   - describe_communications(caseId=case_id)
5. Bedrock Claude로 요약 및 분류
   - 입력: 케이스 제목 + 대화 내역
   - 출력: category, service, question, solution, steps, tags
6. S3에 JSON 저장
   - 경로: {category}/{service}/{YYYY-MM}/{display-id}.json
7. Bedrock KB 인덱싱 트리거
   - start_ingestion_job(knowledgeBaseId, dataSourceId)
8. 인덱싱 완료 (백그라운드)
9. 다음 검색부터 해당 케이스 조회 가능
```

### Workflow 3: 과거 케이스 마이그레이션

```
1. 관리자가 EC2에서 migrate_cases.py 실행
2. Support API로 과거 해결된 케이스 목록 조회
   - afterTime: "2023-12-01T00:00:00Z"
   - includeResolvedCases: True
3. 각 케이스에 대해:
   a. S3에 이미 존재하는지 확인
   b. 존재하면 스킵
   c. 존재하지 않으면:
      - 케이스 정보 수집
      - Bedrock 요약
      - S3 저장
      - 1초 대기 (Rate Limit 방지)
4. 모든 케이스 처리 완료
5. Bedrock KB 인덱싱 트리거
6. 성공/실패 통계 출력
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: 케이스 저장 완전성
*For any* 해결된 Support 케이스, EventBridge가 ResolveCase 이벤트를 감지하면 해당 케이스는 반드시 S3 Knowledge Base에 저장되어야 한다.
**Validates: Requirements 3.2, 3.5**

### Property 2: 검색 결과 관련성
*For any* 사용자 검색 쿼리, Bedrock Knowledge Base가 반환하는 케이스들은 벡터 유사도 점수 기준으로 내림차순 정렬되어야 한다.
**Validates: Requirements 1.2**

### Property 3: 케이스 분류 정확성
*For any* 케이스, Bedrock Claude가 분류한 category는 technical, billing, account 중 하나여야 하며, service는 유효한 AWS 서비스명이어야 한다.
**Validates: Requirements 4.1, 4.2**

### Property 4: JSON 구조 일관성
*For any* S3에 저장되는 케이스 JSON, 필수 필드(case_id, display_id, category, service, question, solution, steps, tags)를 모두 포함해야 한다.
**Validates: Requirements 4.4**

### Property 5: 마이그레이션 중복 방지
*For any* 마이그레이션 실행, 이미 S3에 존재하는 케이스는 재처리되지 않아야 한다.
**Validates: Requirements 5.3**

### Property 6: 에러 재시도 제한
*For any* Bedrock API 호출 실패, 시스템은 최대 3회까지만 재시도해야 하며, 3회 실패 시 에러를 로그에 기록하고 중단해야 한다.
**Validates: Requirements 5.4, 7.2**

### Property 7: 응답 시간 제한
*For any* Slack 사용자 질문, KB Bot은 10초 이내에 응답을 반환하거나 타임아웃 메시지를 표시해야 한다.
**Validates: Requirements 2.5**

## Error Handling

### Lambda 에러 처리
- **Bedrock API 실패**: 지수 백오프로 최대 3회 재시도 (2초, 4초, 8초)
- **Support API 실패**: 즉시 실패 처리 및 CloudWatch Logs 기록
- **S3 저장 실패**: 즉시 실패 처리, Lambda 함수 실패 상태로 종료
- **타임아웃**: 120초 제한, 초과 시 자동 종료

### Slack Bot 에러 처리
- **Q CLI 실행 실패**: 사용자에게 "일시적 오류가 발생했습니다" 메시지 표시
- **타임아웃**: 10초 초과 시 "처리 시간이 초과되었습니다" 메시지 표시
- **MCP 연결 실패**: 에러 로그 기록 및 재시작 안내

### 마이그레이션 에러 처리
- **케이스별 에러**: 해당 케이스만 스킵하고 다음 케이스 계속 처리
- **에러 로깅**: migration_errors.log 파일에 케이스 ID와 에러 메시지 기록
- **Rate Limit**: 각 케이스 처리 후 1초 대기

## Testing Strategy

### Unit Tests
- Lambda 함수의 각 기능 (케이스 수집, 요약, S3 저장) 개별 테스트
- Slack Bot의 이벤트 처리 로직 테스트
- 에러 처리 로직 테스트

### Integration Tests
- EventBridge → Lambda → S3 → Bedrock KB 전체 플로우 테스트
- Slack → EC2 → Q CLI → Bedrock KB 검색 플로우 테스트
- 마이그레이션 스크립트 소규모 데이터 테스트

### Manual Tests
- AWS Support App을 통한 케이스 생성 및 해결
- Slack에서 실제 검색 및 AI 답변 확인
- 과거 케이스 마이그레이션 실행 및 결과 확인

## Security Considerations

### IAM 역할 및 권한
- **EC2 역할**: Support API, S3, Bedrock 읽기/쓰기 권한
- **Lambda 역할**: Support API, S3, Bedrock, CloudWatch Logs 권한
- **최소 권한 원칙**: 필요한 권한만 부여

### 데이터 보안
- **S3 암호화**: 서버 측 암호화 (SSE-S3) 활성화
- **전송 중 암호화**: HTTPS/TLS 사용
- **Slack 토큰**: 환경 변수로 관리, 코드에 하드코딩 금지

### 네트워크 보안
- **EC2 Security Group**: SSH(22), HTTPS(443)만 허용
- **Private Subnet 고려**: 프로덕션 환경에서는 Private Subnet + NAT Gateway 권장

## Performance Considerations

### Lambda 최적화
- **메모리**: 512MB (Bedrock API 호출 고려)
- **타임아웃**: 120초 (케이스 처리 시간 고려)
- **동시 실행**: 제한 없음 (케이스 해결 빈도 낮음)

### Bedrock KB 최적화
- **검색 결과 수**: 최대 5개로 제한
- **인덱싱 빈도**: 케이스 저장 시마다 트리거 (자동 배치 처리)

### Slack Bot 최적화
- **응답 시간**: Q CLI 실행 시간 2-3초 목표
- **동시 요청**: Socket Mode로 순차 처리

## Cost Estimation

### 월간 예상 비용 (케이스 월 50건 기준)

- **EC2 (t3.small)**: ~$15/월
- **Lambda 실행**: ~$0 (프리티어 내)
- **S3 스토리지**: ~$0.05/월
- **Bedrock Claude**: ~$2/월 (50건 × $0.04)
- **Bedrock KB**: ~$1/월
- **EventBridge**: $0 (무료)

**총 예상 비용**: ~$18-20/월
