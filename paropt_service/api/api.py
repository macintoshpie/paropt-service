import psycopg2.extras
import threading
import pickle
import parsl
import uuid
import json
import time
import os
from threading import Thread 
import json
import traceback

from flask import Blueprint, jsonify, request, abort
from parsl.app.app import python_app

from .paropt_manager import ParoptManager

import paropt
from paropt.runner import ParslRunner
from paropt.storage import LocalFile, RelationalDB
from paropt.optimizer import BayesianOptimizer, GridSearch
from paropt.runner.parsl import timeCmd

api = Blueprint("api", __name__)

def toJson(obj):
    return json.dumps(obj, indent=2, sort_keys=True, default=str)

@api.route('/experiments', methods=['POST'])
def getOrCreateExperiment():
    """Create a new experiment
    Expects json body like below. All attributes are required.
    ```
    {
        "tool_name": "<tool_name>",
        "parameters": [<parameter1>, <parameter2>, ...],
        "command_template_string": "<command_template_string>"
    }
    ```
    A parameter is defined as follows
    ```
    {
        "name": "<name>",
        "minimum": <minimum>,
        "maximum": <maximum>
    }
    ```
    """
    request_data = request.get_json()
    if request_data == None:
        return "Must include json body and content type header to create experiment", 400
    try:
        experiment, _, created = ParoptManager.getOrCreateExperiment(request_data)
        return toJson(experiment.asdict()), 200
    except Exception as e:
        print("Error: {}".format(e))
        print(traceback.format_exc())
        return "Failed to get/create experiment: {}".format(e), 500

@api.route('/experiments/<experiment_id>', methods=['GET'])
def getExperiment(experiment_id):
    """Get Experiment info"""
    experiment = ParoptManager.getExperiment(experiment_id)
    if experiment == None:
        return "No experiment with id {}".format(experiment_id), 404
    experiment_dict = experiment.asdict()
    if ParoptManager.isRunning(experiment_id):
        experiment_dict['status'] = 'running'
    else:
        experiment_dict['status'] = 'not running'
    return toJson(experiment_dict), 200

@api.route('/experiments/<experiment_id>/trials', methods=['GET'])
def getTrials(experiment_id):
    """Get all recorded trials for experiment"""
    trials = ParoptManager.getTrials(experiment_id)
    return toJson(trials), 200

@api.route('/experiments/<experiment_id>/trials', methods=['POST'])
def runTrials(experiment_id):
    """Run trials for experiment
    Expects json body like below. See the optimizers in paropt package for initialization parameters
    ```
    {
        "optimizer": {
            "type": "bayesopt" | "grid",
            [optimizer_specific_params]
        }
    }
    ```
    """
    request_data = request.get_json()
    request_data = request_data if request_data != None else {}

    success, res = ParoptManager.runTrials(experiment_id, request_data)
    if success == True:
        return res, 202
    return res, 404

@api.route('/experiments/running', methods=['GET'])
def getRunningExperiments():
    """Get currently running experiments"""
    running_exps = ParoptManager.getRunningExperiments()
    return toJson(running_exps)

@api.route('/experiments/<experiment_id>/stop', methods=['POST'])
def stopExperiment(experiment_id):
    """Stop a running experiment"""
    stop_res = ParoptManager.stopExperiment(experiment_id)
    return toJson(stop_res)
