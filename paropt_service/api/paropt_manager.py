import multiprocessing
import atexit
import os
import time

from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, in_production, getAWSConfig

import parsl

import paropt
from paropt.runner import ParslRunner
from paropt.storage import LocalFile, RelationalDB
from paropt.optimizer import BayesianOptimizer, GridSearch
from paropt.runner.parsl import timeCmd
from paropt.storage.entities import Parameter, Experiment, EC2Compute, LocalCompute

def getOptimizer(optimizer_config):
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
  _started = False
  _cleanup_proc = None
  _running_experiments = {}
  _finished_experiments = multiprocessing.Queue()
  db_storage = None
  session = None

  @classmethod
  def start(cls):
    if cls._started:
      return
    atexit.register(cls._stop)
    cls.db_storage = RelationalDB(
      'postgresql',
      DB_USER,
      DB_PASSWORD,
      DB_HOST,
      DB_NAME
    )
    cls.session = cls.db_storage.Session()
    cls._started = True
  
  @classmethod
  def _stop(cls):
    # find other children and stop them
    for child in multiprocessing.active_children():
      child.terminate()

  @classmethod
  def runTrials(cls, experiment_id, run_config):
    if not cls._started:
      raise Exception("ParoptManager not started")
      
    # clear out the finished queue while we're here
    cls._clearQueue()
    
    # check if experiment is already running
    experiment_proc = cls._running_experiments.get(experiment_id, None)
    if experiment_proc != None and experiment_proc.is_alive():
      return True, "experiment already running"

    experiment = cls.getExperiment(experiment_id)
    if experiment == None:
      return False, "Experiment not found with id {}".format(id)
    
    optimizer = getOptimizer(run_config.get('optimizer'))
    if optimizer == None:
      return False, "Invalid run configuration provided"
    
    x = multiprocessing.Process(target=cls._startRunner, args=[experiment.asdict(), optimizer, cls._finished_experiments], name="Runner-123")
    x.start()
    cls._running_experiments[experiment_id] = x
    return True, "started experiment"

  @classmethod
  def _clearQueue(cls):
    while not cls._finished_experiments.empty():
      old_experiment_id = str(cls._finished_experiments.get(False))
      proc = cls._running_experiments.pop(old_experiment_id, None)
      if proc != None:
        assert proc.is_alive() == False

  @classmethod
  def getRunningExperiments(cls):
    cls._clearQueue()
    return list(cls._running_experiments.keys())
  
  @classmethod
  def isRunning(cls, experiment_id):
    cls._clearQueue()
    return None != cls._running_experiments.get(str(experiment_id))
  
  @classmethod
  def getTrials(cls, experiment_id):
    trials = cls.db_storage.getTrials(cls.session, experiment_id)
    return [trial.asdict() for trial in trials]

  @classmethod
  def dictToExperiment(cls, experiment_dict):
    experiment_params = [Parameter(**param) for param in experiment_dict.pop('parameters')]
    if in_production:
      compute = EC2Compute(**experiment_dict.pop('compute'))
    else:
      compute = LocalCompute(**experiment_dict.pop('compute'))
    return Experiment(parameters=experiment_params, compute=compute, **experiment_dict)
  
  @classmethod
  def getOrCreateExperiment(cls, experiment_dict):
    experiment = cls.dictToExperiment(experiment_dict)
    print("experiment dict: ", experiment_dict)
    print('CREATED EXPERIMENT: ', experiment)
    db_storage = RelationalDB(
      'postgresql',
      DB_USER,
      DB_PASSWORD,
      DB_HOST,
      DB_NAME
    )
    return db_storage.getOrCreateExperiment(cls.session, experiment)
  
  @classmethod
  def getExperiment(cls, experiment_id):
    return cls.db_storage.getExperiment(cls.session, experiment_id)

  @classmethod
  def stopExperiment(cls, experiment_id):
    cls._clearQueue()
    exp = cls._running_experiments.get(experiment_id, None)
    if exp != None:
      exp.terminate()
      cls._running_experiments.pop(experiment_id)
      return {'message': "stopped running experiment {}".format(experiment_id)}
    return {'message': "experiment {} not already running".format(experiment_id)}

  @classmethod
  def _startRunner(cls, experiment_dict, optimizer, finish_queue):
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
    finish_queue.put(experiment.id)

