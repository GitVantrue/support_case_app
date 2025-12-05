# Lambda 함수 테스트 가이드

## 현재 상태
✅ MOCK 모드 테스트 완료 (가짜 데이터)
- 테스트 케이스 ID: case-test-123
- 실행 시간: 6.3초
- Bedrock 요약: 성공
- 결과: technical/ec2/2025-12/99999.json

## 다음 테스트 단계

### 2단계: 실제 Support 케이스로 테스트

#### 준비사항
1. 과거에 해결된 실제 Support 케이스 ID 확인
2. Lambda 환경 변수 설정:
   - `MOCK_MODE=false` (실제 API 호출)
   - `BUCKET_NAME=support-knowledge-base-20251204` (실제 버킷명)

#### 실제 케이스 ID 확인 방법

**방법 1: AWS CLI로 확인**
```bash
# 최근 해결된 케이스 목록 조회
aws support describe-cases \
  --include-resolved-cases \
  --max-results 10 \
  --region us-east-1

# 출력 예시에서 caseId와 displayId 확인
# "caseId": "case-986719740728-muen-2022-c5a3adcdde2ee229"
# "displayId": "12345"
```

**방법 2: AWS Support 콘솔에서 확인**
1. AWS Console → Support → Support Center
2. "Case history" 클릭
3. 해결된 케이스 선택
4. URL에서 케이스 ID 확인: `...?caseId=case-xxx...`

#### 테스트 실행

1. **Lambda 환경 변수 업데이트**
   ```
   MOCK_MODE = false
   BUCKET_NAME = support-knowledge-base-20251204
   ```

2. **테스트 이벤트 생성**
   - Lambda 콘솔 → "테스트" 탭
   - `test_events/real_case_test.json` 내용 사용
   - `case-id`와 `display-id`를 실제 값으로 변경

3. **실행 및 확인**
   ```bash
   # CloudWatch Logs 확인
   # 예상 출력:
   # 📋 이벤트 수신: ResolveCase for case 12345
   # 1️⃣ 케이스 정보 수집 중...
   #    케이스 제목: [실제 케이스 제목]
   #    대화 수: X개
   # 2️⃣ Bedrock Claude로 요약 생성 중...
   #    Bedrock 요약 완료
   # 3️⃣ S3에 저장 중...
   #    ✅ S3 저장 완료: s3://...
   # 4️⃣ Bedrock KB 동기화 스킵 (KB_ID 미설정)
   ```

4. **S3 버킷 확인**
   ```bash
   # S3에 파일이 저장되었는지 확인
   aws s3 ls s3://support-knowledge-base-20251204/ --recursive
   
   # 저장된 JSON 파일 다운로드 및 확인
   aws s3 cp s3://support-knowledge-base-20251204/technical/ec2/2025-12/12345.json - | jq .
   ```

### 3단계: Bedrock KB 동기화 테스트

Bedrock Knowledge Base를 생성한 후:

1. **환경 변수 추가**
   ```
   KB_ID = kb-xxxxxxxxxxxxx
   DS_ID = xxxxxxxxxxxxx
   ```

2. **동일한 테스트 이벤트로 재실행**

3. **KB 인덱싱 확인**
   ```bash
   # 인덱싱 작업 상태 확인
   aws bedrock-agent list-ingestion-jobs \
     --knowledge-base-id kb-xxxxxxxxxxxxx \
     --data-source-id xxxxxxxxxxxxx \
     --region ap-northeast-2
   ```

### 4단계: EventBridge 통합 테스트

실제 Support 케이스를 해결하여 EventBridge가 Lambda를 트리거하는지 확인:

1. **EventBridge Rule 확인**
   ```bash
   aws events describe-rule \
     --name SupportCaseUpdateRule \
     --region us-east-1
   ```

2. **테스트 케이스 생성 및 해결**
   - AWS Support Console에서 테스트 케이스 생성
   - 케이스를 "Resolved" 상태로 변경
   - 5-10분 후 Lambda CloudWatch Logs 확인

3. **EventBridge 이벤트 확인**
   ```bash
   # CloudWatch Logs Insights 쿼리
   fields @timestamp, @message
   | filter @message like /ResolveCase/
   | sort @timestamp desc
   | limit 20
   ```

## 테스트 체크리스트

- [x] MOCK 모드 테스트 (가짜 데이터)
- [ ] 실제 케이스 ID로 테스트 (Support API 호출)
- [ ] S3 저장 확인
- [ ] Bedrock KB 동기화 확인
- [ ] EventBridge → Lambda 자동 트리거 확인
- [ ] 에러 케이스 테스트 (존재하지 않는 케이스 ID)
- [ ] 재시도 로직 테스트 (Bedrock API 실패 시뮬레이션)

## 예상 결과

### 성공 시 S3 JSON 구조
```json
{
  "category": "technical",
  "service": "ec2",
  "question": "EC2 인스턴스에 SSH로 연결할 수 없음",
  "answer": "보안 그룹 인바운드 규칙에 SSH 포트를 추가하여 해결",
  "solution": "보안 그룹 설정을 확인하고 SSH 포트(22)를 인바운드 규칙에 추가",
  "steps": [
    "EC2 콘솔에서 인스턴스의 보안 그룹 확인",
    "보안 그룹의 인바운드 규칙 편집",
    "SSH(22) 포트 추가, 소스를 내 IP로 제한",
    "변경 사항 저장 후 SSH 재시도"
  ],
  "tags": ["ec2", "ssh", "security-group", "connectivity"],
  "user_messages": ["..."],
  "support_messages": ["..."],
  "case_id": "case-986719740728-muen-2022-c5a3adcdde2ee229",
  "display_id": "12345",
  "severity": "high",
  "created_at": "2025-12-04T10:00:00Z",
  "resolved_at": "2025-12-04T15:30:00Z"
}
```

## 트러블슈팅

### 문제: "케이스를 찾을 수 없습니다"
**원인**: 케이스 ID가 잘못되었거나 Support API 권한 부족
**해결**:
1. 케이스 ID 형식 확인 (case-로 시작)
2. Lambda IAM 역할에 `support:DescribeCases` 권한 추가
3. 케이스가 실제로 존재하는지 AWS CLI로 확인

### 문제: "Bedrock API 호출 실패"
**원인**: Bedrock 권한 부족 또는 모델 액세스 미활성화
**해결**:
1. Lambda IAM 역할에 `bedrock:InvokeModel` 권한 추가
2. Bedrock Console → Model access → Claude 3 Sonnet 활성화
3. 리전 확인 (us-east-1)

### 문제: "S3 저장 실패"
**원인**: S3 권한 부족 또는 버킷 이름 오류
**해결**:
1. Lambda IAM 역할에 `s3:PutObject` 권한 추가
2. 환경 변수 `BUCKET_NAME` 확인
3. 버킷이 ap-northeast-2 리전에 있는지 확인

### 문제: "타임아웃"
**원인**: Lambda 실행 시간 초과 (기본 3초)
**해결**:
1. Lambda 타임아웃을 120초로 증가
2. 메모리를 512MB로 증가 (현재 128MB)

## 성능 최적화

현재 실행 시간: 6.3초 (MOCK 모드)
예상 실행 시간: 10-15초 (실제 API 호출)

**개선 방안**:
1. Lambda 메모리 증가 → 512MB (CPU도 함께 증가)
2. Bedrock 프롬프트 최적화 → 토큰 수 감소
3. 병렬 처리 → Support API와 S3 저장 동시 실행 (향후)

## 다음 단계

Lambda 테스트 완료 후:
1. ✅ Task 2.6 완료 표시
2. → Phase 3: Slack Bot 구현 시작
3. → Phase 5: 마이그레이션 스크립트 작성
