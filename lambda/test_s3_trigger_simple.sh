#!/bin/bash
# 간단한 S3 트리거 테스트

BUCKET="support-knowledge-base-20251204"
REGION="ap-northeast-2"

echo "🧪 S3 트리거 테스트"
echo ""

# 테스트 파일 생성 및 업로드
echo '{"test": "s3-trigger", "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}' > /tmp/test.json

echo "📤 파일 업로드 중..."
aws s3 cp /tmp/test.json s3://${BUCKET}/test/$(date +%Y%m%d-%H%M%S).json --region ${REGION}

echo ""
echo "⏳ 5초 대기..."
sleep 5

echo ""
echo "📋 Lambda 로그 확인:"
aws logs tail /aws/lambda/SyncKBOnS3Upload --since 1m --region ${REGION}

echo ""
echo "✅ 완료! 위 로그에서 '📁 S3 이벤트'와 '✅ 동기화 작업 시작됨'을 확인하세요"
