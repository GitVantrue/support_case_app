# CloudShell 마이그레이션 - 초간단 가이드

## 🚀 3단계로 끝내기

### 1단계: CloudShell 열기
1. AWS Console 로그인
2. 화면 상단 오른쪽에 있는 **터미널 아이콘** 클릭
3. CloudShell이 열릴 때까지 대기 (30초 정도)

### 2단계: 파일 업로드
1. CloudShell 화면에서 **"Actions"** 버튼 클릭
2. **"Upload file"** 선택
3. `migrate_cases_standalone.py` 파일 선택
4. 업로드 완료 대기

### 3단계: 실행
CloudShell에 다음 명령어를 **복사해서 붙여넣기**:

```bash
nohup python3 migrate_cases_standalone.py > migration.log 2>&1 &
```

Enter 키를 누르면 백그라운드에서 실행됩니다!

## 📊 진행 상황 확인

실행 후 진행 상황을 보려면:

```bash
tail -f migration.log
```

- 실시간으로 로그가 보입니다
- 멈추려면 `Ctrl+C` (프로그램은 계속 실행됨)

## ⏸️ 중단하고 싶을 때

```bash
# 1. 실행 중인 프로세스 찾기
ps aux | grep migrate_cases

# 2. 프로세스 번호(PID) 확인 (두 번째 숫자)
# 예: cloudshell-user  12345  ...

# 3. 중단
kill 12345
```

## ✅ 완료 확인

### 로그 끝부분 보기
```bash
tail -n 30 migration.log
```

"📊 마이그레이션 완료" 메시지가 보이면 완료!

### S3에 저장된 파일 확인
```bash
aws s3 ls s3://support-knowledge-base-20251204/ --recursive --region ap-northeast-2 | wc -l
```

## 💡 자주 묻는 질문

### Q: CloudShell을 닫으면 어떻게 되나요?
**A**: 괜찮습니다! `nohup`으로 실행했기 때문에 계속 실행됩니다.

### Q: 다시 CloudShell을 열면?
**A**: 다음 명령어로 로그를 확인할 수 있습니다:
```bash
tail -f migration.log
```

### Q: 얼마나 걸리나요?
**A**: 케이스 수에 따라 다릅니다:
- 10개: 약 3분
- 50개: 약 15분
- 100개: 약 30분

### Q: 에러가 발생하면?
**A**: 로그 파일을 확인하세요:
```bash
cat migration.log | grep "❌"
```

## 🎯 전체 명령어 요약

```bash
# 1. 파일 업로드 후 실행
nohup python3 migrate_cases_standalone.py > migration.log 2>&1 &

# 2. 진행 상황 확인
tail -f migration.log

# 3. 완료 확인
tail -n 30 migration.log

# 4. S3 파일 수 확인
aws s3 ls s3://support-knowledge-base-20251204/ --recursive --region ap-northeast-2 | wc -l
```

## 📝 명령어 설명

### `nohup python3 migrate_cases_standalone.py > migration.log 2>&1 &`

이 명령어가 하는 일:
- `nohup`: CloudShell을 닫아도 계속 실행
- `python3 migrate_cases_standalone.py`: 스크립트 실행
- `> migration.log`: 출력을 파일에 저장
- `2>&1`: 에러도 같은 파일에 저장
- `&`: 백그라운드에서 실행

### `tail -f migration.log`

이 명령어가 하는 일:
- 로그 파일을 실시간으로 보여줌
- 새로운 내용이 추가되면 자동으로 표시
- `Ctrl+C`로 중단 (프로그램은 계속 실행)

## 🔥 바로 시작하기

1. AWS Console → CloudShell 열기
2. Actions → Upload file → `migrate_cases_standalone.py`
3. 다음 명령어 실행:
   ```bash
   nohup python3 migrate_cases_standalone.py > migration.log 2>&1 &
   tail -f migration.log
   ```

끝! 이제 진행 상황을 보면서 기다리시면 됩니다. 🎉
