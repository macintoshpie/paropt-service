import psycopg2.extras
import globus_sdk
import psycopg2
import os
import urllib.request

from parsl.launchers import SingleNodeLauncher
from parsl.channels import SSHInteractiveLoginChannel, LocalChannel
from parsl.providers import CobaltProvider, LocalProvider, AWSProvider
from parsl.config import Config
from parsl.executors import HighThroughputExecutor
from parsl.executors.ipp import IPyParallelExecutor
from parsl.executors.ipp_controller import Controller

in_production = True if os.getenv('PROD') != None else False
if in_production:
  print("Fetching Public IP from instance metadata...")
  public_ip = urllib.request.urlopen("http://169.254.169.254/latest/meta-data/public-ipv4").read().decode()
else:
  public_ip = os.getenv('PUBLIC_IP')

def getAWSConfig():
  return Config(
    executors=[
      HighThroughputExecutor(
        label='htex_local',
        address=public_ip,
        cores_per_worker=1,
        max_workers=2,
        provider=AWSProvider(
          image_id='ami-073e3f122e47832bf', # image with bio tools installed 
          worker_init='pip3 install git+https://git@github.com/macintoshpie/paropt',
          region='us-east-2',
          key_name='testKeyPair',
          profile="default",
          state_file='awsproviderstate.json',
          nodes_per_block=1,
          init_blocks=2,
          max_blocks=2,
          min_blocks=0,
          walltime='01:00:00',
        ),
      )
    ],
    strategy=None,
  )

GLOBUS_KEY = os.environ.get('globus_key')
GLOBUS_CLIENT = os.environ.get('globus_client')

SECRET_KEY = os.environ.get('secret_key')

DB_HOST = os.environ.get('DB_HOST')
DB_USER = os.environ.get('DB_USER')
DB_NAME = os.environ.get('DB_NAME')
DB_PASSWORD = os.environ.get('DB_PASSWORD')
DB_TABLE = 'parslTestC'

_prod = in_production

def _get_db_connection():
  """
  Establish a database connection
  """
  con_str = "dbname={dbname} user={dbuser} password={dbpass} host={dbhost}".format(dbname=DB_NAME, dbuser=DB_USER,
                                                                                    dbpass=DB_PASSWORD, dbhost=DB_HOST)

  conn = psycopg2.connect(con_str)
  cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

  return conn, cur

def _load_funcx_client():
  """
  Create an AuthClient for the portal
  """
  if _prod:
      app = globus_sdk.ConfidentialAppAuthClient(GLOBUS_CLIENT,
                                                  GLOBUS_KEY)
  else:
      app = globus_sdk.ConfidentialAppAuthClient('', '')
  return app
