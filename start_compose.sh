#! /bin/bash
#
# Helper for running docker compose
#

if [[ $1 =~ prod$ ]]; then
  paropt_env="prod"
else
  paropt_env="dev"
fi

# catting env file b/c it contains some variables used in docker yaml file
sudo env $(cat config/.env.${paropt_env} | sed '/^#/d') \
  docker-compose -f docker-compose.yml -f docker-compose.${paropt_env}.yml up
