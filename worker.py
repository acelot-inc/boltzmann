import os

import boltzmann.config

confname = os.environ.get('BOLTZMANN_CONFIG')
if not confname:
    print('ERROR: Environment variable BOLTZMANN_CONFIG must be set.')
    exit(1)

config = boltzmann.config.get_config(confname)
boltzmann.config.configure(config)

flask_app  = boltzmann.config.flask_app
celery_app = boltzmann.config.celery_app
