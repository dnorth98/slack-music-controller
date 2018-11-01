# slack-music-controller
This is a slack "bot" and controller endpoint to pair with the [musezack-dj](https://github.com/miketypeguy/musezack-dj) project for controlling google play music from Slack.  It is implemented using the [AWS SAM framework](https://github.com/awslabs/serverless-application-model) for deployment on AWS.

# Overall Architecture
![Architecture](https://raw.githubusercontent.com/dnorth98/slack-music-controller/master/images/arch.png)

# Setup

## Slack Setup
The tool uses the outgoing webhooks custom integration.  In Slack, go to Configure Apps->Custom Integrations->Outgoing Webhooks and add a new configuration.  Use the following values:
* Channel - this is the channel you want to trigger the music controller from.  It can be any channel.  Slack will list for the *trigger word* in this channel only
* Trigger Word - this must be *heydj*
* URL - for now, use any value. You'll come back later and fill in the real value once the endpoints are deployed to AWS.
* Descriptive label, name, icon - these can be whatever you'd like.

While you're editing the properties, copy the *Token* value and save it for later.  We'll need to pass that to the deployment script when setting up the endpoints on AWS.  Save the new outgoing webhook but leave this browser tab open as you will need to come back and sub in the real endpoint URL after deploying to AWS.

## Deploying to AWS
Before starting, you will need:
* The [AWS CLI](https://aws.amazon.com/cli/) installed and default credentials configured
* the [AWS SAM CLI](https://github.com/awslabs/aws-sam-cli) installed
* An existing S3 bucket where the AWS Lambda code will be deployed to by SAM
* This repo cloned

1. Run the *build.sh* script.  This will just copy the needed files into the right locations
2. Run the *deploy.sh* script like

```
./deploy.sh <s3 bucket> <slack token for the webhook> <a token to use for the muzack controller>
```

The bucket and slack token are discussed above.  The Musezack controller token is any value you generate that is then used by the Musezack client when calling into the `/controller` endpoint.

deploy.sh uses AWS SAM to package the AWS Lambda functions and then deploys them to AWS.  Everything is deployed as a Cloudformation Stack in your default region (usually us-east-1).  Once the stack is deployed, the script will output several pieces of information.  You'll need 2 of the outputs (you can also get these by logging into the AWS Console, going to Cloudformaton, finding the `slack-music-controller` stack and clicking on Outputs):
* API Gateway endpoint URL for HeyDJ Slack webhook - Edit the Slack outgoing webhook you created above and use this URL as the webhook URL
* API Gateway endpoint URL for Musezack controller to poll - Use this URL in the configuration for Musezack for it's endpoint to poll for commands

# Running and debugging locally
AWS SAM makes running and debugging locally really easy.  Running SAM projects locally is [well documented in the SAM docs](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-quick-start.html) but here's the specifics for this project:

1. Create a FIFO SQS queue in AWS.  It *must* be a FIFO queue.  You can use the default properties for testing
2. create an `env.json` file containing values for the SQS queue, slack token and controller token.  Example:
```
{
  "HeyDJFunction": {
    "SLACK_TOKEN": "my-slack-token",
    "QUEUE_NAME": "my-sqs-fifo-queue"
  },
  "ControllerFunction": {
    "CONTROLLER_TOKEN": "my-controller-function",
    "QUEUE_NAME": "my-sqs-fifo-queue"
  }
}
```
3.  Start the API using SAM `sam local start-api --env-vars env.json`
4.  Send a request to the API using the URLs provided by SAM and your controller token.  Examples below

## Testing the controller endpoint locally
The controller endpoint just checks the AWS SQS queue for commands and sends back an ordered JSON list to the Musezack client.  Authentication is done via a simple token passed in the query string.  Testing it locally is then as simple as hitting the local endpoint and passing the token.
```
curl http://127.0.0.1:3000/controller?token=my_controller_token
```
## Testing the heydj endpoint locally
While the controller is easy to test locally, to test the Slack endpoint locally, you'll need to send in a valid slack payload.  In the `local-debug` folder in the project, you'll find sample payloads for a few of the commands.  You'll need to set the correct slack token in the payload but you can then test like this:
```
curl -X POST --data "@local-debug/heydj/request-command.body" http://127.0.0.1:3000/heydj
```
