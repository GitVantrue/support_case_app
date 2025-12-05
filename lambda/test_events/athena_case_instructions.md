# Athena MSCK 케이스 테스트 가이드

## 케이스 정보
- **제목**: MSCK 쿼리 간헐적 오류
- **케이스 ID**: 14424339821
- **생성일**: 2023-12-06
- **상태**: 해결됨
- **심각도**: 시스템 손상
- **카테고리**: Athena, Query Related Issue
- **서비스**: Amazon Athena

## 테스트 실행 방법

### 1단계: 실제 케이스 ID 확인

먼저 AWS CLI로 이 케이스의 정확한 case-id를 확인해야 합니다:

```bash
# 2023년 12월 케이스 조회
aws support describe-cases \
  --include-resolved-cases \
  --after-time "2023-12-01T00:00:00Z" \
  --before-time "2023-12-31T23:59:59Z" \
  --region us-east-1 \
  --query "cases[?displayId=='14424339821']" \
  --output json
```

출력 예시:
```json
{
  "cases": [
    {
      "caseId": "case-986719740728-muen-2023-xxxxx",
      "displayId": "14424339821",
      "subject": "MSCK 쿼리 간헐적 오류",
      "status": "resolved",
      ...
    }
  ]
}
```

### 2단계: 테스트 이벤트 업데이트

위에서 확인한 정확한 `caseId`를 `real_case_test.json`에 입력:

```json
{
  "detail": {
    "case-id": "case-986719740728-muen-2023-xxxxx",  // 실제 값으로 변경
    "display-id": "14424339821",
    ...
  }
}
```

### 3단계: Lambda 환경 변수 설정

Lambda 콘솔에서 환경 변수 업데이트:

```
MOCK_MODE = false
BUCKET_NAME = support-knowledge-base-20251204
```

### 4단계: Lambda 테스트 실행

1. Lambda 콘솔 → ProcessResolvedCase 함수
2. "테스트" 탭 클릭
3. "새 이벤트 생성" 클릭
4. 이벤트 이름: `athena-msck-case`
5. `real_case_test.json` 내용 붙여넣기 (case-id 수정 후)
6. "테스트" 버튼 클릭

### 5단계: 결과 확인

#### CloudWatch Logs 확인
```
📋 이벤트 수신: ResolveCase for case 14424339821
1️⃣ 케이스 정보 수집 중...
   케이스 제목: MSCK 쿼리 간헐적 오류
   대화 수: X개
2️⃣ Bedrock Claude로 요약 생성 중...
   Bedrock 요약 완료 (시도 1/3)
3️⃣ S3에 저장 중...
   ✅ S3 저장 완료: s3://support-knowledge-base-20251204/technical/athena/2025-12/14424339821.json
4️⃣ Bedrock KB 동기화 스킵 (KB_ID 미설정)
✅ 케이스 처리 완료: 14424339821
```

#### S3 파일 확인
```bash
# S3에 저장된 파일 확인
aws s3 ls s3://support-knowledge-base-20251204/technical/athena/2025-12/

# JSON 파일 다운로드 및 내용 확인
aws s3 cp s3://support-knowledge-base-20251204/technical/athena/2025-12/14424339821.json - | jq .
```

### 예상 결과 (JSON)

```json
{
  "category": "technical",
  "service": "athena",
  "question": "Athena에서 MSCK REPAIR TABLE 쿼리가 간헐적으로 실패함",
  "answer": "파티션 메타데이터 동기화 문제로 인한 오류, Glue Crawler 사용 권장",
  "solution": "MSCK 대신 Glue Crawler를 사용하여 파티션을 자동으로 감지하고 추가",
  "steps": [
    "Glue Crawler 생성 및 S3 데이터 소스 지정",
    "스케줄 설정 (예: 매일 또는 주기적)",
    "Crawler 실행하여 파티션 자동 추가",
    "Athena 쿼리로 파티션 확인"
  ],
  "tags": ["athena", "msck", "partition", "glue-crawler", "query-error"],
  "user_messages": [...],
  "support_messages": [...],
  "case_id": "case-986719740728-muen-2023-xxxxx",
  "display_id": "14424339821",
  "severity": "high",
  "created_at": "2023-12-06T02:00:04.737Z",
  "resolved_at": "2023-12-XX..."
}
```

## 트러블슈팅

### 문제: "케이스를 찾을 수 없습니다"

**원인**: 케이스 ID 형식이 잘못되었거나 Support API 권한 부족

**해결 방법**:
1. AWS CLI로 정확한 case-id 확인 (위 1단계 참조)
2. Lambda IAM 역할 권한 확인:
   ```json
   {
     "Effect": "Allow",
     "Action": [
       "support:DescribeCases",
       "support:DescribeCommunications"
     ],
     "Resource": "*"
   }
   ```

### 문제: "Access Denied" (Support API)

**원인**: Support API는 Business 또는 Enterprise Support 플랜이 필요

**해결 방법**:
1. AWS Support 플랜 확인
2. 또는 MOCK_MODE=true로 테스트 계속

### 문제: Bedrock 요약이 이상함

**원인**: 케이스 내용이 복잡하거나 대화가 많음

**해결 방법**:
1. CloudWatch Logs에서 Bedrock 입력 프롬프트 확인
2. 프롬프트 개선 (필요시)
3. 재시도 로직이 작동하는지 확인

## 다음 테스트 케이스

이 케이스가 성공하면 다른 서비스 케이스도 테스트:
- EC2 관련 케이스
- RDS 관련 케이스
- Lambda 관련 케이스
- Billing 관련 케이스

각 서비스별로 S3 경로가 다르게 생성되는지 확인:
- `technical/athena/2025-12/14424339821.json`
- `technical/ec2/2025-12/xxxxx.json`
- `billing/2025-12/xxxxx.json`
