#!/usr/bin/env python3
"""
AWS Support 케이스 마이그레이션 스크립트

과거 해결된 케이스를 일괄적으로 Knowledge Base에 추가합니다.
"""

import boto3
import json
import time
import sys
from datetime import datetime
from typing import Dict, Any, List

# Lambda 함수 코드 재사용을 위한 import
sys.path.append('../lambda')
from process_resolved_case import (
    get_case_details,
    summarize_with_bedrock,
    save_to_s3,
    trigger_kb_sync
)

# 설정
BUCKET_NAME = 'support-knowledge-base-20251204'
KB_ID = ''  # Bedrock KB ID (있으면 입력)
DS_ID = ''  # Data Source ID (있으면 입력)
START_DATE = '2023-01-01T00:00:00Z'  # 마이그레이션 시작 날짜
END_DATE = '2025-12-31T23:59:59Z'    # 마이그레이션 종료 날짜
RATE_LIMIT_DELAY = 1  # 각 케이스 처리 후 대기 시간 (초)

# AWS 클라이언트
support_client = boto3.client('support', region_name='us-east-1')
s3_client = boto3.client('s3', region_name='ap-northeast-2')

# 통계
stats = {
    'total': 0,
    'success': 0,
    'skipped': 0,
    'failed': 0,
    'errors': []
}


def get_resolved_cases(after_time: str, before_time: str = None) -> List[Dict[str, Any]]:
    """
    해결된 케이스 목록 조회
    
    Args:
        after_time: 시작 날짜 (ISO 8601 형식)
        before_time: 종료 날짜 (ISO 8601 형식, 선택사항)
    
    Returns:
        케이스 목록
    """
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
    """
    S3에 케이스가 이미 존재하는지 확인
    
    Args:
        display_id: 케이스 표시 번호
    
    Returns:
        존재 여부
    """
    try:
        # S3에서 모든 경로 검색 (category/service를 모르므로)
        response = s3_client.list_objects_v2(
            Bucket=BUCKET_NAME,
            Prefix='',
            MaxKeys=1000
        )
        
        for obj in response.get('Contents', []):
            if f"/{display_id}.json" in obj['Key']:
                return True
        
        return False
        
    except Exception as e:
        print(f"      ⚠️  S3 확인 실패: {str(e)}")
        return False


def process_case(case: Dict[str, Any]) -> bool:
    """
    개별 케이스 처리
    
    Args:
        case: 케이스 정보
    
    Returns:
        성공 여부
    """
    case_id = case['caseId']
    display_id = case.get('displayId', case_id)
    subject = case.get('subject', 'N/A')
    
    print(f"\n{'='*80}")
    print(f"📦 케이스 처리 중: {display_id}")
    print(f"   제목: {subject}")
    print(f"   케이스 ID: {case_id}")
    
    try:
        # 1. S3에 이미 존재하는지 확인
        print(f"   1️⃣ S3 중복 확인 중...")
        if check_case_exists_in_s3(display_id):
            print(f"   ⏭️  이미 존재함, 스킵")
            stats['skipped'] += 1
            return True
        
        # 2. 케이스 상세 정보 수집
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
        print(f"   에러 로그를 확인하세요.")


def main():
    """메인 함수"""
    print("="*80)
    print("🚀 AWS Support 케이스 마이그레이션 시작")
    print("="*80)
    print(f"버킷: {BUCKET_NAME}")
    print(f"기간: {START_DATE} ~ {END_DATE}")
    print(f"Rate Limit 대기: {RATE_LIMIT_DELAY}초")
    print("="*80)
    
    # 사용자 확인
    response = input("\n계속하시겠습니까? (y/n): ")
    if response.lower() != 'y':
        print("취소되었습니다.")
        return
    
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
            print(f"   ⏳ {RATE_LIMIT_DELAY}초 대기 중...")
            time.sleep(RATE_LIMIT_DELAY)
    
    # 3. 에러 로그 저장
    save_error_log()
    
    # 4. Bedrock KB 동기화 (선택사항)
    if KB_ID and DS_ID:
        print(f"\n🔄 Bedrock Knowledge Base 동기화 중...")
        try:
            trigger_kb_sync()
            print(f"   ✅ 동기화 시작됨")
        except Exception as e:
            print(f"   ⚠️  동기화 실패: {str(e)}")
    
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
