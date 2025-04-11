import boltzmann.config
import os

config_name = os.environ.get('BOLTZMANN_CONFIG')
if config_name is None:
    print('ERROR: Environment variable BOLTZMANN_CONFIG must be specified.')
    exit(1)

config = boltzmann.config.get_config(config_name)
boltzmann.config.configure(config)

flask_app  = boltzmann.config.flask_app
celery_app = boltzmann.config.celery_app
