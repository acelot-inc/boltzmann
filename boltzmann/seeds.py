import glob
import os

from .config import flask_app
from .models import db, Protein

def readfile(path):
    with open(path) as file:
        return file.read()

def seed():
    with flask_app.app_context():
        pattern  = flask_app.config['BOLTZ_PROTEINS'] + '/*'
        proteins = []
        for path in glob.glob(pattern):
            db.session.add(Protein(
                name     = readfile(path + '/name.txt').strip(),
                sequence = readfile(path + '/sequence.txt').strip(),
                style    = readfile(path + '/style.json'),
                msa_file = os.path.basename(path) + '/msa.csv'
            ))

        db.session.commit()
