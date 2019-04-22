#! /bin/bash
#
# Helper for building and running paropt service
# note that docker commands may require sudo permission
#

# If running workers on AWS (EC2Compute), you need to include the lines below, else remove them
# this assumes you have the aws cli installed and configured on the machine
# Note that other AWS env vars are required, see .example.env
AWS_ACCESS_KEY_ID=$(aws --profile default configure get aws_access_key_id)
AWS_SECRET_ACCESS_KEY=$(aws --profile default configure get aws_secret_access_key)
# parsl requires a file for keeping track of the vpcs and security groups it creates.
provider_state_path=`pwd`/config/awsproviderstate.json

# optinally rebuild the image, passing arguments
if [[ $1 =~ build ]]; then
  shift
  docker build . -t paropt-service:latest $@
fi

# the log path allows you to persist logs when running the optimizer
logging_path=${HOME}/Documents/log/paropt
# environment variables for the container
env_config_path=config/.env.dev

# run the container
# if not using AWS, remove the lines setting AWS environment variables
sudo docker run -p 8080:8080 -p 54000-54100:54000-54100 \
  -v ${provider_state_path}:/etc/awsproviderstate.json \
  -v ${logging_path}:/var/log/paropt \
  --env-file ${env_config_path} \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  paropt-service:latest
