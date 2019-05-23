tldr;
RESTful service for automating optimization of arbitrary tools.

## Setup
To run the service, clone this repo then setup your environment variable files `config/.env.prod` and `config/.env.dev`. The file `config/.example.env` shows the required environment variables and what they are used for.
The service requires a database server to be running as well (see here for runnnig a postgres server).
If running in `prod`, it also requires an AWS account that can launch EC2 instances.
See the example env file for more info.

Once you've properly setup the .env file, you can run the `start_compose.sh` script:
```
Usage:
./start_compose.sh [--dev | --prod] (any other args to pass to docker, e.g. --build)
  --dev: run dev deployment, using .env.dev file and dockerfile.dev.yaml - auth endpoint protection is disabled
  --prod: run prod deployment, using .env.prod file and dockerifile.prod.yaml - auth endpoint protection is enabled
```

## Usage
See examples in `/examples` directory. Here's a quick overview the endpoints (prefixed with `/api/v1`)
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
Note that currently we are using flask sessions for auth, so if running in `prod`, you'll first have to go through the auth flow by visiting the `/login` endpoint. You must login with a uchicago account to use the service. Once authenthenticated, the session is maintained through your `session` cookie, so if you want to make any requests outside of the browser, youll need to copy that cookie into your requests.
