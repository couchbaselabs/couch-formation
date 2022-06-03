#!/bin/bash
#

which jq >/dev/null 2>&1
if [ $? -ne 0 ]; then
   echo "Please install jq and make sure its location is in PATH."
   return
fi

if [ ! -r $HOME/.aws/aws-session-token.json ]; then
   echo "Session token file not found."
   return
fi

unset AWS_SESSION_TOKEN
unset AWS_ACCESS_KEY_ID
unset AWS_SECRET_ACCESS_KEY

export AWS_ACCESS_KEY_ID=$(cat $HOME/.aws/aws-session-token.json | jq -r '.Credentials.AccessKeyId')
export AWS_SECRET_ACCESS_KEY=$(cat $HOME/.aws/aws-session-token.json | jq -r '.Credentials.SecretAccessKey')
export AWS_SESSION_TOKEN=$(cat $HOME/.aws/aws-session-token.json | jq -r '.Credentials.SessionToken')
export AWS_DEFAULT_REGION=$(cat $HOME/.aws/aws-session-token.json | jq -r '.Credentials.Region')
