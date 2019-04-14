tldr;
RESTful service for automating optimization of arbitrary tools.

## Examples
### Create new experiment
request body in json format (data.json in example below):
```json
{
  "tool_name": "mytool",
  "parameters": [
    {
      "name": "parameterA",
      "minimum": 0,
      "maximum": 10
    }
  ],
  "command_template_string": "echo \"HELLO WORLD\"\n sleep ${parameterA}"
}
```
```bash
curl -d "@data.json" -H "Content-Type: application/json" -X POST http://localhost:8080/api/v1/experiments
```

### Run trials for experiment
After creating an experiment you can run trials.
In trial.json:
```json
{
  "optimizer": {
    "type": "bayesopt",
    "n_init": 2,
    "n_iter": 2,
  }
}
```
```bash
curl -d "@trial.json" -H "Content-Type: application/json" -X POST http://localhost:8080/api/v1/experiments/1/trials
```