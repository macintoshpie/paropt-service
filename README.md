tldr;
RESTful service for automating optimization of arbitrary tools.

## Usage
Clone this repo then setup your environment variable files `config/.env.prod` and `config/.env.dev`. The file `config/.example.env` shows the required environment variables and what they are used for.
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

## Examples
See examples in `/examples`.

## Authentication
Note that currently we are using flask sessions for auth, so if running in `prod`, you'll first have to go through the auth flow by visiting the `/login` endpoint. You must login with a uchicago account to use the service. Once authenthenticated, the session is maintained through your `session` cookie, so if you want to make any requests outside of the browser, youll need to copy that cookie into your requests.
