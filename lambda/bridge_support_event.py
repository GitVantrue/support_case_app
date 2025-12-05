#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Support Event Bridge Lambda (us-east-1)
AWS Support 이벤트를 ap-northeast-2의 Lambda로 전달
"""

import boto3
import json
import os

# ap-northeast-2 리전의 Lambda 클라이언트
lambda_client = boto3.client('lambda', region_name='ap-northeast-2')

# 타겟 Lambda 함수 이름
TARGET_LAMBDA = os.environ.get('TARGET_LAMBDA_ARN', 'process-resolved-case')


def lambda_handler(event, context):
    """
    us-east-1의 Support 이벤트를 ap-northeast-2 Lambda로 전달
    
    Args:
        event: EventBridge에서 전달된 Support 이벤트
        context: Lambda 실행 컨텍스트
    
    Returns:
        dict: 응답 상태
    """
    
    print(f"[수신] Support 이벤트: {json.dumps(event, ensure_ascii=False)}")
    
    # 이벤트 정보 추출
    case_id = event.get('detail', {}).get('case-id', 'Unknown')
    event_name = event.get('detail', {}).get('event-name', 'Unknown')
    
    print(f"[처리] Case ID: {case_id}, Event: {event_name}")
    
    try:
        # ap-northeast-2의 Lambda 비동기 호출
        response = lambda_client.invoke(
            FunctionName=TARGET_LAMBDA,
            InvocationType='Event',  # 비동기 호출
            Payload=json.dumps(event, ensure_ascii=False).encode('utf-8')
        )
        
        status_code = response['StatusCode']
        print(f"[성공] ap-northeast-2 Lambda 호출 완료: {status_code}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Event forwarded successfully',
                'case_id': case_id,
                'target_region': 'ap-northeast-2',
                'lambda_status': status_code
            })
        }
        
    except Exception as e:
        print(f"[에러] Lambda 호출 실패: {str(e)}")
        
        # 에러 발생 시에도 200 반환 (EventBridge 재시도 방지)
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Error forwarding event',
                'error': str(e),
                'case_id': case_id
            })
        }
