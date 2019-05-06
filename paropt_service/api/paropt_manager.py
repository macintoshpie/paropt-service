import multiprocessing
import atexit
import os
import time

from flask import current_app

import redis
from rq import Queue, Connection
from rq.registry import StartedJobRegistry
from rq.job import Job

from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, in_production, getAWSConfig

import parsl

import paropt
from paropt.runner import ParslRunner
from paropt.storage import LocalFile, RelationalDB
from paropt.optimizer import BayesianOptimizer, GridSearch
from paropt.runner.parsl import timeCmd
from paropt.storage.entities import Parameter, Experiment, EC2Compute, LocalCompute

def getOptimizer(optimizer_config):
  """Construct optimizer from a config dict
  
  Args:
    optimizer_config(dict): configuration for optimizer
  
  Returns:
    Optimizer
  """
  if optimizer_config == None:
    return BayesianOptimizer(
      n_init=2,
      n_iter=2
    )
  optimizer_type = optimizer_config.get('type')
  if optimizer_type == 'bayesopt':
    n_init = optimizer_config.get('n_init')
    n_iter = optimizer_config.get('n_iter')
    try:
      n_init = int(n_init)
      n_iter = int(n_iter)
      return BayesianOptimizer(n_init=n_init, n_iter=n_iter)
    except:
      return None
  elif optimizer_type == 'grid':
    num_configs_per_param = optimizer_config.get('num_configs_per_param')
    try:
      num_configs_per_param = int(num_configs_per_param)
      return GridSearch(num_configs_per_param=num_configs_per_param)
    except:
      return None

class ParoptManager():
  """Manages paropt tasks and storage records using Redis queue and paropt storage"""
  _started = False
  db_storage = None

  @classmethod
  def start(cls):
    if cls._started:
      return
    cls.db_storage = RelationalDB(
      'postgresql',
      DB_USER,
      DB_PASSWORD,
      DB_HOST,
      DB_NAME
    )
    cls._started = True

  @classmethod
  def runTrials(cls, experiment_id, run_config):
    """Put experiment into job queue to be run

    Args:
      experiment_id(int): id of experiment to run
      run_config(dict): dict for how to config optimizer
    
    Returns:
      result(dict): result of attempt to add job to queue
    """
    if not cls._started:
      raise Exception("ParoptManager not started")

    # check if experiment exists
    experiment = cls.getExperimentDict(experiment_id)
    if experiment == None:
      return {'status': 'failed', 'message': "Experiment not found with id {}".format(id)}
    
    # check if experiment is already running
    job = cls.getRunningExperiment(experiment_id)
    if job:
      return {'status': 'failed', 'message': 'Experiment already running'}
    
    optimizer = getOptimizer(run_config.get('optimizer'))
    if optimizer == None:
      return {'status': 'failed', 'message': "Invalid run configuration provided"}
    
    # submit job to redis
    with Connection(redis.from_url(current_app.config['REDIS_URL'])):
      q = Queue()
      job = q.enqueue(
        f=cls._startRunner,
        args=(experiment, optimizer),
        result_ttl=0,
        job_timeout=-1,
        meta={'experiment_id': str(experiment_id)})

    response_object = {
      'status': 'submitted',
      'job': cls.jobToDict(job)
    }
    return response_object

  @classmethod
  def getRunningExperiments(cls):
    """Returns experiments currently being run

    Returns:
      jobs(list): list of jobs that are being run
    """
    with Connection(redis.from_url(current_app.config['REDIS_URL'])) as conn:
      registry = StartedJobRegistry('default', connection=conn)
      q = Queue(connection=conn)
      return [Job.fetch(id, connection=conn) for id in registry.get_job_ids()]
  
  @classmethod
  def jobToDict(cls, job):
    """Returns job as dict"""
    if job == None:
      return {}
    else:
      return {
        'job_id': job.get_id(),
        'job_status': job.get_status(),
        'job_result': job.result,
        'job_meta': job.meta
      }
  
  @classmethod
  def getRunningExperiment(cls, experiment_id):
    """Gets the running job for experiment
    Args:
      experiment_id(str): id of experiment
    Returns:
      experiment(Job): is None if not currently running
    """
    jobs = cls.getRunningExperiments()
    for job in jobs:
      if job.get_status() != 'finished' and job.meta.get('experiment_id') == str(experiment_id):
        return job
    return None
  
  @classmethod
  def getTrials(cls, experiment_id):
    """Gets previous trials for experiment
    Args:
      experiment_id(str): id of experiment
    Returns:
      trials([]dict): List of trials in dict representation
    """
    session = cls.db_storage.Session()
    try:
      trials = cls.db_storage.getTrials(session, experiment_id)
      trials_dicts = [trial.asdict() for trial in trials]
    except:
      session.rollback()
      raise
    finally:
      session.close()
    return trials_dicts

  @classmethod
  def dictToExperiment(cls, experiment_dict):
    """Returns dict as Experiment
    Args:
      experiment_dict(dict): dictionary representation of Experiment
    Returns:
      experiment(Experiment): constructed Experiment
    """
    experiment_params = [Parameter(**param) for param in experiment_dict.pop('parameters')]
    if in_production:
      compute = EC2Compute(**experiment_dict.pop('compute'))
    else:
      compute = LocalCompute(**experiment_dict.pop('compute'))
    return Experiment(parameters=experiment_params, compute=compute, **experiment_dict)
  
  @classmethod
  def getOrCreateExperiment(cls, experiment_dict):
    """Get or create experiment from dict
    Args:
      experiment_dict(dict): dictionary representation of Experiment
    Returns:
      experiment(dict): new or fetched Experiment as a dict
    """
    experiment = cls.dictToExperiment(experiment_dict)
    session = cls.db_storage.Session()
    try:
      experiment, _, _ = cls.db_storage.getOrCreateExperiment(session, experiment)
      experiment_dict = experiment.asdict()
    except:
      session.rollback()
      raise
    finally:
      session.close()
    return experiment_dict
  
  @classmethod
  def getExperimentDict(cls, experiment_id):
    """Get experiment as a dict
    Args:
      experiment_id(str): id of experiment
    Returns:
      experiment(Experiment): dict of found experiment; None if not found
    """
    session = cls.db_storage.Session()
    try:
      experiment = cls.db_storage.getExperiment(session, experiment_id)
      experiment_dict = experiment.asdict() if experiment != None else None
    except:
      session.rollback()
      raise
    finally:
      session.close()
    return experiment_dict

  @classmethod
  def stopExperiment(cls, experiment_id):
    """Stops running an experiment
    Args:
      experiment_id(str): experiment to stop
    """
    return {'message': 'this functionality is not implemented yet'}

  @classmethod
  def _startRunner(cls, experiment_dict, optimizer):
    """Runs an experiment with paropt. This is the function used for job queueing

    Args:
      experiment_dict(dict): dict representation of experiment to run.
        Although it's a dict, the experiment it represents should already exist in the database.
      optimizer(Optimizer): Optimizer instance to use for running the experiment
    
    Returns:
      result(dict): result of the run
    
    Raises:
      Exception: when the runner fails, it will raise an exception with the message from the result
    """
    paropt.setConsoleLogger()
    experiment = cls.dictToExperiment(experiment_dict)
    storage = RelationalDB(
      'postgresql',
      DB_USER,
      DB_PASSWORD,
      DB_HOST,
      DB_NAME
    )

    po = ParslRunner(
      parsl_app=timeCmd,
      optimizer=optimizer,
      storage=storage,
      experiment=experiment,
      logs_root_dir='/var/log/paropt')
    po.run(debug=True)
    # cleanup launched instances
    po.cleanup()

    if po.run_result['success'] == False:
      raise Exception(po.run_result['message'])

    return po.run_result
