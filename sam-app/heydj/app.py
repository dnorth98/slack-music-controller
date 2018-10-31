import json
import boto3
from botocore.exceptions import ClientError
import os
from urllib.parse import parse_qs
import base64

def post_command_to_queue(command, arg, user):
    print("Posting command to queue")
    status = True

    sqs_queue_name = None
    queue = None
    message = {}

    if 'QUEUE_NAME' in os.environ:
        sqs_queue_name = os.environ['QUEUE_NAME']

        sqs = boto3.resource('sqs')

        try:
            queue = sqs.get_queue_by_name(QueueName=sqs_queue_name)
        except ClientError as ex:
            if ex.response['Error']['Code'] == 'AWS.SimpleQueueService.NonExistentQueue':
                print("ERROR: SQS queue " + sqs_queue_name + " was not found")
                status = False

        if queue:
            message_json = {
                "command" : command,
                "user" : user,
            }

            if arg:
                message_json['arg'] = arg

            # Must be a base64 encoded string
            # This gets it as a bytes type...
            base64_message = base64.b64encode(json.dumps(message_json).encode('utf-8'))

            # And this gets it as a b64 encoded string
            base64_message = base64_message.decode('utf-8')
            print("base64 " + base64_message)

            # Create a new message
            try:
                response = queue.send_message(
                    MessageBody=base64_message,
                    MessageGroupId='SlackDJ'
                )
            except ClientError as ex:
                print("ERROR writing to SQS queue " + ex.response['Error']['Code'])
                status = False

            if status:
                print("Successfully sent message to queue")
                print("SQS Message ID: " + response.get('MessageId'))
                print("SQS MD5: " + response.get('MD5OfMessageBody'))

    return status

def command_handler(command, arg, user):
    print("Handling command")
    slack_dict = {}
    post_command = True

    if command == 'help':
        # Do not post to queue, handle here
        post_command = False

    if command == 'request':
        # special format checking
        if ' by' in arg:
            post_command = True
        else:
            post_command = False
            print("Not submitting request command - does not match correct format")
            slack_dict['text'] = user + ', requests need to be of the form SONG by ARTIST. Try again.'

    if post_command:
        status = post_command_to_queue(command, arg, user)

    if command == 'help':
        slack_dict['text'] = 'You can ask me the following:\n'
        slack_dict['text'] += '*play* - play whatever is queued up\n'
        slack_dict['text'] += '*stop* - stop the funky beats\n'
        slack_dict['text'] += '*skip* - skip to the next track\n'
        slack_dict['text'] += '*nowplaying* - report back what is currently playing\n'
        slack_dict['text'] += '*nextup* - report back what is coming up\n'
        slack_dict['text'] += '*request* <songname> by <artist> - request a song be added to the playlist\n'
        slack_dict['text'] += 'eg: heydj request danger zone by kenny loggins\n'
    elif command == 'nextup':
        if status:
            slack_dict['text'] = 'OK, ' + user + '. I have asked the DJ to tell us what\'s spinning next'
        else:
            slack_dict['text'] = 'I\'m sorry ' + user + '. I was unable to ask the DJ to tell us what\'s spinning next'
    elif command == 'nowplaying':
        if status:
            slack_dict['text'] = 'OK, ' + user + '. I have asked the DJ to tell us what\'s playing now'
        else:
            slack_dict['text'] = 'I\'m sorry ' + user + '. I was unable to ask the DJ to tell us what\'s playing now'
    elif command == 'play':
        if status:
            slack_dict['text'] = 'OK, ' + user + '. I have asked the DJ to play some funky beats'
        else:
            slack_dict['text'] = 'I\'m sorry ' + user + '. I was unable to ask the DJ to play some funky beats'
    elif command == 'request':
        if not slack_dict: # will be already set if there is a format error
            if status:
                slack_dict['text'] = 'OK, ' + user + '. I have asked the DJ to play ' + arg
            else:
                slack_dict['text'] = 'I\'m sorry ' + user + '. I was unable to ask the DJ to play ' + arg
    elif command == 'skip':
        if status:
            slack_dict['text'] = 'OK, ' + user + '. I have asked the DJ to skip to the next track'
        else:
            slack_dict['text'] = 'I\'m sorry ' + user + '. I was unable to ask the DJ to skip to the next track'
    elif command == 'stop':
        if status:
            slack_dict['text'] = 'OK, ' + user + '. I have asked the DJ to stop the beats'
        else:
            slack_dict['text'] = 'I\'m sorry ' + user + '. I was unable to ask the DJ to stop the beats'
    else:
        print("ERROR - command handler called with unknown command")

    return slack_dict

def validate_slack_token(incoming_token):
    print("Validating slack auth token")
    valid = False

    # Now see if we have the allowable token in the env
    if incoming_token and 'SLACK_TOKEN' in os.environ:
        valid_slack_token = os.environ['SLACK_TOKEN']

        if valid_slack_token == incoming_token:
            valid = True

    return valid

def lambda_handler(event, context):
    # print("Received event: " + json.dumps(event, indent=2))
    statusCode = 200
    valid_trigger_word = 'heydj'
    slack_return_content = []

    if 'body' in event:
        parsed_body = parse_qs(event['body'])

        # The parsed body looks like:
        # {'channel_id': ['channel id'],
        # 'channel_name': ['slack channel name'],
        # 'service_id': ['slack bot id'],
        # 'team_domain': ['slack domain prefix'],
        # 'team_id': ['slack team id'],
        # 'text': ['heydj request testing 1234'],
        # 'timestamp': ['1540930044.021500'],
        # 'token': ['yourslacktoken'],
        # 'trigger_word': ['heydj'],
        # 'user_id': ['slack user id'],
        # 'user_name': ['slack username']}

        if 'token' in parsed_body:
            if validate_slack_token(parsed_body['token'][0]):
                print("Valid slack token provided - processing command")

                # Check the trigger word is correct
                if parsed_body['trigger_word'][0] == valid_trigger_word:
                    print("Valid trigger word detected")

                    # The text field contains the entire command.  Examples:
                    # request stand by REM
                    # help
                    # skip

                    # Get the command first...
                    words = parsed_body['text'][0].split(" ")
                    command = words[1]
                    print("Received command: " + command)

                    # Now get the argument if it is there
                    # If there is no extra argument, arg will remain blank
                    arg = ' '.join(words[2:])
                    if arg:
                        print("Received argument [" + arg + "]")

                    # This will return a dict in the format slack expects....
                    # We json encode it before sending it along to slack
                    slack_return_content = command_handler(command, arg, parsed_body['user_name'][0])
                else:
                    statusCode = 500
                    print("ERROR: Invalid trigger word. Wanted " + valid_trigger_word + " received " + parsed_body['trigger_word'][0])
            else:
                statusCode = 401
                print("ERROR: Invalid slack token was provided")
        else:
            statusCode = 401
            print("ERROR: No slack token was provided in the body")
    else:
        statusCode = 500
        print("ERROR: No body was provided in the event")

    return {
        "statusCode": statusCode,
        "body": json.dumps(slack_return_content)
    }
