# Support Event Bridge Lambda 설정 가이드

## 개요
AWS Support 이벤트는 us-east-1 리전에서만 발생하므로, us-east-1에 브릿지 Lambda를 생성하여 ap-northeast-2의 Lambda로 이벤트를 전달합니다.

## 아키텍처
```
[Support Case Resolved]
    ↓ (us-east-1)
[EventBridge Rule - us-east-1]
    ↓
[Bridge Lambda - us-east-1]
    ↓ (크로스 리전 호출)
[Process Lambda - ap-northeast-2]
    ↓
[S3 Bucket - ap-northeast-2]
```

---

## 1. IAM Role 생성 (us-east-1)

### AWS 콘솔에서:
1. IAM → Roles → Create role
2. Trusted entity: Lambda
3. Role name: `support-bridge-lambda-role`
4. 권한 정책:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": "arn:aws:lambda:ap-northeast-2:*:function:process-resolved-case"
    }
  ]
}
```

---

## 2. Lambda 함수 생성 (us-east-1)

### AWS 콘솔에서:
1. Lambda → Create function
2. 설정:
   - Function name: `support-event-bridge`
   - Runtime: **Python 3.14**
   - Architecture: x86_64
   - Execution role: `support-bridge-lambda-role` (위에서 생성한 Role)

3. 코드 업로드:
   - `lambda/bridge_support_event.py` 파일 내용을 복사하여 붙여넣기

4. Configuration 설정:
   - Timeout: 30초
   - Memory: 128 MB

5. Environment variables:
   - Key: `TARGET_LAMBDA_ARN`
   - Value: `process-resolved-case`

---

## 3. EventBridge 규칙 생성 (us-east-1)

### AWS 콘솔에서:
1. EventBridge → Rules → Create rule
2. 설정:
   - Name: `support-case-resolved-bridge`
   - Event bus: default
   - Rule type: Rule with an event pattern

3. Event pattern:
```json
{
  "source": ["aws.support"],
  "detail-type": ["Support Case Update"],
  "detail": {
    "event-name": ["ResolveCase"]
  }
}
```

4. Target:
   - Target type: AWS service
   - Select a target: Lambda function
   - Function: `support-event-bridge`

5. Create rule

---

## 4. 기존 서울 리전 규칙 삭제

### AWS 콘솔에서:
1. 리전을 **ap-northeast-2 (서울)** 로 변경
2. EventBridge → Rules
3. 기존 Support 관련 규칙 찾기
4. Delete

---

## 5. 테스트

### 방법 1: Lambda 테스트 이벤트 (us-east-1)

1. Lambda → `support-event-bridge` → Test
2. Test event:
```json
{
  "version": "0",
  "id": "test-event-id",
  "region": "us-east-1",
  "time": "2024-12-05T10:00:00Z",
  "source": "aws.support",
  "detail-type": "Support Case Update",
  "resources": [],
  "detail": {
    "case-id": "case-test-123",
    "display-id": "12345",
    "event-name": "ResolveCase"
  }
}
```

3. Test 실행
4. CloudWatch Logs 확인:
   - us-east-1: `/aws/lambda/support-event-bridge`
   - ap-northeast-2: `/aws/lambda/process-resolved-case`

### 방법 2: 실제 Support 케이스

1. AWS Support에서 테스트 케이스 생성
2. 케이스를 Resolved로 변경
3. 몇 분 후 CloudWatch Logs 확인

---

## 6. 모니터링

### CloudWatch Logs 확인:

**us-east-1 브릿지 Lambda:**
```bash
aws logs tail /aws/lambda/support-event-bridge --follow --region us-east-1
```

**ap-northeast-2 처리 Lambda:**
```bash
aws logs tail /aws/lambda/process-resolved-case --follow --region ap-northeast-2
```

### EventBridge 지표:

- EventBridge → Rules → `support-case-resolved-bridge` → Monitoring
- Invocations, FailedInvocations 확인

---

## 트러블슈팅

### 이벤트가 전달되지 않는 경우:

1. **Support 플랜 확인**
   - Business 또는 Enterprise Support 필요
   - Basic/Developer 플랜에서는 이벤트 발생 안 함

2. **IAM 권한 확인**
   - 브릿지 Lambda Role에 `lambda:InvokeFunction` 권한 있는지 확인

3. **리전 확인**
   - EventBridge 규칙: us-east-1
   - 브릿지 Lambda: us-east-1
   - 처리 Lambda: ap-northeast-2

4. **CloudWatch Logs 확인**
   - 에러 메시지 확인
   - 이벤트 페이로드 확인

---

## 비용

- **브릿지 Lambda (us-east-1)**
  - 실행 시간: ~100ms
  - 메모리: 128MB
  - 월 예상 비용: 케이스 수에 따라 다름 (대부분 무료 티어 내)

- **EventBridge**
  - 무료 (기본 이벤트 버스)

- **크로스 리전 Lambda 호출**
  - 데이터 전송 비용 발생 (매우 적음)
