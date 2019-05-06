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

from flask import Blueprint, jsonify, request, abort, current_app

import redis
from rq import Queue, Connection

from .utils import login_required

from .paropt_manager import ParoptManager

import paropt
from paropt.runner import ParslRunner
from paropt.storage import LocalFile, RelationalDB
from paropt.optimizer import BayesianOptimizer, GridSearch
from paropt.runner.parsl import timeCmd

api = Blueprint("api", __name__)

@api.route('/experiments', methods=['POST'])
@login_required
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
        experiment_dict = ParoptManager.getOrCreateExperiment(request_data)
        return jsonify(experiment_dict), 200
    except Exception as e:
        print("Error: {}".format(e))
        print(traceback.format_exc())
        return "Failed to get/create experiment: {}".format(e), 500

@api.route('/experiments/<int:experiment_id>', methods=['GET'])
@login_required
def getExperiment(experiment_id):
    """Get Experiment info"""
    experiment = ParoptManager.getExperimentDict(experiment_id)
    if experiment == None:
        return "No experiment with id {}".format(experiment_id), 404
    # experiment_dict = experiment.asdict()
    experiment['job'] = ParoptManager.jobToDict(ParoptManager.getRunningExperiment(experiment_id))
    return jsonify(experiment), 200

@api.route('/experiments/<int:experiment_id>/trials', methods=['GET'])
@login_required
def getTrials(experiment_id):
    """Get all recorded trials for experiment"""
    trials = ParoptManager.getTrials(experiment_id)
    return jsonify(trials), 200

@api.route('/experiments/<int:experiment_id>/trials', methods=['POST'])
@login_required
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

    result = ParoptManager.runTrials(experiment_id, request_data)
    if result['status'] == 'submitted':
        return jsonify(result), 202
    return jsonify(result), 400

@api.route('/experiments/running', methods=['GET'])
@login_required
def getRunningExperiments():
    """Get currently running experiments"""
    running_exps = ParoptManager.getRunningExperiments()
    running_exps = [ParoptManager.jobToDict(job) for job in running_exps]
    return jsonify(running_exps)

@api.route('/experiments/<int:experiment_id>/stop', methods=['POST'])
@login_required
def stopExperiment(experiment_id):
    """Stop a running experiment"""
    stop_res = ParoptManager.stopExperiment(experiment_id)
    return jsonify(stop_res)
