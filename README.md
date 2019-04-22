tldr;
RESTful service for automating optimization of arbitrary tools.
## Usage
Clone this repo, then configure the `start_service.sh` as specified in the script. It expects some environment variables to be configured, see `config/.example.env` for an example.  
Once configured, you can run it in dev mode with `./start_service.sh --dev`, or in prod (on aws) with `./start_service.sh --prod`.

## Examples
See examples in `/examples`.
