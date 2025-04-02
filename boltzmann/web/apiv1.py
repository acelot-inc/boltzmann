import flask

from ..tasks  import dock
from ..models import db, Docking, Job, Protein, Session

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
    jobs = Job.query.filter_by(session_id=session_id).all()
    return {job.id: job.to_json() for job in jobs}

@blueprint.route('/sessions/<int:session_id>/jobs', methods=['POST'])
def enqueue(session_id):
    session = Session.query.get_or_404(session_id)
    print(flask.request.data)

    jobs  = []
    tasks = []
    info  = flask.request.get_json()
    print(info)

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
        jobs.append(job)

    # IDs get assigned here:
    db.session.commit()

    for task in tasks:
        result = dock.delay(task.id)
        result.forget()

    return {job.id: job.to_json() for job in jobs}

@blueprint.route('/sessions/<int:session_id>/jobs/<int:job_id>/models/<int:model_id>')
def model(session_id, job_id, model_id):
    job = Job.query.filter_by(session_id=session_id).get_or_404(job_id)
    if job.status not in ('scoring', 'finished', 'scoring-failed'):
        return 404

    path = os.path.join(app.root, job.model_path(model_id))
    return flask.send_file(path, mimetype='chemical/x-mmcif')
