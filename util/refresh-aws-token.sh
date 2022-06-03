#!/bin/bash
#
REGION="us-east-2"

while getopts "a:t:r:" opt
do
  case $opt in
    a)
      USER_ARN=$OPTARG
      ;;
    t)
      TOKEN_CODE=$OPTARG
      ;;
    r)
      REGION=$OPTARG
      ;;
    \?)
      echo "Unrecognized options."
      exit 1
      ;;
  esac
done

if [ -z "$USER_ARN" -o -z "$TOKEN_CODE" ]; then
   echo "Usage: $0 -a arn -t code"
   exit 1
fi

unset AWS_SESSION_TOKEN
unset AWS_ACCESS_KEY_ID
unset AWS_SECRET_ACCESS_KEY
unset AWS_DEFAULT_REGION

aws sts get-session-token --serial-number "$USER_ARN" --token-code "$TOKEN_CODE" > $HOME/.aws/aws-session-token.json
jq ".Credentials.Region = \"$REGION\"" $HOME/.aws/aws-session-token.json > $HOME/.aws/aws-session-token.json.temp
mv $HOME/.aws/aws-session-token.json.temp $HOME/.aws/aws-session-token.json
chmod 600 $HOME/.aws/aws-session-token.json
