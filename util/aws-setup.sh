#!/bin/bash
#
[ ! -d $HOME/.aws ] && mkdir $HOME/.aws && chmod 750 $HOME/.aws

echo -n "Access Key : "
read ACCESSKEY
echo -n "Secret Key : "
read SECRETKEY

cat <<EOF > $HOME/.aws/credentials
[default]
aws_access_key_id = $ACCESSKEY
aws_secret_access_key = $SECRETKEY
EOF

chmod 640 $HOME/.aws/credentials
