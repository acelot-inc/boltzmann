import flask
import flask_wtf

from wtforms.fields     import StringField
from wtforms.validators import InputRequired

from ..models import db, Protein, Session

blueprint = flask.Blueprint('sessions', __name__)

class SessionForm(flask_wtf.FlaskForm):
    name = StringField('Name', validators=[InputRequired()])


@blueprint.route('', methods=['GET', 'POST'])
def index():
    form = SessionForm()
    if form.validate_on_submit():
        session = Session(name=form.name.data)
        db.session.add(session)
        db.session.commit()

        return flask.redirect(flask.url_for('sessions.show', session_id=session.id))

    sessions = Session.query.order_by(Session.name).all()
    return flask.render_template('sessions/index.html', sessions=sessions, form=form)

@blueprint.route('/<int:session_id>')
def show(session_id):
    session  = Session.query.get_or_404(session_id)
    proteins = Protein.query.all()
    return flask.render_template('sessions/show.html', session=session, proteins=proteins)
