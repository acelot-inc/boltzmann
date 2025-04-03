import celery
import flask
import json
import os


from .models import db

thisdir = os.path.dirname(__file__)


flask_app = flask.Flask('Boltzmann',
    template_folder = os.path.join(thisdir, 'templates'),
    static_folder   = os.path.join(thisdir, 'static')
)

class FlaskTask(celery.Task):
    def __call__(self, *args, **kwargs):
        with flask_app.app_context():
            return self.run(*args, **kwargs)

celery_app = celery.Celery(flask_app.name, task_cls=FlaskTask)
flask_app.extensions['celery'] = celery_app


def configure(config):
    flask_app.config['SQLALCHEMY_DATABASE_URI']        = config['database']
    flask_app.config['SECRET_KEY']                     = config['secret_key']
    flask_app.config['DEBUG']                          = config['debug']
    flask_app.config['DEVELOPMENT']                    = config['development']
    flask_app.config['TESTING']                        = config['testing']
    flask_app.config['WTF_CSRF_ENABLED']               = config['csrf']
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    flask_app.config['BOLTZ']  = config['boltz']
    flask_app.config['CELERY'] = config['celery']

    # Configure the DB...
    db.init_app(flask_app)
    flask_app.db = db

    # Configure the background workers...
    celery_app.config_from_object(flask_app.config['CELERY'])
    celery_app.set_default()

    # Avoid a (web -> tasks -> config) import cycle...
    from . import web

    # Attach some HTTP endpoints!
    flask_app.register_blueprint(web.apiv1.blueprint,    url_prefix='/api/v1')
    flask_app.register_blueprint(web.sessions.blueprint, url_prefix='/sessions')

    @flask_app.route('/')
    def root():
        return flask.redirect(flask.url_for('sessions.index'))


def get_config(name):
    if name == 'DEV':
        return {
            'database':     'sqlite:///dev.db',
            'secret_key':   'dev',
            'debug':        True,
            'development':  True,
            'testing':      False,
            'csrf':         True,
            'celery': {
                'broker_url':        'redis://localhost:6379/0',
                'result_backend':    'redis://localhost:6379/0',
                'task_ignore_result': True
            },
            'boltz': {
                'proteins': 'data/proteins/all.yml',
                'cachedir': '...',
                'workdir':  '...'
            }
        }
    if name == 'TEST':
        return {
            'database':     'sqlite:///test.db',
            'secret_key':   'test',
            'debug':        True,
            'development':  False,
            'testing':      True,
            'csrf':         False,
            'celery': {
                'broker_url':        'redis://localhost:6379/0',
                'result_backend':    'redis://localhost:6379/0',
                'task_ignore_result': True
            },
            'boltz': {
                'proteins': 'data/proteins/all.yml',
                'cachedir': '...',
                'workdir':  '...'
            }
        }
    with open(name) as file:
        return json.load(file)

def seed_db(db):
    pass
