import boto3
import os
import time
from dotenv import load_dotenv

load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN")
REGION = os.getenv("REGION")

session = boto3.Session(
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    aws_session_token=AWS_SESSION_TOKEN,
    region_name=REGION
)

ec2_client = session.client("ec2")
ec2_resource = session.resource("ec2")
s3_client = session.client("s3")
sqs_client = session.client("sqs")

KEY_NAME = "myKey"
SECURITY_GROUP_NAME = "MyWebServerGroup"
BUCKET_NAME = "cse546-bucket-" + str(int(time.time()))
QUEUE_NAME = "cse546-test-queue.fifo"


# Step 1: Get latest Amazon Linux 2 AMI
def get_latest_ami():
    response = ec2_client.describe_images(
        Owners=["amazon"],
        Filters=[
            {"Name": "name", "Values": ["amzn2-ami-hvm-*-x86_64-gp2"]},
            {"Name": "state", "Values": ["available"]}
        ]
    )
    images = sorted(response["Images"], key=lambda x: x["CreationDate"], reverse=True)
    return images[0]["ImageId"]


AMI_ID = get_latest_ami()
print(f"✅ Latest Amazon Linux AMI ID fetched: {AMI_ID}")


# Step 2: Launch EC2 instance
def get_security_group_id():
    response = ec2_client.describe_security_groups(
        Filters=[{"Name": "group-name", "Values": [SECURITY_GROUP_NAME]}]
    )
    return response["SecurityGroups"][0]["GroupId"]


print("➡️ Creating EC2 instance...")
sg_id = get_security_group_id()
instance = ec2_resource.create_instances(
    ImageId=AMI_ID,
    InstanceType="t2.micro",
    KeyName=KEY_NAME,
    MinCount=1,
    MaxCount=1,
    SecurityGroupIds=[sg_id],
    TagSpecifications=[{
        'ResourceType': 'instance',
        'Tags': [{'Key': 'Project', 'Value': 'CSE546'}]
    }]
)[0]

instance_id = instance.id
print(f"✅ EC2 instance launched: {instance_id}")

