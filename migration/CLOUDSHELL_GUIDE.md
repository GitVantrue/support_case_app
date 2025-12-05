# CloudShell에서 마이그레이션 실행 가이드

## 🚀 빠른 시작

### 1단계: CloudShell 열기
1. AWS Console 로그인
2. 상단 툴바에서 CloudShell 아이콘 클릭 (터미널 모양)
3. CloudShell이 시작될 때까지 대기 (약 30초)

### 2단계: 파일 업로드
1. CloudShell에서 "Actions" → "Upload file" 클릭
2. `migrate_cases_standalone.py` 파일 선택
3. 업로드 완료 대기

### 3단계: 설정 수정 (선택사항)
```bash
# 파일 편집
vi migrate_cases_standalone.py

# 또는 nano 사용
nano migrate_cases_standalone.py
```

수정할 항목:
- `BUCKET_NAME`: S3 버킷 이름
- `START_DATE`: 시작 날짜
- `END_DATE`: 종료 날짜
- `KB_ID`, `DS_ID`: Bedrock KB 정보 (있으면)

### 4단계: 백그라운드 실행

#### 방법 1: nohup 사용 (간단)
```bash
# 백그라운드 실행
nohup python3 migrate_cases_standalone.py > migration.log 2>&1 &

# 프로세스 ID 확인
echo $!

# 진행 상황 확인
tail -f migration.log

# Ctrl+C로 로그 보기 중단 (프로세스는 계속 실행됨)
```

#### 방법 2: screen 사용 (권장 - CloudShell 종료 후에도 계속 실행)
```bash
# screen 세션 시작
screen -S migration

# 스크립트 실행
python3 migrate_cases_standalone.py

# Detach (백그라운드로 전환): Ctrl+A, 그 다음 D
# 이제 CloudShell을 닫아도 계속 실행됩니다!

# 나중에 다시 연결
screen -r migration

# screen 세션 목록 확인
screen -ls
```

## 📊 진행 상황 확인

### 로그 파일 확인
```bash
# 실시간 로그 확인
tail -f migration.log

# 최근 50줄 확인
tail -n 50 migration.log

# 전체 로그 확인
cat migration.log

# 성공한 케이스 수 확인
grep "✅ 성공" migration.log | wc -l

# 실패한 케이스 수 확인
grep "❌" migration.log | wc -l
```

### 프로세스 확인
```bash
# 실행 중인 Python 프로세스 확인
ps aux | grep migrate_cases

# 프로세스 종료 (필요 시)
kill <PID>
```

## ⏸️ 중단 및 재시작

### 중단 방법
```bash
# 프로세스 ID 확인
ps aux | grep migrate_cases

# 프로세스 종료
kill <PID>

# 또는 강제 종료
kill -9 <PID>
```

### 재시작
```bash
# 동일한 명령어로 재시작
nohup python3 migrate_cases_standalone.py > migration.log 2>&1 &

# 이미 처리된 케이스는 자동으로 스킵됩니다
```

## 📁 결과 확인

### 완료 확인
```bash
# 로그 끝부분 확인
tail -n 20 migration.log

# 마이그레이션 완료 메시지 확인
grep "마이그레이션 완료" migration.log
```

### S3 확인
```bash
# S3에 저장된 파일 수 확인
aws s3 ls s3://support-knowledge-base-20251204/ --recursive --region ap-northeast-2 | wc -l

# 최근 저장된 파일 확인
aws s3 ls s3://support-knowledge-base-20251204/ --recursive --region ap-northeast-2 | tail -n 10
```

### 에러 로그 확인
```bash
# 에러 로그 파일 목록
ls -lh migration_errors_*.json

# 에러 로그 내용 확인
cat migration_errors_*.json | jq .
```

## 🔧 트러블슈팅

### 문제 1: CloudShell 세션 타임아웃
**증상**: CloudShell이 20분 후 자동 종료됨

**해결**: screen 사용
```bash
screen -S migration
python3 migrate_cases_standalone.py
# Ctrl+A, D로 detach
```

### 문제 2: 파일 업로드 실패
**증상**: 파일이 너무 큼

**해결**: 파일을 직접 생성
```bash
# 파일 생성
cat > migrate_cases_standalone.py << 'EOF'
[파일 내용 붙여넣기]
EOF

# 실행 권한 부여
chmod +x migrate_cases_standalone.py
```

### 문제 3: Python 버전 확인
```bash
# Python 버전 확인
python3 --version

# boto3 설치 확인
python3 -c "import boto3; print(boto3.__version__)"
```

### 문제 4: 권한 에러
**증상**: "Access Denied" 에러

**해결**: CloudShell은 현재 로그인한 사용자의 권한을 사용합니다.
- IAM 권한 확인 필요
- Support API, Bedrock, S3 권한 필요

## 💡 유용한 팁

### 1. 진행 상황 알림
```bash
# 완료 시 알림 (macOS/Linux)
nohup python3 migrate_cases_standalone.py > migration.log 2>&1 && echo "완료!" &
```

### 2. 로그 파일 다운로드
```bash
# CloudShell에서 로컬로 다운로드
# Actions → Download file → migration.log
```

### 3. 특정 기간만 마이그레이션
파일 수정:
```python
START_DATE = '2024-01-01T00:00:00Z'  # 2024년만
END_DATE = '2024-12-31T23:59:59Z'
```

### 4. Rate Limit 조정
케이스가 많으면:
```python
RATE_LIMIT_DELAY = 2  # 2초로 증가
```

## 📋 체크리스트

실행 전:
- [ ] CloudShell 열기
- [ ] `migrate_cases_standalone.py` 업로드
- [ ] 설정 확인 (BUCKET_NAME, 날짜)
- [ ] screen 세션 시작
- [ ] 스크립트 실행
- [ ] Detach (Ctrl+A, D)

실행 중:
- [ ] 로그 파일 주기적으로 확인
- [ ] 에러 발생 시 확인
- [ ] S3 파일 증가 확인

완료 후:
- [ ] 로그 파일 확인
- [ ] S3 파일 수 확인
- [ ] 에러 로그 확인
- [ ] Bedrock KB 인덱싱 확인

## 🎯 예상 시간

케이스 수에 따라:
- 10개: 약 3분
- 50개: 약 15분
- 100개: 약 30분
- 500개: 약 2.5시간

## 📞 다음 단계

마이그레이션 완료 후:
1. S3 버킷 확인
2. Bedrock KB 인덱싱 대기 (10-30분)
3. Slack Bot으로 검색 테스트
4. EventBridge Rule 활성화

## 🔗 참고 링크

- [AWS CloudShell 사용자 가이드](https://docs.aws.amazon.com/cloudshell/latest/userguide/)
- [screen 명령어 가이드](https://www.gnu.org/software/screen/manual/screen.html)
