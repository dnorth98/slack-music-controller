import json
import os
import boto3
from botocore.exceptions import ClientError
import base64
import pprint

def get_commands_from_queue():
    print("Polling queue for commands")
    messages = []

    sqs_queue_name = None
    queue = None

    if 'QUEUE_NAME' in os.environ:
        sqs_queue_name = os.environ['QUEUE_NAME']

        sqs = boto3.resource('sqs')

        try:
            queue = sqs.get_queue_by_name(QueueName=sqs_queue_name)
        except ClientError as ex:
            if ex.response['Error']['Code'] == 'AWS.SimpleQueueService.NonExistentQueue':
                print("ERROR: SQS queue " + sqs_queue + " was not found")

        if queue:
            # get the commands from the queue. Each message has a body that always
            # has a command and a user. It MAY also contain an arg
            for message in queue.receive_messages(MaxNumberOfMessages=10):
                message_body = json.loads(base64.b64decode(message.body))

                # Make sure we have a command and a user
                # The producer will make sure only valid commands get onto the queue
                if 'command' in message_body and 'user' in message_body:
                    messages.append(message_body)
                else:
                    print("ERROR: No command and/or user specified in the queue message")
                    print(message_body)

                # Let the queue know that the message is processed
                message.delete()
    else:
        print("ERROR: No QUEUE_NAME environment variable found")

    return messages

def validate_controller_token(event):
    print("Validating controller auth token")
    valid = False
    incoming_token = None

    # get the incoming token from the request
    if 'queryStringParameters' in event and event['queryStringParameters']:
        if 'token' in event['queryStringParameters']:
            incoming_token = event['queryStringParameters']['token']
            print("We have a token " + incoming_token)

    # Now see if we have a controller token in the env
    if incoming_token and 'CONTROLLER_TOKEN' in os.environ:
        controller_token = os.environ['CONTROLLER_TOKEN']

        if controller_token == incoming_token:
            valid = True

    return valid

def lambda_handler(event, context):
    queue_messages = []
    statusCode = 200

    if validate_controller_token(event):
        print("Controller token is valid - checking for commands")

        # See if we have any commands in the queue
        queue_messages = get_commands_from_queue()

        pprint.pprint(queue_messages)
    else:
        statusCode = 401
        print("Invalid controller token")

    return {
        "statusCode": statusCode,
        "body": json.dumps(queue_messages)
    }
