import celery
import json
import traceback

from .models import db, Docking, Protein
from . import boltz

# https://stackoverflow.com/q/35664436
# Session = scoped_session(sessionmaker(bind=db.engine))

# celery_app = celery.Celery('tasks')
from .config import celery_app, flask_app

# @celery_app.task
# def add_protein(name, sequence):
#     folder = os.path.join(celery_app.root, 'sessions', '0')
#     config = boltz.config_for([
#         boltz.ProteinSequence(sequence, msa_file=protein.msa_file)
#     ])

#     # Get an MSA file from Boltz's default MSA server...
#     boltz.run(config, folder, name,
#         use_msa_server = True,
#         override       = True
#     )

#     # Copy the new MSA file to the proteins dorectory...
#     old_file = os.path.join(folder, 'output', 'boltz_results_' + name, 'msa', name + '_0.csv'),
#     new_file = os.path.join(celery_app.root, 'proteins', name + '.csv'),
#     shutil.copyfile(old_file, new_file)

#     # Add the protein to the DB!
#     protein = Protein(
#         name     = name,
#         sequence = sequence,
#         msa_file = new_file
#     )

#     db.session.add(protein)
#     db.session.commit()


@celery_app.task(queue='docking')
def dock(docking_id):
    docking = Docking.query.get(docking_id)
    protein = docking.protein

    docking.docking_status = 'running'
    db.session.add(docking)
    db.session.commit()

    try:
        config = boltz.config_for([
            boltz.ProteinSequence(protein.sequence, msa_file=protein.msa_file),
            boltz.SmilesSequence(docking.smiles)
        ])

        folder = flask_app.config['BOLTZ']['workdir']
        cache  = flask_app.config['BOLTZ']['cachedir']
        boltz.run(folder, docking.name, config, cache=cache)
        docking.docking_status = 'finished'
    except Exception as e:
        print(traceback.format_exc())
        docking.docking_status = 'failed'
        docking.scoring_status = 'canceled'
    db.session.add(docking)
    db.session.commit()

    # Queue up the scoring task...
    if docking.docking_status == 'finished':
        result = score.delay(docking_id)
        result.forget()


@celery_app.task(queue='scoring')
def score(docking_id):
    docking = Docking.query.get(docking_id)

    docking.scoring_status = 'running'
    db.session.add(docking)
    db.session.commit()

    try:
        folder = flask_app.config['BOLTZ']['workdir']
        scores = boltz.score_all(folder, docking.name)
        docking.scores = json.dumps(scores)
        docking.scoring_status = 'finished'
    except Exception as e:
        print(traceback.format_exc())
        docking.scoring_status = 'failed'
    db.session.add(docking)
    db.session.commit()
