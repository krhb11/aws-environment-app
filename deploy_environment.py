"""Run in authenticated AWS CloudShell. No application or document data is loaded."""
import io
import json
import sys
import time
import zipfile
from pathlib import Path
import boto3
from botocore.exceptions import ClientError

STACK='codex-env-20261125'
REGION='ap-northeast-2'

def file(name):
    if sys.argv[0].endswith('.zip'):
        with zipfile.ZipFile(sys.argv[0]) as z:return z.read(name)
    return (Path(__file__).parent/name).read_bytes()

def main():
    cf=boto3.client('cloudformation',region_name=REGION)
    template=json.loads(file('cloudformation.json'))
    cf.validate_template(TemplateBody=json.dumps(template))
    try:
        cf.update_stack(StackName=STACK,TemplateBody=json.dumps(template),Capabilities=['CAPABILITY_IAM'])
        print('UPDATE_STARTED',STACK,flush=True)
    except ClientError as exc:
        if 'No updates are to be performed' not in str(exc):raise
        print('NO_INFRASTRUCTURE_CHANGES',flush=True)
    while True:
        stack=cf.describe_stacks(StackName=STACK)['Stacks'][0]
        status=stack['StackStatus']
        print('STACK_STATUS',status,flush=True)
        if status=='UPDATE_COMPLETE':break
        if 'ROLLBACK' in status or 'FAILED' in status:
            for event in cf.describe_stack_events(StackName=STACK)['StackEvents'][:15]:
                print(event['LogicalResourceId'],event['ResourceStatus'],event.get('ResourceStatusReason',''))
            raise RuntimeError(status)
        time.sleep(15)
    outputs={o['OutputKey']:o['OutputValue'] for o in stack['Outputs']}
    s3=boto3.client('s3',region_name=REGION)
    s3.put_object(Bucket=outputs['WebBucketName'],Key='index.html',Body=file('index.html'),ContentType='text/html; charset=utf-8',CacheControl='no-cache')
    # These empty prefixes establish locations without adding book data.
    for prefix in ['raw/','processed/']:
        s3.put_object(Bucket=outputs['DataBucketName'],Key=prefix,Body=b'')
    result={'scope':'development-environment-only','stack_status':status,'region':REGION,'outputs':outputs}
    result['s3_public_access']={key:s3.get_public_access_block(Bucket=outputs[key])['PublicAccessBlockConfiguration'] for key in ['WebBucketName','DataBucketName']}
    vectors=boto3.client('s3vectors',region_name=REGION)
    result['vector_index']=vectors.get_index(indexArn=outputs['VectorIndexArn'])['index']
    result['vector_count']=len(vectors.list_vectors(indexArn=outputs['VectorIndexArn'],maxResults=1).get('vectors',[]))
    response=boto3.client('lambda',region_name=REGION).invoke(FunctionName=outputs['FunctionName'],Payload=json.dumps({'action':'model_access_check'}).encode())
    result['model_access']=json.loads(response['Payload'].read())
    result['model_access_function_error']=response.get('FunctionError')
    # Export only resource metadata and smoke-test results, never credentials.
    payload=json.dumps(result,ensure_ascii=False,indent=2,default=str).encode()
    Path('rag-environment-result.json').write_bytes(payload)
    s3.put_object(Bucket=outputs['WebBucketName'],Key='environment-result.json',Body=payload,ContentType='application/json',CacheControl='no-store')
    print('RESULT',json.dumps(result,ensure_ascii=False,default=str),flush=True)
    print('WEBSITE',outputs['WebsiteUrl'],flush=True)

if __name__=='__main__':main()
