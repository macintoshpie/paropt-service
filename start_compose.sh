#! /bin/bash
#
# Helper for running docker compose
#

if [[ $1 =~ prod$ ]]; then
  paropt_env="prod"
  # assumes aws cli is installed
  AWS_ACCESS_KEY_ID=$(aws --profile default configure get aws_access_key_id)
  AWS_SECRET_ACCESS_KEY=$(aws --profile default configure get aws_secret_access_key)
else
  paropt_env="dev"
fi

# catting env file b/c it contains some variables used in docker yaml file
sudo env $(cat config/.env.${paropt_env} | sed '/^#/d') \
  docker-compose -f docker-compose.yml -f docker-compose.${paropt_env}.yml up $@
