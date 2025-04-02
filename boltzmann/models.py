import flask_sqlalchemy
import json


db = flask_sqlalchemy.SQLAlchemy()

def boltz_name(docking_id):
    return 'job' + str(docking_id)

class Docking(db.Model):
    __tablename__ = 'dockings'

    id             = db.Column(db.Integer, primary_key=True)
    protein_id     = db.Column(db.Integer, db.ForeignKey('proteins.id'), nullable=False)
    smiles         = db.Column(db.String, nullable=False)

    docking_status = db.Column(db.String, nullable=False, default='pending')
    scoring_status = db.Column(db.String, nullable=False, default='pending')
    scores         = db.Column(db.Text) # JSON blob!

    # Relationships
    protein = db.Relationship('Protein', uselist=False)

    @property
    def name(self):
        return boltz_name(self.id)


class Job(db.Model):
    __tablename__ = 'jobs'

    id         = db.Column(db.Integer, primary_key=True)
    docking_id = db.Column(db.Integer, db.ForeignKey('dockings.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id'), nullable=False)
    name       = db.Column(db.String, nullable=False)

    # Relationships
    docking = db.Relationship('Docking', uselist=False)
    session = db.Relationship('Session', uselist=False)


    def model_path(self, model_id):
        name   = boltz_name(self.docking_id)
        models = boltz.models_folder_for(name)

        return os.path.join(models, '%s_model_%d.cif' % (name, model_id))

    def to_json(self):
        return {
            'id':      self.id,
            'session': self.session.name,
            'name':    self.name,

            'protein': self.docking.protein.name,
            'smiles':  self.docking.smiles,
            'docking': self.docking.docking_status,
            'scoring': self.docking.scoring_status,
            'scores':  json.loads(self.docking.scores) if self.docking.scores else None
        }


class Protein(db.Model):
    __tablename__ = 'proteins'

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String,  nullable=False)
    sequence   = db.Column(db.String,  nullable=False)
    msa_file   = db.Column(db.String,  nullable=False)
    style      = db.Column(db.String)

    @property
    def style_data(self):
        return json.loads(self.style)

class Session(db.Model):
    __tablename__ = 'sessions'

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String,  nullable=False)

    # Relationships
    jobs = db.Relationship('Job', back_populates='session')
