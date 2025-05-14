from datetime import datetime
from app import db

class UserSession(db.Model):
    __tablename__ = 'user_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), nullable=True)
    session_id = db.Column(db.String(50), unique=True, nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)
    user_agent = db.Column(db.Text, nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    events = db.relationship('UserEvent', backref='session', lazy=True)

    def __repr__(self):
        return f'<UserSession {self.session_id}>'

class UserEvent(db.Model):
    __tablename__ = 'user_events'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(50), db.ForeignKey('user_sessions.session_id'), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    event_name = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    event_data = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<UserEvent {self.event_type}:{self.event_name}>'

class EventAggregate(db.Model):
    __tablename__ = 'event_aggregates'

    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(50), nullable=False)
    event_name = db.Column(db.String(100), nullable=False)
    period_type = db.Column(db.String(20), nullable=False)  # daily, weekly, monthly
    period_start = db.Column(db.DateTime, nullable=False)
    count = db.Column(db.Integer, default=0)
    device_type = db.Column(db.String(50), nullable=True)  # mobile, desktop, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('event_type', 'event_name', 'period_type', 'period_start', 'device_type', 
                          name='unique_event_aggregate'),
    )

    def __repr__(self):
        return f'<EventAggregate {self.event_type}:{self.event_name} {self.period_type}>'
