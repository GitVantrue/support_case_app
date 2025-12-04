"""
AWS Support 케이스 해결 시 자동으로 Knowledge Base에 동기화하는 Lambda 함수

EventBridge에서 ResolveCase 이벤트를 수신하여:
1. Support API로 케이스 정보 수집
2. Bedrock Claude로 요약 및 분류
3. S3에 구조화된 JSON 저장
4. Bedrock Knowledge Base 인덱싱 트리거
"""

import boto3
import json
import os
from datetime import datetime
from typing import Dict, Any, List

# 환경 변수
KB_ID = os.environ.get('KB_ID', '')
DS_ID = os.environ.get('DS_ID', '')
BUCKET_NAME = os.environ.get('BUCKET_NAME', 'support-knowledge-base')
MOCK_MODE = os.environ.get('MOCK_MODE', 'false').lower() == 'true'

# AWS 클라이언트 초기화
s3_client = boto3.client('s3', region_name='ap-northeast-2')
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')  # Bedrock은 us-east-1 사용
bedrock_agent = boto3.client('bedrock-agent', region_name='ap-northeast-2')
support_client = boto3.client('support', region_name='us-east-1')  # Support API는 us-east-1


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda 핸들러 함수
    
    Args:
        event: EventBridge에서 전달된 Support Case Update 이벤트
        context: Lambda 실행 컨텍스트
    
    Returns:
        처리 결과 딕셔너리
    """
    try:
        # 이벤트 정보 추출
        case_id = event['detail']['case-id']
        display_id = event['detail']['display-id']
        event_name = event['detail']['event-name']
        
        print(f"📋 이벤트 수신: {event_name} for case {display_id} ({case_id})")
        
        # ResolveCase 이벤트만 처리
        if event_name != 'ResolveCase':
            print(f"⏭️  ResolveCase 이벤트가 아님, 스킵")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Not a ResolveCase event'})
            }
        
        # MOCK 모드 확인
        if MOCK_MODE:
            print("⚠️  MOCK_MODE 활성화 - 테스트 모드로 실행")
        
        # 케이스 처리
        result = process_resolved_case(case_id, display_id)
        
        print(f"✅ 케이스 처리 완료: {display_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Successfully processed case',
                'case_id': case_id,
                'display_id': display_id,
                'result': result
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        print(f"❌ 에러 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'case_id': event.get('detail', {}).get('case-id', 'unknown')
            })
        }


def process_resolved_case(case_id: str, display_id: str) -> Dict[str, Any]:
    """
    해결된 케이스를 처리하여 Knowledge Base에 저장
    
    Args:
        case_id: AWS Support 케이스 ID
        display_id: 사용자에게 표시되는 케이스 번호
    
    Returns:
        처리 결과 딕셔너리
    """
    # 1. 케이스 정보 수집
    print(f"1️⃣ 케이스 정보 수집 중...")
    case_data = get_case_details(case_id)
    
    # 2. Bedrock으로 요약 및 분류
    print(f"2️⃣ Bedrock Claude로 요약 생성 중...")
    summary = summarize_with_bedrock(case_data)
    
    # 3. S3에 저장
    print(f"3️⃣ S3에 저장 중...")
    s3_key = save_to_s3(summary, display_id)
    
    # 4. Bedrock KB 동기화 (MOCK 모드가 아닐 때만)
    if not MOCK_MODE and KB_ID and DS_ID:
        print(f"4️⃣ Bedrock Knowledge Base 동기화 중...")
        trigger_kb_sync()
    else:
        print(f"4️⃣ Bedrock KB 동기화 스킵 (MOCK_MODE 또는 KB_ID/DS_ID 미설정)")
    
    return {
        's3_key': s3_key,
        'category': summary['category'],
        'service': summary['service']
    }


def get_case_details(case_id: str) -> Dict[str, Any]:
    """
    Support API로 케이스 상세 정보 수집
    
    Args:
        case_id: AWS Support 케이스 ID
    
    Returns:
        케이스 정보 및 대화 내역을 포함한 딕셔너리
    """
    # MOCK 모드: 테스트용 가짜 데이터 반환
    if MOCK_MODE and (case_id.startswith('case-test-') or not case_id.startswith('case-')):
        print(f"   [MOCK] 테스트 케이스 데이터 생성: {case_id}")
        return {
            'case': {
                'caseId': case_id,
                'displayId': '99999',
                'subject': '[테스트] EC2 인스턴스 연결 불가',
                'status': 'resolved',
                'serviceCode': 'amazon-ec2',
                'severityCode': 'high',
                'timeCreated': '2025-12-04T10:00:00Z',
                'timeResolved': '2025-12-04T15:00:00Z'
            },
            'communications': [
                {
                    'caseId': case_id,
                    'body': '사용자: ap-northeast-2 리전의 EC2 인스턴스 i-1234567890에 SSH로 연결할 수 없습니다.',
                    'submittedBy': 'user@example.com',
                    'timeCreated': '2025-12-04T10:05:00Z'
                },
                {
                    'caseId': case_id,
                    'body': 'AWS Support: 보안 그룹 인바운드 규칙을 확인해주세요. SSH 포트(22)가 열려있는지 확인이 필요합니다.',
                    'submittedBy': 'support@aws.amazon.com',
                    'timeCreated': '2025-12-04T11:00:00Z'
                },
                {
                    'caseId': case_id,
                    'body': '사용자: 보안 그룹에 SSH 포트를 추가했더니 연결되었습니다. 감사합니다!',
                    'submittedBy': 'user@example.com',
                    'timeCreated': '2025-12-04T14:30:00Z'
                }
            ]
        }
    
    # 실제 Support API 호출
    # 케이스 기본 정보 조회
    case_response = support_client.describe_cases(
        caseIdList=[case_id],
        includeResolvedCases=True,
        language='ko'  # 한국어 응답
    )
    
    if not case_response['cases']:
        raise ValueError(f"케이스를 찾을 수 없습니다: {case_id}")
    
    case = case_response['cases'][0]
    
    # 대화 내역 조회
    comms_response = support_client.describe_communications(
        caseId=case_id,
        maxResults=100  # 최대 100개 대화
    )
    
    communications = comms_response.get('communications', [])
    
    print(f"   케이스 제목: {case.get('subject', 'N/A')}")
    print(f"   대화 수: {len(communications)}개")
    
    return {
        'case': case,
        'communications': communications
    }


def summarize_with_bedrock(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Bedrock Claude를 사용하여 케이스 요약 및 분류
    
    Args:
        case_data: 케이스 정보 및 대화 내역
    
    Returns:
        요약된 케이스 정보 (category, service, question, solution, steps, tags 포함)
    """
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
  "service": "ec2, rds, lambda, s3, vpc 등 AWS 서비스명 (소문자)",
  "question": "핵심 질문을 1-2문장으로 요약",
  "solution": "해결 방법을 3-5줄로 요약",
  "steps": ["해결 단계1", "해결 단계2", "해결 단계3"],
  "tags": ["관련", "키워드", "태그"]
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
    """
    Bedrock API 호출 (재시도 로직 포함)
    
    Args:
        prompt: Bedrock에 전달할 프롬프트
        max_retries: 최대 재시도 횟수
    
    Returns:
        Bedrock 응답 JSON
    """
    import time
    
    for attempt in range(max_retries):
        try:
            # Claude Sonnet 4.5 글로벌 inference profile 사용
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
            
            # 응답 파싱
            result = json.loads(response['body'].read())
            content_text = result['content'][0]['text']
            
            # JSON 추출 (```json ``` 제거)
            if '```json' in content_text:
                content_text = content_text.split('```json')[1].split('```')[0].strip()
            elif '```' in content_text:
                content_text = content_text.split('```')[1].split('```')[0].strip()
            
            summary = json.loads(content_text)
            
            print(f"   Bedrock 요약 완료 (시도 {attempt + 1}/{max_retries})")
            return summary
            
        except Exception as e:
            print(f"   ⚠️  Bedrock API 호출 실패 (시도 {attempt + 1}/{max_retries}): {str(e)}")
            
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2  # 2초, 4초, 6초
                print(f"   {wait_time}초 후 재시도...")
                time.sleep(wait_time)
            else:
                raise


def save_to_s3(summary: Dict[str, Any], display_id: str) -> str:
    """
    요약된 케이스를 S3에 저장
    
    Args:
        summary: 요약된 케이스 정보
        display_id: 케이스 표시 번호
    
    Returns:
        S3 키 (경로)
    """
    category = summary.get('category', 'general')
    service = summary.get('service', 'general')
    date = datetime.now().strftime('%Y-%m')
    
    # S3 키 생성: {category}/{service}/{YYYY-MM}/{display-id}.json
    s3_key = f"{category}/{service}/{date}/{display_id}.json"
    
    # JSON 직렬화
    json_body = json.dumps(summary, ensure_ascii=False, indent=2)
    
    if MOCK_MODE:
        print(f"   [MOCK] S3 저장 시뮬레이션: s3://{BUCKET_NAME}/{s3_key}")
        print(f"   [MOCK] 데이터 크기: {len(json_body)} bytes")
    else:
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
        print(f"   ✅ S3 저장 완료: s3://{BUCKET_NAME}/{s3_key}")
    
    return s3_key


def trigger_kb_sync() -> None:
    """
    Bedrock Knowledge Base 인덱싱 작업 트리거
    """
    try:
        response = bedrock_agent.start_ingestion_job(
            knowledgeBaseId=KB_ID,
            dataSourceId=DS_ID
        )
        
        ingestion_job_id = response['ingestionJob']['ingestionJobId']
        print(f"   ✅ KB 동기화 시작: {ingestion_job_id}")
        
    except Exception as e:
        print(f"   ⚠️  KB 동기화 실패: {str(e)}")
        # KB 동기화 실패는 치명적이지 않으므로 예외를 발생시키지 않음
