import boltzmann.config

config = boltzmann.config.get_config('DEV')
boltzmann.config.configure(config)

flask_app  = boltzmann.config.flask_app
celery_app = boltzmann.config.celery_app
