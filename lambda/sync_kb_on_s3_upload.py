#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S3 업로드 시 Bedrock Knowledge Base 자동 동기화

S3에 새 파일이 업로드되면 자동으로 KB 인덱싱을 트리거합니다.
"""

import os
import boto3
import json
from typing import Dict, Any

# 환경 변수
KB_ID = os.environ.get('KB_ID')
DS_ID = os.environ.get('DS_ID')

# AWS 클라이언트 (리전은 Lambda 실행 환경의 AWS_REGION 자동 사용)
bedrock_agent = boto3.client('bedrock-agent', region_name='ap-northeast-2')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda 핸들러 - S3 이벤트 처리
    
    Args:
        event: S3 이벤트
        context: Lambda 컨텍스트
    
    Returns:
        처리 결과
    """
    try:
        # S3 이벤트 파싱
        for record in event.get('Records', []):
            # S3 정보 추출
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            event_name = record['eventName']
            
            print(f"📁 S3 이벤트: {event_name}")
            print(f"   버킷: {bucket}")
            print(f"   파일: {key}")
            
            # PUT 이벤트만 처리 (새 파일 업로드)
            if 'ObjectCreated' in event_name:
                print(f"🔄 Bedrock KB 동기화 시작...")
                
                # KB 동기화 트리거
                response = bedrock_agent.start_ingestion_job(
                    knowledgeBaseId=KB_ID,
                    dataSourceId=DS_ID
                )
                
                ingestion_job_id = response['ingestionJob']['ingestionJobId']
                status = response['ingestionJob']['status']
                
                print(f"✅ 동기화 작업 시작됨")
                print(f"   Job ID: {ingestion_job_id}")
                print(f"   상태: {status}")
                
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'message': 'KB sync triggered successfully',
                        'ingestion_job_id': ingestion_job_id,
                        'status': status,
                        'file': key
                    })
                }
            else:
                print(f"⏭️  ObjectCreated 이벤트가 아님, 스킵")
                return {
                    'statusCode': 200,
                    'body': json.dumps({'message': 'Event skipped'})
                }
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'No records to process'})
        }
        
    except Exception as e:
        print(f"❌ 에러 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # 에러 발생해도 200 반환 (재시도 방지)
        return {
            'statusCode': 200,
            'body': json.dumps({
                'error': str(e),
                'message': 'Error occurred but returning 200 to prevent retries'
            })
        }
