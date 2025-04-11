import argparse
import boltzmann.config

parser = argparse.ArgumentParser()
parser.add_argument('-b', '--bind', type=str, default='127.0.0.1')
parser.add_argument('-p', '--port', type=int, default=1381)
parser.add_argument('--create-db',  action='store_true')
parser.add_argument('config', nargs='?', default='DEV')
args = parser.parse_args()


config = boltzmann.config.get_config(args.config)
boltzmann.config.configure(config)

flask_app  = boltzmann.config.flask_app
celery_app = boltzmann.config.celery_app

if args.create_db:
    with flask_app.app_context():
        flask_app.db.create_all()
        from boltzmann import seeds
        seeds.seed()
    print('Database initialized.')
    exit(0)


flask_app.run(host=args.bind, port=args.port)
