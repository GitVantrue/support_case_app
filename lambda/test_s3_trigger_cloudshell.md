# CloudShell에서 S3 트리거 테스트

로컬에 AWS CLI 권한이 없을 때 CloudShell에서 테스트하는 방법입니다.

## 1. CloudShell 열기

AWS Console → 우측 상단 CloudShell 아이콘 클릭 (>_ 모양)

## 2. 테스트 파일 생성

```bash
# 간단한 테스트 JSON 생성
cat > test-s3-trigger.json << 'EOF'
{
  "case_id": "test-cloudshell-001",
  "display_id": "99999",
  "category": "technical",
  "service": "s3",
  "question": "CloudShell에서 S3 트리거 테스트",
  "answer": "S3 트리거가 정상 작동하는지 확인",
  "solution": "파일 업로드 시 자동으로 KB 동기화 실행",
  "steps": ["S3 업로드", "Lambda 트리거", "KB 동기화"],
  "tags": ["test", "cloudshell", "s3-trigger"],
  "severity": "low",
  "created_at": "2025-12-05T00:00:00Z",
  "resolved_at": "2025-12-05T01:00:00Z"
}
EOF
```

## 3. S3에 업로드

```bash
BUCKET="support-knowledge-base-20251204"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

aws s3 cp test-s3-trigger.json \
  s3://${BUCKET}/test/cloudshell-${TIMESTAMP}.json \
  --region ap-northeast-2

echo "✅ 업로드 완료: s3://${BUCKET}/test/cloudshell-${TIMESTAMP}.json"
```

## 4. Lambda 로그 확인 (5초 대기)

```bash
echo "⏳ 5초 대기 중..."
sleep 5

echo "📋 Lambda 로그 확인:"
aws logs tail /aws/lambda/SyncKBOnS3Upload \
  --since 1m \
  --region ap-northeast-2
```

## 5. 성공 확인

로그에서 다음 메시지 확인:

```
📁 S3 이벤트: ObjectCreated:Put
   버킷: support-knowledge-base-20251204
   파일: test/cloudshell-...
🔄 Bedrock KB 동기화 시작...
✅ 동기화 작업 시작됨
   Job ID: xxx
   상태: STARTING
```

## 6. 실시간 모니터링 (선택사항)

다른 CloudShell 탭을 열어서:

```bash
# 실시간 로그 모니터링
aws logs tail /aws/lambda/SyncKBOnS3Upload \
  --follow \
  --region ap-northeast-2
```

이 상태에서 첫 번째 탭에서 파일 업로드하면 즉시 로그가 보입니다!

## 7. KB 동기화 작업 확인

```bash
# KB_ID와 DS_ID를 실제 값으로 변경
aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id YOUR_KB_ID \
  --data-source-id YOUR_DS_ID \
  --max-results 5 \
  --region ap-northeast-2
```

## 전체 한 번에 실행

```bash
# 원라이너 테스트
BUCKET="support-knowledge-base-20251204" && \
echo '{"test":"cloudshell","time":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}' > test.json && \
aws s3 cp test.json s3://${BUCKET}/test/$(date +%Y%m%d-%H%M%S).json --region ap-northeast-2 && \
sleep 5 && \
aws logs tail /aws/lambda/SyncKBOnS3Upload --since 1m --region ap-northeast-2
```

## 테스트 파일 정리 (선택사항)

```bash
# 테스트 파일 삭제
aws s3 rm s3://support-knowledge-base-20251204/test/ \
  --recursive \
  --region ap-northeast-2

# KB 재동기화 (삭제 반영)
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id YOUR_KB_ID \
  --data-source-id YOUR_DS_ID \
  --region ap-northeast-2
```

## 문제 해결

### Lambda가 트리거되지 않음

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

### 로그가 안 보임

```bash
# 로그 그룹 존재 확인
aws logs describe-log-groups \
  --log-group-name-prefix /aws/lambda/SyncKBOnS3Upload \
  --region ap-northeast-2

# 최근 로그 스트림 확인
aws logs describe-log-streams \
  --log-group-name /aws/lambda/SyncKBOnS3Upload \
  --order-by LastEventTime \
  --descending \
  --max-items 5 \
  --region ap-northeast-2
```
