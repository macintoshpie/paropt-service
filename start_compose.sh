#! /bin/bash
#
# Helper for running docker compose
#

if [[ "$(uname)" == "Darwin" ]]; then
  export PAROPT_HOST_LOGS=~/Library/Logs/paropt/
else
  export PAROPT_HOST_LOGS=/var/log/paropt/
fi

if [[ $1 =~ prod$ ]]; then
  paropt_env="prod"
  shift
else
  paropt_env="dev"
  shift
fi

sudo -E docker-compose -f docker-compose.yml -f docker-compose.${paropt_env}.yml up $@
