#! /bin/bash
#
# Helper for building and running paropt service
#

function usage() {
  echo "Usage: ./start_service [--aws | --local] (--build (<docker build flags))"
}

paropt_run_location=$1
shift

# optinally rebuild the image, passing remaining arguments
if [[ $1 =~ build ]]; then
  shift
  sudo docker build . -t paropt-service:latest $@
fi

if [[ "${paropt_run_location}" =~ "prod" ]]; then
  # If running workers on AWS (EC2Compute), you need to include the lines below
  # this assumes you have the aws cli installed and configured on the machine
  # Note that other AWS env vars are required, see .example.env
  AWS_ACCESS_KEY_ID=$(aws --profile default configure get aws_access_key_id)
  AWS_SECRET_ACCESS_KEY=$(aws --profile default configure get aws_secret_access_key)

  # environment variables for the container
  source config/.env.prod

  # run the container
  sudo docker run -p 8080:8080 -p 54000-54100:54000-54100 \
    -v ${PAROPT_HOST_AWS_STATE_FILE}:${PAROPT_AWS_STATE_FILE} \
    -v ${PAROPT_HOST_LOGS}:/var/log/paropt \
    --env-file config/.env.prod \
    -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
    -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
    paropt-service:latest

elif [[ "${paropt_run_location}" =~ "dev" ]]; then
  # environment variables for the container
  source config/.env.dev

  # run the container
  sudo docker run -p 8080:8080 -p 54000-54100:54000-54100 \
    -v ${PAROPT_HOST_LOGS}:/var/log/paropt \
    --env-file config/.env.dev \
    paropt-service:latest
else
  usage
  exit 1
fi
