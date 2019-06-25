### tldr;
RESTful service for automating optimization of arbitrary tools. See [paropt](https://github.com/macintoshpie/paropt) for the standalone python package for automated optimization, and [paropt-service-sdk](https://github.com/macintoshpie/paropt-service-sdk) for a python wrapper for HTTP requests to this service.

## Setup
To run the service, clone this repo then setup your environment variable files `config/.env.prod` and `config/.env.dev`. The file `config/.example.env` shows the required environment variables and what they are used for.
The service requires a database server to be running as well (see here for runnnig a postgres server).
If running in `prod`, it also requires an AWS account that can launch EC2 instances.
See the example env file for more info.

Once you've properly setup the .env file, you can run the `start_compose.sh` script:
```
Usage:
./start_compose.sh [--dev | --prod | --build | --setupaws]
  --dev: run dev deployment, using .env.dev file and dockerfile.dev.yaml - auth endpoint protection is disabled
  --prod: run prod deployment, using .env.prod file and dockerifile.prod.yaml - auth endpoint protection is enabled
  --build: rebuild docker image wihtout caching (ie from scratch) - useful when there's an update to requirements
  --setupaws: should be run before starting the production server - runs simple experiment to generate VPC state file, awsproviderstate.json, for parsl
```

If running in production (on AWS), you'll need to have the service launch a test instance which will create a VPC used by parsl *before* starting the server:
```
./start_compose.sh --setupaws
```
Note that if you have already attempted to start the server you might get some errors. When troubleshooting make sure theres nothing at `./config/awsprovider.json`, and rebuild the image without caching by running `./start_compose --build`. It's also possible that you have misconfigured the `.env.prod` file, make sure your Account, Key, ec2 key name, and instance role arn are properly configured.  
Once it successfully runs, you should find the file parsl created under `./config/awsproviderstate.json`, and you can now start the server.

## Usage
See examples in `/examples` directory. Here's a quick overview the endpoints (all calls should be prefixed with `/api/v1`)
* `/experiments`
  * POST: get or create experiment
    * see examples directory for expected body
* `/experiments/<experiment id>`
  * GET: get experiment info
* `/experiments/<experiment id>/trials`
  * GET: get trials for experiment
  * POST: start running a new trial
    * body indicates optimization config. see examples directory for expected body
* `/experients/<experiment id>/job`
  * GET: get "current" (queued or running) job for experiment. Returns `404` if not queued or running and `status` contains `missing`
* `/jobs/<job id>`
  * GET: get job info. Returns `404` if not found and `status` is `missing`
* `/jobs/running`
  * GET: get currently running jobs
* `/jobs/failed`
  * GET: get failed jobs (including stack trace)
* `/jobs/queued`
  * GET: get queued jobs

## Authentication
You can authenticate by hitting the `/login` endpoint, which will redirect you to the main site after successfully logging in. You'll be provided with a session cookie for future auth.  
When using the `paropt-service-sdk`, you'll be given an access token which will be used for each request.
