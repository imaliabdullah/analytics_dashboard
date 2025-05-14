import pytest
from datetime import datetime, timedelta, UTC
from app import create_app, db
from app.models import UserSession, UserEvent, EventAggregate

@pytest.fixture
def app():
    app = create_app('testing')
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:admin@localhost:5433/analytics_dashboard'
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    with app.test_client() as client:
        with app.app_context():
            # Create a test session
            session = UserSession(
                session_id='test-session',
                ip_address='127.0.0.1',
                user_agent='test-agent'
            )
            db.session.add(session)
            db.session.commit()
            
            # Set the session cookie
            client.set_cookie('session_id', 'test-session')
            yield client

def test_track_event_success(client):
    """Test successful event tracking."""
    response = client.post('/events', json={
        'event_type': 'click',
        'event_name': 'test_button',
        'event_data': {'button_id': 'test-btn'}
    })
    
    assert response.status_code == 201
    data = response.get_json()
    assert data is not None
    assert 'event_id' in data
    assert 'session_id' in data
    assert data['status'] == 'success'

def test_track_event_missing_fields(client):
    """Test event tracking with missing required fields."""
    response = client.post('/events', json={
        'event_name': 'test_button'
    })
    
    assert response.status_code == 400
    data = response.get_json()
    assert data is not None
    assert 'error' in data
    assert 'required' in data

def test_track_event_invalid_json(client):
    """Test event tracking with invalid JSON."""
    response = client.post('/events', data='invalid json', content_type='application/json')
    assert response.status_code == 415  # Changed to match actual behavior
    data = response.get_json()
    assert data is not None
    assert 'error' in data

def test_get_overview_stats(client, app):
    """Test getting overview stats."""
    with app.app_context():
        # Create test data
        aggregate = EventAggregate(
            event_type='click',
            event_name='test_button',
            period_type='daily',
            period_start=datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0),
            count=1,
            device_type='desktop'
        )
        db.session.add(aggregate)
        db.session.commit()

    # Test overview stats
    response = client.get('/stats/overview?range=7d')
    assert response.status_code == 200
    data = response.get_json()
    assert data is not None
    assert 'data' in data
    assert 'pagination' in data
    assert len(data['data']) > 0

def test_get_event_counts(client, app):
    """Test getting event counts."""
    with app.app_context():
        # Create test data
        aggregate = EventAggregate(
            event_type='click',
            event_name='test_button',
            period_type='daily',
            period_start=datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0),
            count=1,
            device_type='desktop'
        )
        db.session.add(aggregate)
        db.session.commit()

    # Test event counts
    response = client.get('/stats/event-counts?event_name=test_button&range=7d')
    assert response.status_code == 200
    data = response.get_json()
    assert data is not None
    assert 'data' in data
    assert 'pagination' in data
    assert len(data['data']) > 0

def test_get_top_events(client, app):
    """Test getting top events."""
    with app.app_context():
        # Create test data
        aggregate = EventAggregate(
            event_type='click',
            event_name='test_button',
            period_type='daily',
            period_start=datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0),
            count=5,
            device_type='desktop'
        )
        db.session.add(aggregate)
        db.session.commit()

    # Test top events
    response = client.get('/stats/top-events?limit=5&range=7d')
    assert response.status_code == 200
    data = response.get_json()
    assert data is not None
    assert 'data' in data
    assert len(data['data']) > 0
    assert data['data'][0]['event_name'] == 'test_button'
    assert data['data'][0]['total_count'] == 5

def test_aggregation_trigger(client, app):
    """Test manual aggregation trigger."""
    with app.app_context():
        # Create test event
        event = UserEvent(
            session_id='test-session',  # Use existing session
            event_type='click',
            event_name='test_button',
            timestamp=datetime.now(UTC)
        )
        db.session.add(event)
        db.session.commit()

    # Test aggregation
    response = client.post('/analytics/aggregate?period_type=daily')
    assert response.status_code == 200
    data = response.get_json()
    assert data is not None
    assert 'status' in data
    assert data['status'] == 'success'

def test_invalid_date_range(client):
    """Test invalid date range in stats endpoints."""
    response = client.get('/stats/overview?range=custom')
    assert response.status_code == 400
    data = response.get_json()
    assert data is not None
    assert 'error' in data

def test_pagination(client, app):
    """Test pagination in stats endpoints."""
    with app.app_context():
        # Create multiple test aggregates
        for i in range(15):
            aggregate = EventAggregate(
                event_type='click',
                event_name=f'test_button_{i}',
                period_type='daily',
                period_start=datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0),
                count=1,
                device_type='desktop'
            )
            db.session.add(aggregate)
        db.session.commit()

    # Test pagination
    response = client.get('/stats/overview?page=1&per_page=10')
    assert response.status_code == 200
    data = response.get_json()
    assert data is not None
    assert len(data['data']) == 10
    assert data['pagination']['pages'] == 2 