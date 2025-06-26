from typing import List
import boto3, time
from botocore.exceptions import BotoCoreError, ClientError
from config import Config

from create_log import init_logging

log = init_logging("aws", "aws.log")
import uuid

s3 = boto3.client("s3", region_name=Config.REGION)
sqs = boto3.client("sqs", region_name=Config.REGION)
ec2 = boto3.client("ec2", region_name=Config.REGION)
iam = boto3.client("iam", region_name=Config.REGION)
BOTOCORE_ERROR = BotoCoreError
CLIENT_ERROR = ClientError


# -------- S3 Utilities --------
def clear_bucket(bucket_name):
    log.info(f"Clearing all objects from bucket: {bucket_name}")

    response = s3.list_objects_v2(Bucket=bucket_name)
    if "Contents" not in response:
        log.info("Bucket already empty.")
        return

    for obj in response["Contents"]:
        key = obj["Key"]
        s3.delete_object(Bucket=bucket_name, Key=key)
        log.info(f"Deleted {key} from {bucket_name}")

    log.info(f"Bucket {bucket_name} cleared.")


def ensure_bucket(bucket_name):
    try:
        s3.head_bucket(Bucket=bucket_name)
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": Config.REGION}
            )
            log.info(f"Created S3 bucket: {bucket_name}")
        else:
            raise


def ensure_queue(queue_name, fifo=True):
    log.info("ensure_queue() called")

    attributes = {
        "FifoQueue": "true",
        "ContentBasedDeduplication": "true",
        "VisibilityTimeout": "30"
    } if fifo else {}

    try:
        result = sqs.create_queue(
            QueueName=queue_name,
            Attributes=attributes
        )
        queue_url = result["QueueUrl"]
        log.info("Ensured queue %s → %s", queue_name, queue_url)
        return queue_url

    except CLIENT_ERROR as e:
        if e.response["Error"]["Code"] == "QueueAlreadyExists":
            log.warning("Queue %s already exists. Fetching existing URL...", queue_name)
            result = sqs.get_queue_url(QueueName=queue_name)
            queue_url = result["QueueUrl"]
            log.info("Fetched existing queue %s → %s", queue_name, queue_url)
            return queue_url
        else:
            log.error("Failed to create or access queue %s: %s", queue_name, e)
            raise


def purge_queue(queue_name):
    log.info(f"Purging queue: {queue_name}")
    try:
        response = sqs.get_queue_url(QueueName=queue_name)
        queue_url = response["QueueUrl"]
        sqs.purge_queue(QueueUrl=queue_url)
        log.info(f"Purged queue: {queue_name}")
    except CLIENT_ERROR as e:
        if e.response['Error']['Code'] == 'PurgeQueueInProgress':
            log.warning(f"PurgeQueue already in progress for {queue_name}, skipping.")
        else:
            log.error(f"Failed to purge queue {queue_name}: {e}")
            raise


def upload_file_to_s3(bucket: str, key: str, data, is_path=False):
    try:
        if is_path:
            with open(data, "rb") as f:
                s3.upload_fileobj(f, bucket, key)
        else:
            s3.put_object(Bucket=bucket, Key=key, Body=data)
        log.info(f"Uploaded {key} to {bucket}")
    except Exception as e:
        log.error(f"Failed to upload {key} to {bucket}: {e}")


def download_file_from_s3(bucket, key, download_path):
    s3.download_file(bucket, key, download_path)
    log.info(f"Downloaded {key} from {bucket} → {download_path}")


def get_object_text(bucket, key):
    response = s3.get_object(Bucket=bucket, Key=key)
    return response['Body'].read().decode("utf-8")


# -------- SQS Utilities --------
def get_queue_url(name):
    return sqs.get_queue_url(QueueName=name)["QueueUrl"]


def send_sqs_message(queue_url, body):
    params = {"QueueUrl": queue_url, "MessageBody": body}
    if queue_url.endswith(".fifo"):
        params["MessageGroupId"] = "default"
        params["MessageDeduplicationId"] = str(uuid.uuid4())
    resp = sqs.send_message(**params)
    log.info(f"Sent message to SQS {queue_url}")
    return resp["MessageId"]


def receive_sqs_message(queue_url, wait=10):
    resp = sqs.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=wait
    )
    messages = resp.get("Messages", [])
    if not messages:
        return None
    msg = messages[0]
    return msg["Body"], msg["ReceiptHandle"]


def delete_sqs_message(queue_url, receipt_handle):
    sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
    log.info(f"Deleted message from {queue_url}")


def get_queue_depth(queue_url):
    """Get total queue depth: visible + in-flight (not visible)"""
    try:
        attrs = sqs.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=["ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"]
        )["Attributes"]
        visible = int(attrs.get("ApproximateNumberOfMessages", 0))
        in_flight = int(attrs.get("ApproximateNumberOfMessagesNotVisible", 0))
        total = visible + in_flight
        log.debug(f"Queue depth: {visible} visible, {in_flight} in-flight, total = {total}")
        return total
    except Exception as e:
        log.error(f"Failed to get queue depth: {e}")
        return 0


# -------- EC2 Utilities --------
def get_default_ami(region):
    log.info("Looking up latest Amazon Linux 2 AMI...")
    response = ec2.describe_images(
        Owners=["amazon"],
        Filters=[
            {"Name": "name", "Values": ["amzn2-ami-hvm-*-x86_64-gp2"]},
            {"Name": "state", "Values": ["available"]},
        ]
    )
    images = sorted(response["Images"], key=lambda x: x["CreationDate"], reverse=True)
    return images[0]["ImageId"] if images else None


def get_default_sg_id():
    log.info(f"Looking up security group '{Config.SECURITY_GROUP_NAME}'...")
    response = ec2.describe_security_groups(
        Filters=[{"Name": "group-name", "Values": [Config.SECURITY_GROUP_NAME]}]
    )
    groups = response.get("SecurityGroups", [])
    return groups[0]["GroupId"] if groups else None


def get_default_iam_profile():
    log.info(f"Looking up IAM instance profile '{Config.IAM_INSTANCE_PROFILE}'...")
    profiles = iam.list_instance_profiles().get("InstanceProfiles", [])
    for p in profiles:
        if p["InstanceProfileName"] == Config.IAM_INSTANCE_PROFILE:
            return p["InstanceProfileName"]
    return None


def list_instances_by_tag(tag_key: str, tag_value: str, states: list = None) -> list:
    """General-purpose function to list instances filtered by tag and state."""
    filters = [
        {"Name": f"tag:{tag_key}", "Values": [tag_value]}
    ]
    if states:
        filters.append({"Name": "instance-state-name", "Values": states})

    resp = ec2.describe_instances(Filters=filters)
    instances = []
    for r in resp["Reservations"]:
        for inst in r["Instances"]:
            instances.append(inst["InstanceId"])
    return instances


def launch_worker_instance():
    ami = get_default_ami(Config.REGION)
    sg_id = get_default_sg_id()
    iam_profile = get_default_iam_profile()

    if not all([ami, sg_id, iam_profile]):
        raise Exception(f"Missing parameters for EC2 launch. AMI: {ami}, SG: {sg_id}, IAM: {iam_profile}")

    log.info(f"Launching worker instance with AMI={ami}, SG={sg_id}, IAM={iam_profile}...")

    ec2.run_instances(
        ImageId=ami,
        InstanceType=Config.INSTANCE_TYPE,
        MinCount=1,
        MaxCount=1,
        KeyName=Config.KEY_NAME,
        SecurityGroupIds=[sg_id],
        IamInstanceProfile={'Name': iam_profile},
        TagSpecifications=[{
            "ResourceType": "instance",
            "Tags": [
                {"Key": "Name", "Value": f"{Config.WORKER_TAG}-{int(time.time())}"},
                {"Key": "Role", "Value": Config.WORKER_TAG}
            ]
        }]
    )


def terminate_worker_instance(instance_id):
    ec2.terminate_instances(InstanceIds=[instance_id])
    log.info(f"Terminated instance {instance_id}")


def list_objects_in_s3(bucket: str, prefix: str = "") -> List[str]:
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    return [obj["Key"] for obj in response.get("Contents", [])]


def download_from_s3(bucket: str, key: str, local_path: str):
    s3.download_file(Bucket=bucket, Key=key, Filename=local_path)
