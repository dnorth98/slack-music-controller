#!/bin/bash

BUCKET=$1
SLACK_TOKEN=$2
CONTROLLER_TOKEN=$3

pushd sam-app

sam package --template-file template.yaml --output-template-file packaged.yaml --s3-bucket ${BUCKET}

sam deploy \
    --template-file packaged.yaml \
    --parameter-overrides SlackToken=${SLACK_TOKEN} ControllerToken=${CONTROLLER_TOKEN} \
    --stack-name slack-music-controller \
    --capabilities CAPABILITY_IAM \
    --region us-east-1

popd
