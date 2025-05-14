from flask import Blueprint, request, jsonify, make_response
from app.services import track_event, get_or_create_session, aggregate_events
from app.models import UserSession, UserEvent, EventAggregate
from datetime import datetime, timedelta, UTC
from sqlalchemy import func, desc
from app import db

bp = Blueprint('main', __name__)

@bp.before_request
def before_request():
    """Middleware to ensure session exists for all requests."""
    if not request.cookies.get('session_id'):
        session = get_or_create_session()
        response = make_response()
        response.set_cookie('session_id', session.session_id, max_age=30*24*60*60)  # 30 days
        return response

@bp.route('/events', methods=['POST'])
def track_user_event():
    """Endpoint to track user events."""
    if not request.is_json:
        return jsonify({
            'error': 'Content-Type must be application/json'
        }), 415
        
    try:
        data = request.get_json()
    except Exception:
        return jsonify({
            'error': 'Invalid JSON data'
        }), 415
    
    # Validate required fields
    required_fields = ['event_type', 'event_name']
    if not all(field in data for field in required_fields):
        return jsonify({
            'error': 'Missing required fields',
            'required': required_fields
        }), 400
    
    try:
        event = track_event(
            event_type=data['event_type'],
            event_name=data['event_name'],
            event_data=data.get('event_data')
        )
        
        return jsonify({
            'status': 'success',
            'event_id': event.id,
            'session_id': event.session_id
        }), 201
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to track event',
            'message': str(e)
        }), 500

@bp.route('/stats/overview', methods=['GET'])
def get_overview_stats():
    """Get daily stats for a given period."""
    range_type = request.args.get('range', '7d')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    
    # Calculate date range
    end_date = datetime.now(UTC)
    if range_type == '7d':
        start_date = end_date - timedelta(days=7)
    elif range_type == '30d':
        start_date = end_date - timedelta(days=30)
    else:
        # Custom range
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        if not start_date or not end_date:
            return jsonify({'error': 'start_date and end_date required for custom range'}), 400
        start_date = datetime.fromisoformat(start_date)
        end_date = datetime.fromisoformat(end_date)

    # Query daily aggregates
    query = EventAggregate.query.filter(
        EventAggregate.period_type == 'daily',
        EventAggregate.period_start >= start_date,
        EventAggregate.period_start <= end_date
    )

    # Apply filters
    event_type = request.args.get('event_type')
    device_type = request.args.get('device_type')
    if event_type:
        query = query.filter_by(event_type=event_type)
    if device_type:
        query = query.filter_by(device_type=device_type)

    # Get total count for pagination
    total = query.count()
    
    # Apply sorting
    sort_by = request.args.get('sort_by', 'period_start')
    sort_order = request.args.get('sort_order', 'desc')
    if sort_order == 'desc':
        query = query.order_by(desc(sort_by))
    else:
        query = query.order_by(sort_by)

    # Apply pagination
    paginated_query = query.paginate(page=page, per_page=per_page)
    
    return jsonify({
        'status': 'success',
        'data': [{
            'date': agg.period_start.date().isoformat(),
            'event_type': agg.event_type,
            'event_name': agg.event_name,
            'count': agg.count,
            'device_type': agg.device_type
        } for agg in paginated_query.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': paginated_query.pages
        }
    })

@bp.route('/stats/event-counts', methods=['GET'])
def get_event_counts():
    """Get aggregated counts for specific events."""
    event_name = request.args.get('event_name')
    if not event_name:
        return jsonify({'error': 'event_name is required'}), 400

    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    
    # Calculate date range
    range_type = request.args.get('range', '7d')
    end_date = datetime.now(UTC)
    if range_type == '7d':
        start_date = end_date - timedelta(days=7)
    elif range_type == '30d':
        start_date = end_date - timedelta(days=30)
    else:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        if not start_date or not end_date:
            return jsonify({'error': 'start_date and end_date required for custom range'}), 400
        start_date = datetime.fromisoformat(start_date)
        end_date = datetime.fromisoformat(end_date)

    # Query aggregates
    query = EventAggregate.query.filter(
        EventAggregate.event_name == event_name,
        EventAggregate.period_start >= start_date,
        EventAggregate.period_start <= end_date
    )

    # Apply filters
    event_type = request.args.get('event_type')
    device_type = request.args.get('device_type')
    if event_type:
        query = query.filter_by(event_type=event_type)
    if device_type:
        query = query.filter_by(device_type=device_type)

    # Get total count
    total = query.count()
    
    # Apply sorting
    sort_by = request.args.get('sort_by', 'period_start')
    sort_order = request.args.get('sort_order', 'desc')
    if sort_order == 'desc':
        query = query.order_by(desc(sort_by))
    else:
        query = query.order_by(sort_by)

    # Apply pagination
    paginated_query = query.paginate(page=page, per_page=per_page)
    
    return jsonify({
        'status': 'success',
        'data': [{
            'period_start': agg.period_start.isoformat(),
            'period_type': agg.period_type,
            'count': agg.count,
            'device_type': agg.device_type
        } for agg in paginated_query.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': paginated_query.pages
        }
    })

@bp.route('/stats/top-events', methods=['GET'])
def get_top_events():
    """Get top N most triggered events."""
    limit = int(request.args.get('limit', 10))
    range_type = request.args.get('range', '7d')
    
    # Calculate date range
    end_date = datetime.now(UTC)
    if range_type == '7d':
        start_date = end_date - timedelta(days=7)
    elif range_type == '30d':
        start_date = end_date - timedelta(days=30)
    else:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        if not start_date or not end_date:
            return jsonify({'error': 'start_date and end_date required for custom range'}), 400
        start_date = datetime.fromisoformat(start_date)
        end_date = datetime.fromisoformat(end_date)

    # Query top events
    top_events = db.session.query(
        EventAggregate.event_type,
        EventAggregate.event_name,
        func.sum(EventAggregate.count).label('total_count')
    ).filter(
        EventAggregate.period_start >= start_date,
        EventAggregate.period_start <= end_date
    ).group_by(
        EventAggregate.event_type,
        EventAggregate.event_name
    ).order_by(
        desc('total_count')
    ).limit(limit).all()
    
    return jsonify({
        'status': 'success',
        'data': [{
            'event_type': event.event_type,
            'event_name': event.event_name,
            'total_count': event.total_count
        } for event in top_events]
    })

@bp.route('/analytics/aggregate', methods=['POST'])
def trigger_aggregation():
    """Manually trigger event aggregation."""
    period_type = request.args.get('period_type', 'daily')
    
    if period_type not in ['daily', 'weekly', 'monthly']:
        return jsonify({
            'error': 'Invalid period type. Must be one of: daily, weekly, monthly'
        }), 400
        
    try:
        # Check if there are any events to aggregate
        event_count = UserEvent.query.count()
        if event_count == 0:
            return jsonify({
                'status': 'warning',
                'message': 'No events found to aggregate'
            }), 200
            
        # Run aggregation synchronously for testing
        aggregate_events(period_type)
        
        # Verify aggregation results
        aggregate_count = EventAggregate.query.filter_by(period_type=period_type).count()
        
        return jsonify({
            'status': 'success',
            'message': f'Aggregation completed for {period_type} period',
            'period_type': period_type,
            'total_events': event_count,
            'aggregated_groups': aggregate_count
        }), 200
    except Exception as e:
        return jsonify({
            'error': 'Failed to trigger aggregation',
            'message': str(e)
        }), 500


