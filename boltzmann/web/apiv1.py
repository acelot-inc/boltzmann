import flask

from ..tasks  import dock
from ..models import db, Docking, Job, Protein, Session
from ..boltz  import model_path

# @blueprint.route('/queue')
# def queue():
#     jobs = Job.query.order(Job.id).all()
#     return [job.to_json() for job in jobs]

blueprint = flask.Blueprint('apiv1', __name__)

@blueprint.route('/sessions/<int:session_id>/job/<int:job_id>')
def job(session_id, job_id):
    job = Job.query.filter_by(session_id=session_id).get_or_404(job_id)
    return job.to_json()

@blueprint.route('/sessions/<int:session_id>/jobs')
def jobs(session_id):
    # jobs = Job.query.filter_by(session_id=session_id).all()
    # return {job.id: job.to_json() for job in jobs}
    return session(session_id)

@blueprint.route('/sessions/<int:session_id>/jobs', methods=['POST'])
def enqueue(session_id):
    session = Session.query.get_or_404(session_id)
    # print(flask.request.data)

    # jobs  = []
    tasks = []
    info  = flask.request.get_json()
    # print(info)

    for data in info:
        protein = Protein.query.get_or_404(data['protein_id'])
        smiles  = data['smiles']
        jobname = data['name']

        docking = Docking.query.filter_by(
            protein = protein,
            smiles  = smiles
        ).first()

        if docking is None:
            docking = Docking(protein=protein, smiles=smiles)
            tasks.append(docking)

        job = Job(
            session = session,
            docking = docking,
            name    = jobname
        )

        db.session.add(job)
        # jobs.append(job)

    # IDs get assigned here:
    db.session.commit()

    for task in tasks:
        result = dock.delay(task.id)
        result.forget()

    return jobs(session_id)

@blueprint.route('/sessions/<int:session_id>/jobs/<int:job_id>/models/<int:model_id>')
def model(session_id, job_id, model_id):
    job = Job.query.filter_by(session_id=session_id, id=job_id).first_or_404()
    if job.docking.docking_status != 'finished':
        return 404

    # if model_id >= job.diffusion_samples:
    #     return 404

    root = flask.current_app.config['BOLTZ']['workdir']
    path = model_path(root, job.docking.name, model_id)
    # return flask.send_file(path, mimetype='chemical/x-mmcif')
    return flask.send_file(path, mimetype='chemical/pdb')

@blueprint.route('/sessions/<int:session_id>')
def session(session_id):
    query = Docking.query.with_entities(
        Docking.id
    ).filter(
        Docking.scoring_status == 'pending'
    ).order_by(
        Docking.id
    )

    docking_queue = query.all()
    scoring_queue = query.filter(Docking.docking_status != 'pending').all()

    docking_place = {d.id:i for i, d in enumerate(docking_queue, 1)}
    scoring_place = {d.id:i for i, d in enumerate(scoring_queue, 1)}

    jobs = Job.query.filter_by(session_id=session_id).all()
    info = {
        'queues': {
            'docking': len(docking_queue),
            'scoring': len(scoring_queue)
        },
        'jobs': {}
    }

    for job in jobs:
        json = job.to_json()
        json['place'] = docking_place.get(job.docking_id)
        if json['place'] is None:
            json['place'] = scoring_place.get(job.docking_id)
        info['jobs'][job.id] = json

    return info
