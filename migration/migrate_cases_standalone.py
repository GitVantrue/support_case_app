#!/usr/bin/env python3
"""
AWS Support 케이스 마이그레이션 스크립트 (CloudShell용 독립 실행 버전)

과거 해결된 케이스를 일괄적으로 Knowledge Base에 추가합니다.
Lambda 함수 코드를 포함하여 단일 파일로 실행 가능합니다.
"""

import boto3
import json
import time
from datetime import datetime
from typing import Dict, Any, List

# ============================================================================
# 설정 (여기를 수정하세요)
# ============================================================================

BUCKET_NAME = 'support-knowledge-base-20251204'  # S3 버킷 이름
KB_ID = ''  # Bedrock KB ID (있으면 입력, 없으면 빈 문자열)
DS_ID = ''  # Data Source ID (있으면 입력, 없으면 빈 문자열)
START_DATE = '2023-01-01T00:00:00Z'  # 마이그레이션 시작 날짜
END_DATE = '2025-12-31T23:59:59Z'    # 마이그레이션 종료 날짜
RATE_LIMIT_DELAY = 1  # 각 케이스 처리 후 대기 시간 (초)

# ============================================================================
# AWS 클라이언트 초기화
# ============================================================================

s3_client = boto3.client('s3', region_name='ap-northeast-2')
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')
bedrock_agent = boto3.client('bedrock-agent', region_name='ap-northeast-2')
support_client = boto3.client('support', region_name='us-east-1')

# ============================================================================
# 통계
# ============================================================================

stats = {
    'total': 0,
    'success': 0,
    'skipped': 0,
    'failed': 0,
    'errors': []
}

# ============================================================================
# Lambda 함수 코드 (재사용)
# ============================================================================

def get_case_details(case_id: str) -> Dict[str, Any]:
    """Support API로 케이스 상세 정보 수집"""
    # 케이스 기본 정보 조회
    case_response = support_client.describe_cases(
        caseIdList=[case_id],
        includeResolvedCases=True,
        language='ko'
    )
    
    if not case_response['cases']:
        raise ValueError(f"케이스를 찾을 수 없습니다: {case_id}")
    
    case = case_response['cases'][0]
    
    # 대화 내역 조회
    comms_response = support_client.describe_communications(
        caseId=case_id,
        maxResults=100
    )
    
    communications = comms_response.get('communications', [])
    
    return {
        'case': case,
        'communications': communications
    }


def summarize_with_bedrock(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """Bedrock Claude를 사용하여 케이스 요약 및 분류"""
    case = case_data['case']
    communications = case_data['communications']
    
    # 케이스 내용 조합
    full_text = f"""
제목: {case.get('subject', 'N/A')}
심각도: {case.get('severityCode', 'normal')}
서비스 코드: {case.get('serviceCode', 'general')}
생성일: {case.get('timeCreated', 'N/A')}

대화 내역:
"""
    
    for comm in communications:
        submitted_by = comm.get('submittedBy', 'Unknown')
        body = comm.get('body', '')
        full_text += f"\n[{submitted_by}]\n{body}\n"
    
    # Bedrock Claude 프롬프트
    prompt = f"""다음 AWS Support 케이스를 분석하여 요약해주세요:

{full_text}

다음 JSON 형식으로만 응답하세요 (다른 텍스트 없이 JSON만):
{{
  "category": "technical, billing, account 중 하나",
  "service": "ec2, rds, lambda, s3, vpc, athena 등 AWS 서비스명 (소문자)",
  "question": "사용자의 핵심 질문을 1-2문장으로 요약",
  "answer": "AWS Support 엔지니어의 최종 답변을 1-2문장으로 요약",
  "solution": "문제 해결 방법을 3-5줄로 요약",
  "steps": ["구체적인 해결 단계1", "구체적인 해결 단계2", "구체적인 해결 단계3"],
  "tags": ["관련", "키워드", "태그"],
  "user_messages": ["사용자가 보낸 주요 메시지들"],
  "support_messages": ["AWS Support가 보낸 주요 답변들"]
}}
"""
    
    # Bedrock API 호출 (재시도 로직 포함)
    summary_json = invoke_bedrock_with_retry(prompt, max_retries=3)
    
    # 원본 정보 추가
    summary_json['case_id'] = case['caseId']
    summary_json['display_id'] = case.get('displayId', case['caseId'])
    summary_json['severity'] = case.get('severityCode', 'normal')
    summary_json['created_at'] = case.get('timeCreated', '')
    summary_json['resolved_at'] = case.get('timeResolved', datetime.now().isoformat())
    
    return summary_json


def invoke_bedrock_with_retry(prompt: str, max_retries: int = 3) -> Dict[str, Any]:
    """Bedrock API 호출 (재시도 로직 포함)"""
    for attempt in range(max_retries):
        try:
            response = bedrock_runtime.invoke_model(
                modelId='arn:aws:bedrock:us-east-1:370662402529:inference-profile/global.anthropic.claude-sonnet-4-5-20250929-v1:0',
                body=json.dumps({
                    'anthropic_version': 'bedrock-2023-05-31',
                    'max_tokens': 2000,
                    'messages': [
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ]
                })
            )
            
            result = json.loads(response['body'].read())
            content_text = result['content'][0]['text']
            
            # JSON 추출
            if '```json' in content_text:
                content_text = content_text.split('```json')[1].split('```')[0].strip()
            elif '```' in content_text:
                content_text = content_text.split('```')[1].split('```')[0].strip()
            
            summary = json.loads(content_text)
            return summary
            
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2
                time.sleep(wait_time)
            else:
                raise


def save_to_s3(summary: Dict[str, Any], display_id: str) -> str:
    """요약된 케이스를 S3에 저장"""
    category = summary.get('category', 'general')
    service = summary.get('service', 'general')
    date = datetime.now().strftime('%Y-%m')
    
    # S3 키 생성
    s3_key = f"{category}/{service}/{date}/{display_id}.json"
    
    # JSON 직렬화
    json_body = json.dumps(summary, ensure_ascii=False, indent=2)
    
    # S3에 저장
    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=s3_key,
        Body=json_body,
        ContentType='application/json',
        Metadata={
            'case-id': summary['case_id'],
            'display-id': display_id,
            'category': category,
            'service': service
        }
    )
    
    return s3_key


def trigger_kb_sync() -> None:
    """Bedrock Knowledge Base 인덱싱 작업 트리거"""
    if not KB_ID or not DS_ID:
        return
    
    try:
        response = bedrock_agent.start_ingestion_job(
            knowledgeBaseId=KB_ID,
            dataSourceId=DS_ID
        )
        ingestion_job_id = response['ingestionJob']['ingestionJobId']
        print(f"   ✅ KB 동기화 시작: {ingestion_job_id}")
    except Exception as e:
        print(f"   ⚠️  KB 동기화 실패: {str(e)}")

# ============================================================================
# 마이그레이션 로직
# ============================================================================

def get_resolved_cases(after_time: str, before_time: str = None) -> List[Dict[str, Any]]:
    """해결된 케이스 목록 조회"""
    print(f"\n📋 해결된 케이스 목록 조회 중...")
    print(f"   기간: {after_time} ~ {before_time or '현재'}")
    
    cases = []
    next_token = None
    
    while True:
        try:
            params = {
                'includeResolvedCases': True,
                'afterTime': after_time,
                'language': 'ko',
                'maxResults': 100
            }
            
            if before_time:
                params['beforeTime'] = before_time
            
            if next_token:
                params['nextToken'] = next_token
            
            response = support_client.describe_cases(**params)
            
            batch_cases = response.get('cases', [])
            cases.extend(batch_cases)
            
            print(f"   조회됨: {len(batch_cases)}개 (총 {len(cases)}개)")
            
            next_token = response.get('nextToken')
            if not next_token:
                break
                
        except Exception as e:
            print(f"   ⚠️  케이스 목록 조회 실패: {str(e)}")
            break
    
    # 해결된 케이스만 필터링
    resolved_cases = [c for c in cases if c.get('status') == 'resolved']
    print(f"\n✅ 총 {len(resolved_cases)}개의 해결된 케이스 발견")
    
    return resolved_cases


def check_case_exists_in_s3(display_id: str) -> bool:
    """S3에 케이스가 이미 존재하는지 확인"""
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=BUCKET_NAME, Prefix='')
        
        for page in pages:
            for obj in page.get('Contents', []):
                if f"/{display_id}.json" in obj['Key']:
                    return True
        
        return False
        
    except Exception as e:
        return False


def process_case(case: Dict[str, Any]) -> bool:
    """개별 케이스 처리"""
    case_id = case['caseId']
    display_id = case.get('displayId', case_id)
    subject = case.get('subject', 'N/A')
    
    print(f"\n{'='*80}")
    print(f"📦 케이스 처리 중: {display_id}")
    print(f"   제목: {subject}")
    print(f"   케이스 ID: {case_id}")
    
    try:
        # 1. S3 중복 확인
        print(f"   1️⃣ S3 중복 확인 중...")
        if check_case_exists_in_s3(display_id):
            print(f"   ⏭️  이미 존재함, 스킵")
            stats['skipped'] += 1
            return True
        
        # 2. 케이스 정보 수집
        print(f"   2️⃣ 케이스 정보 수집 중...")
        case_data = get_case_details(case_id)
        
        # 3. Bedrock 요약
        print(f"   3️⃣ Bedrock 요약 생성 중...")
        summary = summarize_with_bedrock(case_data)
        
        # 4. S3 저장
        print(f"   4️⃣ S3에 저장 중...")
        s3_key = save_to_s3(summary, display_id)
        
        print(f"   ✅ 성공: {s3_key}")
        stats['success'] += 1
        return True
        
    except Exception as e:
        error_msg = f"케이스 {display_id} 처리 실패: {str(e)}"
        print(f"   ❌ {error_msg}")
        stats['failed'] += 1
        stats['errors'].append({
            'case_id': case_id,
            'display_id': display_id,
            'error': str(e)
        })
        return False


def save_error_log():
    """에러 로그를 파일에 저장"""
    if stats['errors']:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'migration_errors_{timestamp}.json'
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(stats['errors'], f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 에러 로그 저장: {filename}")


def print_summary():
    """마이그레이션 결과 요약 출력"""
    print(f"\n{'='*80}")
    print(f"📊 마이그레이션 완료")
    print(f"{'='*80}")
    print(f"총 케이스 수:    {stats['total']}")
    print(f"✅ 성공:         {stats['success']}")
    print(f"⏭️  스킵:         {stats['skipped']}")
    print(f"❌ 실패:         {stats['failed']}")
    print(f"{'='*80}")
    
    if stats['failed'] > 0:
        print(f"\n⚠️  {stats['failed']}개 케이스 처리 실패")


def main():
    """메인 함수"""
    print("="*80)
    print("🚀 AWS Support 케이스 마이그레이션 시작")
    print("="*80)
    print(f"버킷: {BUCKET_NAME}")
    print(f"기간: {START_DATE} ~ {END_DATE}")
    print(f"Rate Limit 대기: {RATE_LIMIT_DELAY}초")
    print("="*80)
    
    # 1. 해결된 케이스 목록 조회
    cases = get_resolved_cases(START_DATE, END_DATE)
    stats['total'] = len(cases)
    
    if stats['total'] == 0:
        print("\n⚠️  처리할 케이스가 없습니다.")
        return
    
    # 2. 각 케이스 처리
    print(f"\n🔄 {stats['total']}개 케이스 처리 시작...\n")
    
    for i, case in enumerate(cases, 1):
        print(f"\n진행률: {i}/{stats['total']} ({i*100//stats['total']}%)")
        
        process_case(case)
        
        # Rate Limit 방지
        if i < stats['total']:
            time.sleep(RATE_LIMIT_DELAY)
    
    # 3. 에러 로그 저장
    save_error_log()
    
    # 4. Bedrock KB 동기화
    if KB_ID and DS_ID:
        print(f"\n🔄 Bedrock Knowledge Base 동기화 중...")
        trigger_kb_sync()
    
    # 5. 결과 요약
    print_summary()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단되었습니다.")
        print_summary()
        save_error_log()
    except Exception as e:
        print(f"\n\n❌ 예상치 못한 에러: {str(e)}")
        import traceback
        traceback.print_exc()
        save_error_log()
