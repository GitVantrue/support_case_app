# Requirements Document

## Introduction

AWS Support 케이스 관리 및 지식 기반 시스템은 Slack을 통해 사용자가 과거 Support 케이스를 검색하고, AI 기반 답변을 받으며, 새로운 케이스를 생성할 수 있는 통합 솔루션입니다. 해결된 케이스는 자동으로 Knowledge Base에 저장되어 향후 유사한 문제 해결에 활용됩니다.

## Glossary

- **KB Bot**: Slack에서 동작하는 커스텀 AI 챗봇으로 Knowledge Base 검색 및 AI 답변을 제공하는 시스템
- **Knowledge Base (KB)**: Amazon Bedrock Knowledge Base를 사용하여 과거 Support 케이스를 저장하고 검색하는 벡터 데이터베이스
- **Support Case**: AWS Support에 생성된 기술 지원 요청 케이스
- **Q CLI**: Amazon Q Command Line Interface로 MCP 서버와 통합하여 AI 기능을 제공하는 도구
- **MCP (Model Context Protocol)**: AI 에이전트가 외부 도구 및 데이터 소스와 통신하기 위한 프로토콜
- **Support MCP**: AWS Support API와 통신하여 케이스 관리 기능을 제공하는 MCP 서버
- **Bedrock KB MCP**: Amazon Bedrock Knowledge Base와 통신하여 검색 기능을 제공하는 MCP 서버
- **EventBridge**: AWS 서비스 이벤트를 감지하고 Lambda 함수를 트리거하는 이벤트 버스
- **케이스 요약**: Bedrock Claude를 사용하여 케이스 내용을 핵심 질문과 해결 방법으로 정리한 구조화된 데이터

## Requirements

### Requirement 1: Knowledge Base 검색

**User Story:** 사용자로서, 문제 발생 시 과거 해결된 유사 케이스를 빠르게 검색하여 해결 방법을 찾고 싶다.

#### Acceptance Criteria

1. WHEN 사용자가 Slack에서 KB Bot을 멘션하고 질문을 입력하면, THE KB Bot SHALL Bedrock Knowledge Base에서 관련 케이스를 검색한다
2. WHEN Knowledge Base 검색이 완료되면, THE KB Bot SHALL 관련도가 높은 순서로 최대 3개의 유사 케이스를 반환한다
3. WHEN 검색 결과가 표시될 때, THE KB Bot SHALL 각 케이스의 번호, 제목, 해결 방법을 포함한다
4. WHEN 검색 결과가 없을 때, THE KB Bot SHALL 결과가 없음을 알리고 케이스 생성을 안내한다
5. WHEN 검색 요청이 실패하면, THE KB Bot SHALL 에러 메시지를 표시하고 재시도를 안내한다

### Requirement 2: AI 기반 답변 생성

**User Story:** 사용자로서, 질문에 대해 AI가 Knowledge Base를 기반으로 종합적인 답변을 제공받고 싶다.

#### Acceptance Criteria

1. WHEN 사용자가 KB Bot에게 질문하면, THE KB Bot SHALL Q CLI를 통해 Bedrock KB MCP로 관련 케이스를 검색한다
2. WHEN 관련 케이스가 발견되면, THE KB Bot SHALL Q CLI를 통해 케이스 내용을 기반으로 답변을 생성한다
3. WHEN 답변이 생성될 때, THE KB Bot SHALL 해결 방법과 관련 케이스 링크를 포함한다
4. WHEN 여러 케이스가 관련될 때, THE KB Bot SHALL 가장 적합한 해결 방법을 우선적으로 제시한다
5. WHEN 답변 생성이 완료되면, THE KB Bot SHALL 3초 이내에 Slack에 응답을 표시한다

### Requirement 3: 케이스 자동 Knowledge Base 동기화

**User Story:** 시스템 관리자로서, 케이스가 해결되면 자동으로 Knowledge Base에 저장되어 향후 검색에 활용되기를 원한다.

#### Acceptance Criteria

1. WHEN AWS Support 케이스가 해결 상태로 변경되면, THE System SHALL EventBridge를 통해 ResolveCase 이벤트를 감지한다
2. WHEN ResolveCase 이벤트가 감지되면, THE System SHALL Lambda 함수를 트리거하여 케이스 처리를 시작한다
3. WHEN Lambda 함수가 실행되면, THE System SHALL Support API를 통해 케이스 전체 내용과 대화 내역을 수집한다
4. WHEN 케이스 내용이 수집되면, THE System SHALL Bedrock Claude를 사용하여 케이스를 요약하고 카테고리를 분류한다
5. WHEN 요약이 완료되면, THE System SHALL 구조화된 JSON 형식으로 S3에 저장한다
6. WHEN S3 저장이 완료되면, THE System SHALL Bedrock Knowledge Base 인덱싱 작업을 트리거한다
7. WHEN 인덱싱이 완료되면, THE System SHALL 해당 케이스가 다음 검색부터 조회 가능하도록 한다

### Requirement 4: 케이스 분류 및 구조화

**User Story:** 시스템 관리자로서, 케이스가 카테고리와 서비스별로 자동 분류되어 체계적으로 저장되기를 원한다.

#### Acceptance Criteria

1. WHEN Bedrock Claude가 케이스를 분석하면, THE System SHALL 케이스를 technical, billing, account 중 하나로 분류한다
2. WHEN 카테고리가 결정되면, THE System SHALL AWS 서비스명(ec2, rds, lambda 등)을 추출한다
3. WHEN 분류가 완료되면, THE System SHALL S3 경로를 {category}/{service}/{date}/{case-id}.json 형식으로 생성한다
4. WHEN JSON 데이터를 생성할 때, THE System SHALL case_id, question, solution, steps, tags 필드를 포함한다
5. WHEN 케이스 요약이 생성되면, THE System SHALL 핵심 질문을 1-2문장으로 요약한다
6. WHEN 해결 방법이 정리되면, THE System SHALL 단계별 해결 과정을 배열 형태로 저장한다

### Requirement 5: 과거 케이스 마이그레이션

**User Story:** 시스템 관리자로서, 시스템 구축 전에 생성된 과거 케이스들을 일괄적으로 Knowledge Base에 추가하고 싶다.

#### Acceptance Criteria

1. WHEN 마이그레이션 스크립트가 실행되면, THE System SHALL 지정된 기간의 해결된 케이스 목록을 조회한다
2. WHEN 케이스 목록이 조회되면, THE System SHALL 각 케이스를 순차적으로 처리한다
3. WHEN 케이스를 처리할 때, THE System SHALL 이미 Knowledge Base에 존재하는 케이스는 건너뛴다
4. WHEN Bedrock API 호출이 실패하면, THE System SHALL 최대 3회까지 재시도한다
5. WHEN 각 케이스 처리 후, THE System SHALL Rate Limit 방지를 위해 1초간 대기한다
6. WHEN 마이그레이션이 완료되면, THE System SHALL 성공, 스킵, 실패 건수를 로그에 기록한다
7. WHEN 실패한 케이스가 있으면, THE System SHALL 케이스 ID와 에러 메시지를 별도 파일에 저장한다

### Requirement 6: Slack 대화형 인터페이스

**User Story:** 사용자로서, Slack에서 자연스러운 대화를 통해 KB Bot과 상호작용하고 싶다.

#### Acceptance Criteria

1. WHEN 사용자가 KB Bot을 멘션하면, THE KB Bot SHALL 메시지를 수신하고 처리를 시작한다
2. WHEN KB Bot이 처리 중일 때, THE KB Bot SHALL "검색 중..." 메시지를 즉시 표시한다
3. WHEN 검색 결과가 준비되면, THE KB Bot SHALL 동일한 스레드에 응답을 표시한다
4. WHEN 사용자가 스레드에서 추가 질문하면, THE KB Bot SHALL 대화 컨텍스트를 유지하며 응답한다
5. WHEN KB Bot이 케이스 생성을 제안할 때, THE KB Bot SHALL AWS Support App 사용 방법을 안내한다

### Requirement 7: 에러 처리 및 복구

**User Story:** 시스템 관리자로서, 시스템 오류 발생 시 자동으로 복구되거나 명확한 에러 정보를 제공받고 싶다.

#### Acceptance Criteria

1. WHEN Lambda 함수 실행 중 에러가 발생하면, THE System SHALL 에러 내용을 CloudWatch Logs에 기록한다
2. WHEN Bedrock API 호출이 실패하면, THE System SHALL 지수 백오프 방식으로 재시도한다
3. WHEN S3 저장이 실패하면, THE System SHALL 에러를 로그에 기록하고 Lambda 함수를 실패 상태로 종료한다
4. WHEN KB Bot이 Q CLI 실행에 실패하면, THE System SHALL 사용자에게 일시적 오류 메시지를 표시한다
5. WHEN EventBridge Rule이 Lambda 트리거에 실패하면, THE System SHALL 자동으로 재시도한다
