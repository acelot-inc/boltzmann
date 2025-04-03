import glob
import json
import os
import yaml

from .config import flask_app
from .models import db, Protein

def seed():
    if Protein.query.count() > 0:
        print('Proteins already exist; skipping...')
        return

    root = os.path.dirname(flask_app.config['BOLTZ']['proteins'])
    with open(flask_app.config['BOLTZ']['proteins']) as file:
        data = yaml.safe_load(file)

    for protein in data['proteins']:
        db.session.add(Protein(
            name     = protein['name'],
            sequence = protein['sequence'],
            style    = json.dumps(protein['style']),
            msa_file = os.path.join(protein['msa_file'], root)
        ))

    db.session.commit()
