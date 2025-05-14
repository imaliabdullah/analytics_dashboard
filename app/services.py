import uuid
from datetime import datetime, timedelta, UTC
from flask import request
from app import db, celery
from app.models import UserSession, UserEvent, EventAggregate
from sqlalchemy import func
import re
import json
from celery.schedules import crontab

def get_or_create_session():
    """Get or create a user session."""
    session_id = request.cookies.get('session_id')
    if session_id:
        session = UserSession.query.filter_by(session_id=session_id).first()
        if session:
            return session
    
    # Create new session
    session = UserSession(
        session_id=session_id,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string,
        start_time=datetime.now(UTC)
    )
    db.session.add(session)
    db.session.commit()
    return session

def track_event(event_type, event_name, event_data=None):
    """Track a user event."""
    session = get_or_create_session()
    
    event = UserEvent(
        session_id=session.session_id,
        event_type=event_type,
        event_name=event_name,
        event_data=json.dumps(event_data) if event_data else None,
        timestamp=datetime.now(UTC)
    )
    
    db.session.add(event)
    db.session.commit()
    return event

def get_device_type(user_agent):
    """Simple device detection from user agent."""
    mobile_pattern = re.compile(r'mobile|android|iphone|ipad|ipod', re.IGNORECASE)
    return 'mobile' if mobile_pattern.search(user_agent) else 'desktop'

@celery.task
def aggregate_events(period_type='daily'):
    """Aggregate events into period buckets."""
    try:
        # Get the start of the current period
        now = datetime.now(UTC)
        if period_type == 'daily':
            period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period_type == 'weekly':
            # Start from the beginning of the week (Monday)
            period_start = now - timedelta(days=now.weekday())
            period_start = period_start.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period_type == 'monthly':
            # Start from the beginning of the month
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            raise ValueError(f"Unsupported period type: {period_type}")
        
        # Query events for aggregation
        events = UserEvent.query.filter(
            UserEvent.timestamp >= period_start
        ).all()
        
        if not events:
            print(f"No events found for period {period_type} starting at {period_start}")
            return
        
        # Group events by type, name, and device
        event_groups = {}
        for event in events:
            session = UserSession.query.filter_by(session_id=event.session_id).first()
            if not session:
                continue
                
            device_type = get_device_type(session.user_agent)
            
            key = (event.event_type, event.event_name, device_type)
            if key not in event_groups:
                event_groups[key] = 0
            event_groups[key] += 1
        
        # Create or update aggregates
        for (event_type, event_name, device_type), count in event_groups.items():
            # Check if aggregate already exists for this period
            aggregate = EventAggregate.query.filter_by(
                event_type=event_type,
                event_name=event_name,
                period_type=period_type,
                period_start=period_start,
                device_type=device_type
            ).first()
            
            if aggregate:
                # Update existing aggregate
                aggregate.count += count
                print(f"Updated aggregate for {event_type}/{event_name}: {count} events")
            else:
                # Create new aggregate
                aggregate = EventAggregate(
                    event_type=event_type,
                    event_name=event_name,
                    period_type=period_type,
                    period_start=period_start,
                    count=count,
                    device_type=device_type
                )
                db.session.add(aggregate)
                print(f"Created new aggregate for {event_type}/{event_name}: {count} events")
        
        db.session.commit()
        print(f"Successfully aggregated {len(event_groups)} event groups for {period_type} period")
        
    except Exception as e:
        db.session.rollback()
        print(f"Error during aggregation: {str(e)}")
        raise e

# Schedule periodic tasks
@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Daily aggregation at midnight
    sender.add_periodic_task(
        crontab(hour=0, minute=0),
        aggregate_events.s('daily')
    )
    
    # Weekly aggregation on Monday at midnight
    sender.add_periodic_task(
        crontab(day_of_week=1, hour=0, minute=0),  # 1 = Monday
        aggregate_events.s('weekly')
    )
    
    # Monthly aggregation on 1st at midnight
    sender.add_periodic_task(
        crontab(day_of_month=1, hour=0, minute=0),
        aggregate_events.s('monthly')
    )
