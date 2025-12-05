#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import boto3
import json
import time
from datetime import datetime

# 설정
BUCKET_NAME = 'support-knowledge-base-20251204'
KB_ID = ''
DS_ID = ''
START_DATE = '2023-01-01T00:00:00Z'
END_DATE = '2025-12-31T23:59:59Z'
RATE_LIMIT_DELAY = 1

# AWS 클라이언트
s3_client = boto3.client('s3', region_name='ap-northeast-2')
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')
bedrock_agent = boto3.client('bedrock-agent', region_name='ap-northeast-2')
support_client = boto3.client('support', region_name='us-east-1')

stats = {'total': 0, 'success': 0, 'skipped': 0, 'failed': 0, 'errors': []}

def get_case_details(case_id):
    case_response = support_client.describe_cases(
        caseIdList=[case_id],
        includeResolvedCases=True,
        language='ko'
    )
    if not case_response['cases']:
        raise ValueError(f"Case not found: {case_id}")
    case = case_response['cases'][0]
    comms_response = support_client.describe_communications(caseId=case_id, maxResults=100)
    return {'case': case, 'communications': comms_response.get('communications', [])}

def summarize_with_bedrock(case_data):
    case = case_data['case']
    communications = case_data['communications']
    full_text = f"Title: {case.get('subject', 'N/A')}\nSeverity: {case.get('severityCode', 'normal')}\n\nConversations:\n"
    for comm in communications:
        full_text += f"\n[{comm.get('submittedBy', 'Unknown')}]\n{comm.get('body', '')}\n"
    
    prompt = f"""Analyze this AWS Support case and summarize in JSON format only:

{full_text}

Return ONLY this JSON (no other text):
{{
  "category": "technical, billing, or account",
  "service": "ec2, rds, lambda, s3, vpc, athena, etc (lowercase)",
  "question": "User's main question in 1-2 sentences",
  "answer": "AWS Support's final answer in 1-2 sentences",
  "solution": "Problem resolution in 3-5 lines",
  "steps": ["Step 1", "Step 2", "Step 3"],
  "tags": ["keyword1", "keyword2"],
  "user_messages": ["User message 1"],
  "support_messages": ["Support message 1"]
}}"""
    
    for attempt in range(3):
        try:
            response = bedrock_runtime.invoke_model(
                modelId='arn:aws:bedrock:us-east-1:370662402529:inference-profile/global.anthropic.claude-sonnet-4-5-20250929-v1:0',
                body=json.dumps({
                    'anthropic_version': 'bedrock-2023-05-31',
                    'max_tokens': 2000,
                    'messages': [{'role': 'user', 'content': prompt}]
                })
            )
            result = json.loads(response['body'].read())
            content_text = result['content'][0]['text']
            if '```json' in content_text:
                content_text = content_text.split('```json')[1].split('```')[0].strip()
            elif '```' in content_text:
                content_text = content_text.split('```')[1].split('```')[0].strip()
            summary = json.loads(content_text)
            summary['case_id'] = case['caseId']
            summary['display_id'] = case.get('displayId', case['caseId'])
            summary['severity'] = case.get('severityCode', 'normal')
            summary['created_at'] = case.get('timeCreated', '')
            summary['resolved_at'] = case.get('timeResolved', datetime.now().isoformat())
            return summary
        except Exception as e:
            if attempt < 2:
                time.sleep((attempt + 1) * 2)
            else:
                raise

def save_to_s3(summary, display_id):
    category = summary.get('category', 'general')
    service = summary.get('service', 'general')
    date = datetime.now().strftime('%Y-%m')
    s3_key = f"{category}/{service}/{date}/{display_id}.json"
    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=s3_key,
        Body=json.dumps(summary, ensure_ascii=False, indent=2),
        ContentType='application/json'
    )
    return s3_key

def check_case_exists_in_s3(display_id):
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=''):
            for obj in page.get('Contents', []):
                if f"/{display_id}.json" in obj['Key']:
                    return True
        return False
    except:
        return False

def get_resolved_cases(after_time, before_time=None):
    print(f"\nFetching resolved cases...")
    print(f"   Period: {after_time} ~ {before_time or 'now'}")
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
            batch = response.get('cases', [])
            cases.extend(batch)
            print(f"   Found: {len(batch)} (total {len(cases)})")
            next_token = response.get('nextToken')
            if not next_token:
                break
        except Exception as e:
            print(f"   Error: {e}")
            break
    resolved = [c for c in cases if c.get('status') == 'resolved']
    print(f"\nTotal resolved cases: {len(resolved)}")
    return resolved

def process_case(case):
    case_id = case['caseId']
    display_id = case.get('displayId', case_id)
    subject = case.get('subject', 'N/A')
    print(f"\n{'='*80}")
    print(f"Processing: {display_id}")
    print(f"   Title: {subject}")
    print(f"   Case ID: {case_id}")
    try:
        print(f"   1. Checking S3...")
        if check_case_exists_in_s3(display_id):
            print(f"   Skip: already exists")
            stats['skipped'] += 1
            return True
        print(f"   2. Fetching case details...")
        case_data = get_case_details(case_id)
        print(f"   3. Summarizing with Bedrock...")
        summary = summarize_with_bedrock(case_data)
        print(f"   4. Saving to S3...")
        s3_key = save_to_s3(summary, display_id)
        print(f"   Success: {s3_key}")
        stats['success'] += 1
        return True
    except Exception as e:
        print(f"   Error: {e}")
        stats['failed'] += 1
        stats['errors'].append({'case_id': case_id, 'display_id': display_id, 'error': str(e)})
        return False

def main():
    print("="*80)
    print("AWS Support Case Migration")
    print("="*80)
    print(f"Bucket: {BUCKET_NAME}")
    print(f"Period: {START_DATE} ~ {END_DATE}")
    print("="*80)
    
    cases = get_resolved_cases(START_DATE, END_DATE)
    stats['total'] = len(cases)
    
    if stats['total'] == 0:
        print("\nNo cases to process.")
        return
    
    print(f"\nProcessing {stats['total']} cases...\n")
    
    for i, case in enumerate(cases, 1):
        print(f"\nProgress: {i}/{stats['total']} ({i*100//stats['total']}%)")
        process_case(case)
        if i < stats['total']:
            time.sleep(RATE_LIMIT_DELAY)
    
    if stats['errors']:
        with open(f"migration_errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 'w') as f:
            json.dump(stats['errors'], f, indent=2)
    
    print(f"\n{'='*80}")
    print(f"Migration Complete")
    print(f"{'='*80}")
    print(f"Total:    {stats['total']}")
    print(f"Success:  {stats['success']}")
    print(f"Skipped:  {stats['skipped']}")
    print(f"Failed:   {stats['failed']}")
    print(f"{'='*80}")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
