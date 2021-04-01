from botocore.exceptions import ClientError
import traceback
import logging
import boto3
import json
import sys
import os

client = boto3.client("cloudformation")
stack_name = ""
ami_id_parameter_name = ""
region = os.environ["AWS_REGION"]


def handle_exception(e):
    e_type, e_value, e_traceback = sys.exc_info()
    traceback_str = traceback.format_exception(e_type, e_value, e_traceback)
    err_msg = json.dumps(
        {
            "errorType": e_type.__name__,
            "errorMessage": str(e_value),
            "stackTrace": traceback_str,
        }
    )
    logger.error(err_msg)


def handler(event, context):
    # grab the ami id from the event
    # refer the sample event for message format
    # https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ECS-AMI-SubscribeTopic.html#ECS-AMI-Notification-format
    try:
        message = json.loads(event["Records"][0]["Sns"]["Message"])
        ami_id = message["ECSAmis"][0]["Regions"][region]["ImageId"]
        logger.info(f"The latest AMI id in {region} is {ami_id}")
    except (KeyError, IndexError) as e:
        print(f"Failed to retrieve AMI Id for {region} region from the event")
        handle_exception(e)
    try:
        response = client.describe_stacks(StackName=stack_name)
    except ClientError as e:
        print(f"Error fetching {stack_name} Stack details")
        handle_exception(e)

    parameters = []

    # copy all current parameters except ami id

    try:
        for parameter in response["Stacks"][0]["Parameters"]:
            if parameter["ParameterKey"] == ami_id_parameter_name:
                continue
            parameters.append(
                {"ParameterKey": parameter["ParameterKey"], "UsePreviousValue": True}
            )
    except (KeyError, IndexError) as e:
        print(f"Failed to get current parameters of {stack_name} from stack details")
        handle_exception(e)
    # replace the ami_id
    parameters.append({"ParameterKey": ami_id_parameter_name, "ParameterValue": ami_id})

    # call update stack using current template and pass the above parameters
    try:
        response = client.update_stack(
            StackName=stack_name,
            UsePreviousTemplate=True,
            Parameters=parameters,
        )
    except ClientError as e:
        print("Error initiating stack update")
        handle_exception(e)
