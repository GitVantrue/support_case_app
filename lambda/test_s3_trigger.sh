#!/bin/bash
# S3 트리거 테스트 스크립트

set -e

BUCKET_NAME="support-knowledge-base-20251204"
REGION="ap-northeast-2"
LAMBDA_FUNCTION="SyncKBOnS3Upload"

echo "🧪 S3 트리거 테스트 시작"
echo "================================"

# 1. 테스트 파일 생성
echo ""
echo "1️⃣ 테스트 파일 생성 중..."
cat > /tmp/test-s3-trigger.json << 'EOF'
{
  "case_id": "test-s3-trigger-001",
  "display_id": "99999",
  "category": "technical",
  "service": "s3",
  "question": "S3 트리거 테스트 질문입니다",
  "answer": "S3 트리거가 정상 작동하는지 확인하는 테스트입니다",
  "solution": "파일 업로드 시 자동으로 KB 동기화가 실행되어야 합니다",
  "steps": [
    "1. S3에 파일 업로드",
    "2. Lambda 자동 트리거",
    "3. KB 동기화 시작"
  ],
  "tags": ["test", "s3-trigger", "automation"],
  "severity": "low",
  "created_at": "2025-12-05T00:00:00Z",
  "resolved_at": "2025-12-05T01:00:00Z"
}
EOF

echo "✅ 테스트 파일 생성 완료: /tmp/test-s3-trigger.json"

# 2. S3에 업로드
echo ""
echo "2️⃣ S3에 파일 업로드 중..."
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
S3_KEY="test/trigger-test/${TIMESTAMP}/test-s3-trigger.json"

aws s3 cp /tmp/test-s3-trigger.json \
  s3://${BUCKET_NAME}/${S3_KEY} \
  --region ${REGION}

echo "✅ 업로드 완료: s3://${BUCKET_NAME}/${S3_KEY}"

# 3. Lambda 로그 확인 (5초 대기)
echo ""
echo "3️⃣ Lambda 실행 대기 중 (5초)..."
sleep 5

echo ""
echo "4️⃣ Lambda 로그 확인 중..."
echo "================================"

# 최근 로그 스트림 가져오기
LOG_GROUP="/aws/lambda/${LAMBDA_FUNCTION}"
LATEST_STREAM=$(aws logs describe-log-streams \
  --log-group-name ${LOG_GROUP} \
  --order-by LastEventTime \
  --descending \
  --max-items 1 \
  --region ${REGION} \
  --query 'logStreams[0].logStreamName' \
  --output text 2>/dev/null || echo "")

if [ -z "$LATEST_STREAM" ] || [ "$LATEST_STREAM" = "None" ]; then
  echo "⚠️  로그 스트림을 찾을 수 없습니다"
  echo ""
  echo "수동으로 확인하세요:"
  echo "aws logs tail ${LOG_GROUP} --follow --region ${REGION}"
else
  # 로그 출력
  aws logs get-log-events \
    --log-group-name ${LOG_GROUP} \
    --log-stream-name ${LATEST_STREAM} \
    --limit 50 \
    --region ${REGION} \
    --query 'events[*].message' \
    --output text
fi

echo ""
echo "================================"
echo "✅ 테스트 완료!"
echo ""
echo "📊 확인 사항:"
echo "1. Lambda가 실행되었는가?"
echo "2. '📁 S3 이벤트' 메시지가 보이는가?"
echo "3. '✅ 동기화 작업 시작됨' 메시지가 보이는가?"
echo ""
echo "🔍 추가 확인:"
echo "# Lambda 로그 실시간 모니터링"
echo "aws logs tail ${LOG_GROUP} --follow --region ${REGION}"
echo ""
echo "# KB 동기화 작업 확인 (KB_ID와 DS_ID 필요)"
echo "aws bedrock-agent list-ingestion-jobs \\"
echo "  --knowledge-base-id YOUR_KB_ID \\"
echo "  --data-source-id YOUR_DS_ID \\"
echo "  --max-results 5 \\"
echo "  --region ${REGION}"
echo ""
echo "# 업로드된 파일 확인"
echo "aws s3 ls s3://${BUCKET_NAME}/${S3_KEY} --region ${REGION}"
