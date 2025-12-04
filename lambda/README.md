# Lambda 함수 배포 가이드

## 파일 설명

- `process_resolved_case.py`: Lambda 함수 메인 코드
- `requirements.txt`: Python 의존성 (boto3)

## 배포 방법

### 방법 1: AWS 콘솔에서 직접 업로드 (간단)

1. AWS Lambda 콘솔 → ProcessResolvedCase 함수 선택
2. "코드" 탭 → "코드 소스" 섹션
3. `lambda_function.py` 파일 내용을 `process_resolved_case.py` 내용으로 교체
4. "Deploy" 버튼 클릭

### 방법 2: ZIP 파일로 배포 (권장)

```bash
# 1. 의존성 설치 (로컬)
pip install -r requirements.txt -t package/

# 2. 코드 복사
cp process_resolved_case.py package/lambda_function.py

# 3. ZIP 파일 생성
cd package
zip -r ../lambda_function.zip .
cd ..

# 4. AWS CLI로 업로드
aws lambda update-function-code \
  --function-name ProcessResolvedCase \
  --zip-file fileb://lambda_function.zip \
  --region ap-northeast-2
```

## 환경 변수 설정

Lambda 콘솔에서 다음 환경 변수를 설정하세요:

```
BUCKET_NAME = support-knowledge-base
KB_ID = kb-xxxxx (Bedrock KB 생성 후)
DS_ID = ds-xxxxx (Bedrock KB 생성 후)
MOCK_MODE = true (테스트 시) 또는 false (프로덕션)
```

## 테스트

### 테스트 이벤트 생성

Lambda 콘솔 → "테스트" 탭 → "새 이벤트 생성":

```json
{
  "version": "0",
  "id": "test-event-id",
  "detail-type": "Support Case Update",
  "source": "aws.support",
  "region": "us-east-1",
  "time": "2025-12-04T10:00:00Z",
  "detail": {
    "case-id": "case-test-123",
    "display-id": "99999",
    "communication-id": "",
    "event-name": "ResolveCase",
    "origin": ""
  }
}
```

### MOCK 모드 테스트

1. 환경 변수 `MOCK_MODE=true` 설정
2. 테스트 이벤트 실행
3. CloudWatch Logs 확인
4. S3 저장은 시뮬레이션만 됨 (실제 저장 안 됨)

### 실제 케이스로 테스트

1. 과거 해결된 케이스 ID 사용
2. 환경 변수 `MOCK_MODE=false` 설정
3. 테스트 이벤트의 `case-id`를 실제 케이스 ID로 변경
4. 실행 후 S3 버킷 확인

## 모니터링

### CloudWatch Logs

Lambda 콘솔 → "모니터링" 탭 → "CloudWatch에서 로그 보기"

로그 출력 예시:
```
📋 이벤트 수신: ResolveCase for case 12345 (case-xxx)
1️⃣ 케이스 정보 수집 중...
   케이스 제목: EC2 인스턴스 연결 불가
   대화 수: 5개
2️⃣ Bedrock Claude로 요약 생성 중...
   Bedrock 요약 완료 (시도 1/3)
3️⃣ S3에 저장 중...
   ✅ S3 저장 완료: s3://support-knowledge-base/technical/ec2/2025-12/12345.json
4️⃣ Bedrock Knowledge Base 동기화 중...
   ✅ KB 동기화 시작: job-xxxxx
✅ 케이스 처리 완료: 12345
```

## 트러블슈팅

### 에러: "케이스를 찾을 수 없습니다"
- 케이스 ID가 올바른지 확인
- Support API 권한 확인 (IAM 역할)

### 에러: "Bedrock API 호출 실패"
- Bedrock 권한 확인 (IAM 역할)
- 리전 확인 (ap-northeast-2)
- Claude 3 Sonnet 모델 액세스 활성화 확인

### 에러: "S3 저장 실패"
- 버킷 이름 확인 (환경 변수)
- S3 권한 확인 (IAM 역할)
- 버킷이 ap-northeast-2 리전에 있는지 확인

## 다음 단계

Lambda 함수 배포 완료 후:
1. EventBridge Rule과 연결 확인
2. 실제 케이스로 테스트
3. Bedrock KB 생성 및 환경 변수 업데이트
4. MOCK_MODE를 false로 변경
