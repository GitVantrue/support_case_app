# ✅ 실제 케이스 테스트 준비 완료

## 케이스 정보
- **제목**: MSCK 쿼리 간헐적 오류
- **케이스 ID**: `case-370662402529-muko-2023-8a933541f4bc87c5`
- **Display ID**: `14424339821`
- **서비스**: Amazon Athena
- **생성일**: 2023-12-06

## 테스트 실행 단계

### 1단계: Lambda 환경 변수 설정

Lambda 콘솔 → ProcessResolvedCase → 구성 → 환경 변수:

```
MOCK_MODE = false                                    # ← 실제 API 호출
BUCKET_NAME = support-knowledge-base-20251204        # ← 실제 S3 버킷명
KB_ID = (선택사항, 아직 없으면 비워두기)
DS_ID = (선택사항, 아직 없으면 비워두기)
```

⚠️ **중요**: `MOCK_MODE=false`로 설정해야 실제 Support API를 호출합니다!

### 2단계: Lambda 테스트 실행

1. **Lambda 콘솔 열기**
   - AWS Console → Lambda → ProcessResolvedCase

2. **테스트 이벤트 생성**
   - "테스트" 탭 클릭
   - "새 이벤트 생성" 클릭
   - 이벤트 이름: `athena-msck-real-case`
   - 아래 JSON 붙여넣기:

```json
{
  "version": "0",
  "id": "test-event-real-case-athena",
  "detail-type": "Support Case Update",
  "source": "aws.support",
  "region": "us-east-1",
  "time": "2023-12-06T02:00:04.737Z",
  "detail": {
    "case-id": "case-370662402529-muko-2023-8a933541f4bc87c5",
    "display-id": "14424339821",
    "communication-id": "",
    "event-name": "ResolveCase",
    "origin": ""
  }
}
```

3. **테스트 실행**
   - "테스트" 버튼 클릭
   - 실행 시간: 약 10-15초 예상

### 3단계: 결과 확인

#### A. Lambda 실행 결과 확인

성공 시 응답:
```json
{
  "statusCode": 200,
  "body": {
    "message": "Successfully processed case",
    "case_id": "case-370662402529-muko-2023-8a933541f4bc87c5",
    "display_id": "14424339821",
    "result": {
      "s3_key": "technical/athena/2025-12/14424339821.json",
      "category": "technical",
      "service": "athena"
    }
  }
}
```

#### B. CloudWatch Logs 확인

Lambda 콘솔 → "모니터링" 탭 → "CloudWatch에서 로그 보기"

예상 로그:
```
📋 이벤트 수신: ResolveCase for case 14424339821 (case-370662402529-muko-2023-8a933541f4bc87c5)
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

#### C. S3 파일 확인

```bash
# S3 버킷 내용 확인
aws s3 ls s3://support-knowledge-base-20251204/technical/athena/2025-12/ --region ap-northeast-2

# 저장된 JSON 파일 다운로드
aws s3 cp s3://support-knowledge-base-20251204/technical/athena/2025-12/14424339821.json - --region ap-northeast-2 | jq .
```

예상 JSON 구조:
```json
{
  "category": "technical",
  "service": "athena",
  "question": "Athena에서 MSCK REPAIR TABLE 쿼리가 간헐적으로 실패하는 문제",
  "answer": "파티션 메타데이터 동기화 문제로 Glue Crawler 사용 권장",
  "solution": "MSCK 대신 AWS Glue Crawler를 사용하여 파티션을 자동으로 감지하고 추가",
  "steps": [
    "Glue Crawler 생성 및 S3 데이터 소스 지정",
    "스케줄 설정하여 주기적으로 실행",
    "Crawler 실행하여 파티션 자동 추가",
    "Athena 쿼리로 파티션 확인"
  ],
  "tags": ["athena", "msck", "partition", "glue-crawler", "query-error"],
  "user_messages": [...],
  "support_messages": [...],
  "case_id": "case-370662402529-muko-2023-8a933541f4bc87c5",
  "display_id": "14424339821",
  "severity": "high",
  "created_at": "2023-12-06T02:00:04.737Z",
  "resolved_at": "..."
}
```

## 예상 문제 및 해결

### ❌ 문제 1: "케이스를 찾을 수 없습니다"

**원인**: Lambda IAM 역할에 Support API 권한 부족

**해결**:
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

### ❌ 문제 2: "Access Denied" (Support API)

**원인**: AWS Support 플랜이 Developer 이하

**해결**: Business 또는 Enterprise Support 플랜 필요

### ❌ 문제 3: "Bedrock API 호출 실패"

**원인**: Lambda IAM 역할에 Bedrock 권한 부족 또는 모델 액세스 미활성화

**해결**:
1. IAM 권한 추가:
```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModel"
  ],
  "Resource": "*"
}
```

2. Bedrock Console → Model access → Claude 3 Sonnet 활성화

### ❌ 문제 4: "S3 저장 실패"

**원인**: Lambda IAM 역할에 S3 권한 부족

**해결**:
```json
{
  "Effect": "Allow",
  "Action": [
    "s3:PutObject",
    "s3:GetObject"
  ],
  "Resource": "arn:aws:s3:::support-knowledge-base-20251204/*"
}
```

### ❌ 문제 5: "타임아웃"

**원인**: Lambda 타임아웃 설정이 너무 짧음 (기본 3초)

**해결**: Lambda 구성 → 일반 구성 → 타임아웃을 120초로 증가

## 성공 기준

✅ Lambda 실행이 성공 (statusCode: 200)
✅ CloudWatch Logs에 모든 단계 완료 메시지
✅ S3에 JSON 파일 저장됨
✅ JSON 파일에 필수 필드 모두 포함
✅ category가 "technical", service가 "athena"

## 다음 단계

이 테스트가 성공하면:
1. ✅ Task 2.6 "Lambda 배포 및 테스트" 완료 표시
2. → 다른 서비스 케이스로도 테스트 (EC2, RDS 등)
3. → Bedrock Knowledge Base 생성 및 동기화 테스트
4. → EventBridge Rule 연결 테스트
