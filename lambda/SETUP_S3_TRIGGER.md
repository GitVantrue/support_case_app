# S3 이벤트 트리거 설정 가이드

## 개요

S3에 새 파일이 업로드되면 자동으로 Bedrock KB 동기화를 실행합니다.

## 장점

- ✅ 완전 자동화
- ✅ 수동 업로드도 자동 동기화
- ✅ 마이그레이션 완료 후 자동 동기화
- ✅ 실패 시 S3가 자동 재시도

## 설정 방법

### 1. Lambda 함수 생성

```bash
# 1. 코드 패키징
cd lambda
zip function.zip sync_kb_on_s3_upload.py

# 2. Lambda 함수 생성
aws lambda create-function \
  --function-name SyncKBOnS3Upload \
  --runtime python3.12 \
  --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-kb-sync-role \
  --handler sync_kb_on_s3_upload.lambda_handler \
  --zip-file fileb://function.zip \
  --timeout 60 \
  --memory-size 256 \
  --region ap-northeast-2 \
  --environment Variables="{
    KB_ID=your-kb-id,
    DS_ID=your-ds-id,
    AWS_REGION=ap-northeast-2
  }"
```

### 2. S3 버킷에 이벤트 알림 설정

#### 방법 A: AWS CLI

```bash
# 1. Lambda 권한 추가 (S3가 Lambda 호출 가능하도록)
aws lambda add-permission \
  --function-name SyncKBOnS3Upload \
  --statement-id s3-trigger \
  --action lambda:InvokeFunction \
  --principal s3.amazonaws.com \
  --source-arn arn:aws:s3:::support-knowledge-base-20251204 \
  --region ap-northeast-2

# 2. S3 이벤트 알림 설정 파일 생성
cat > s3-notification.json << 'EOF'
{
  "LambdaFunctionConfigurations": [
    {
      "Id": "kb-sync-on-upload",
      "LambdaFunctionArn": "arn:aws:lambda:ap-northeast-2:YOUR_ACCOUNT:function:SyncKBOnS3Upload",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {
        "Key": {
          "FilterRules": [
            {
              "Name": "suffix",
              "Value": ".json"
            }
          ]
        }
      }
    }
  ]
}
EOF

# 3. S3 버킷에 알림 설정 적용
aws s3api put-bucket-notification-configuration \
  --bucket support-knowledge-base-20251204 \
  --notification-configuration file://s3-notification.json \
  --region ap-northeast-2
```

#### 방법 B: AWS Console

1. **S3 Console** 열기
2. `support-knowledge-base-20251204` 버킷 선택
3. **Properties** 탭 → **Event notifications** 섹션
4. **Create event notification** 클릭
5. 설정:
   - **Event name**: `kb-sync-on-upload`
   - **Event types**: `All object create events` 선택
   - **Suffix**: `.json` (JSON 파일만)
   - **Destination**: `Lambda function`
   - **Lambda function**: `SyncKBOnS3Upload` 선택
6. **Save changes**

### 3. IAM 역할 권한

Lambda 함수에 필요한 권한:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock-agent:StartIngestionJob",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

## 테스트

### 1. 수동 파일 업로드로 테스트

```bash
# 테스트 파일 생성
cat > test-case.json << 'EOF'
{
  "case_id": "test-123",
  "question": "테스트 질문",
  "solution": "테스트 해결 방법"
}
EOF

# S3에 업로드
aws s3 cp test-case.json s3://support-knowledge-base-20251204/technical/test/2025-12/test-123.json --region ap-northeast-2

# Lambda 로그 확인
aws logs tail /aws/lambda/SyncKBOnS3Upload --follow --region ap-northeast-2
```

### 2. 예상 로그

```
📁 S3 이벤트: ObjectCreated:Put
   버킷: support-knowledge-base-20251204
   파일: technical/test/2025-12/test-123.json
🔄 Bedrock KB 동기화 시작...
✅ 동기화 작업 시작됨
   Job ID: abc123...
   상태: STARTING
```

### 3. KB 동기화 상태 확인

```bash
aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id YOUR_KB_ID \
  --data-source-id YOUR_DS_ID \
  --max-results 5 \
  --region ap-northeast-2
```

## 동작 흐름

```
1. 케이스 해결 → Lambda (ProcessResolvedCase) 실행
2. Lambda가 S3에 JSON 저장
3. S3 이벤트 발생 (ObjectCreated)
4. Lambda (SyncKBOnS3Upload) 자동 트리거
5. Bedrock KB 동기화 시작
6. 인덱싱 완료 (백그라운드, 5-10분)
7. 검색 가능!
```

## 기존 Lambda 수정 (선택사항)

기존 `ProcessResolvedCase` Lambda에서 동기화 호출을 제거할 수 있습니다:

```python
# 기존 코드 (제거 가능)
if not MOCK_MODE and KB_ID and DS_ID:
    print(f"4️⃣ Bedrock Knowledge Base 동기화 중...")
    trigger_kb_sync()
else:
    print(f"4️⃣ Bedrock KB 동기화 스킵")

# 새 코드
print(f"4️⃣ Bedrock KB 동기화는 S3 이벤트 트리거가 자동 처리")
```

**장점**: 
- Lambda 실행 시간 단축
- S3 저장과 동기화 분리
- 더 깔끔한 아키텍처

## 트러블슈팅

### 문제 1: Lambda가 트리거되지 않음

**확인**:
```bash
# S3 이벤트 알림 설정 확인
aws s3api get-bucket-notification-configuration \
  --bucket support-knowledge-base-20251204 \
  --region ap-northeast-2

# Lambda 권한 확인
aws lambda get-policy \
  --function-name SyncKBOnS3Upload \
  --region ap-northeast-2
```

### 문제 2: "Access Denied" 에러

**원인**: Lambda IAM 역할에 Bedrock 권한 부족

**해결**: IAM 역할에 `bedrock-agent:StartIngestionJob` 권한 추가

### 문제 3: 동기화가 너무 자주 실행됨

**원인**: 파일이 여러 번 업로드되거나 수정됨

**해결**: 
- 필터 조건 추가 (특정 경로만)
- 중복 실행 방지 로직 추가

## 비용

- **Lambda 실행**: 파일당 $0.0000002 (거의 무료)
- **S3 이벤트**: 무료
- **Bedrock KB 인덱싱**: 작업당 $0.10

**예상**: 월 100개 파일 업로드 시 약 $10

## 다음 단계

1. Lambda 함수 생성
2. S3 이벤트 알림 설정
3. 테스트 파일 업로드
4. 로그 확인
5. KB 동기화 상태 확인
6. 완료!
