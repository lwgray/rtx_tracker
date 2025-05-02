"""
Monitoring state management for RTX 5090 Stock Tracker
"""

import os
import json
import datetime
from utils.logger import get_logger

# Get logger
logger = get_logger(__name__)

# Default state values
DEFAULT_STATE = {
    "monitoring_active": True,
    "interval_minutes": 60,
    "price_threshold": 2500,
    "last_run": None,
    "next_run": None
}

STATE_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "monitoring_state.json")

def load_monitoring_state():
    """Load monitoring state from file"""
    try:
        if os.path.exists(STATE_FILE_PATH):
            with open(STATE_FILE_PATH, 'r') as f:
                state = json.load(f)
                
                # Convert string timestamps to datetime objects if they exist
                if state.get('last_run'):
                    state['last_run'] = datetime.datetime.fromisoformat(state['last_run'])
                if state.get('next_run'):
                    state['next_run'] = datetime.datetime.fromisoformat(state['next_run'])
                
                logger.debug(f"Loaded monitoring state: {state}")
                return state
        else:
            # Return default if file doesn't exist yet
            logger.info("Monitoring state file not found, using default values")
            save_monitoring_state(DEFAULT_STATE)
            return DEFAULT_STATE.copy()
    except Exception as e:
        logger.error(f"Error loading monitoring state: {e}")
        return DEFAULT_STATE.copy()

def save_monitoring_state(state):
    """Save monitoring state to file"""
    try:
        # Convert datetime objects to ISO format strings for JSON serialization
        state_copy = state.copy()
        if state_copy.get('last_run') and isinstance(state_copy['last_run'], datetime.datetime):
            state_copy['last_run'] = state_copy['last_run'].isoformat()
        if state_copy.get('next_run') and isinstance(state_copy['next_run'], datetime.datetime):
            state_copy['next_run'] = state_copy['next_run'].isoformat()
        
        with open(STATE_FILE_PATH, 'w') as f:
            json.dump(state_copy, f, indent=2)
        
        logger.debug(f"Saved monitoring state: {state_copy}")
        return True
    except Exception as e:
        logger.error(f"Error saving monitoring state: {e}")
        return False

def update_monitoring_interval(minutes):
    """Update the monitoring interval"""
    try:
        state = load_monitoring_state()
        state['interval_minutes'] = int(minutes)
        
        # Update next_run based on new interval if monitoring is active
        if state['monitoring_active'] and state.get('last_run'):
            last_run = state['last_run'] if isinstance(state['last_run'], datetime.datetime) else \
                datetime.datetime.fromisoformat(state['last_run'])
            state['next_run'] = last_run + datetime.timedelta(minutes=state['interval_minutes'])
        
        save_monitoring_state(state)
        logger.info(f"Updated monitoring interval to {minutes} minutes")
        return True
    except Exception as e:
        logger.error(f"Error updating monitoring interval: {e}")
        return False

def update_price_threshold(threshold):
    """Update the price alert threshold"""
    try:
        state = load_monitoring_state()
        state['price_threshold'] = float(threshold)
        save_monitoring_state(state)
        logger.info(f"Updated price threshold to ${threshold}")
        return True
    except Exception as e:
        logger.error(f"Error updating price threshold: {e}")
        return False

def toggle_monitoring_status():
    """Toggle the monitoring active state"""
    try:
        state = load_monitoring_state()
        state['monitoring_active'] = not state['monitoring_active']
        
        # If activating, set next_run
        if state['monitoring_active']:
            now = datetime.datetime.now()
            state['next_run'] = now + datetime.timedelta(minutes=state['interval_minutes'])
        else:
            state['next_run'] = None
        
        save_monitoring_state(state)
        logger.info(f"Toggled monitoring active state to {state['monitoring_active']}")
        return state['monitoring_active']
    except Exception as e:
        logger.error(f"Error toggling monitoring status: {e}")
        return None

def update_run_timestamps(last_run=None, calculate_next=True):
    """Update the last run and next run timestamps"""
    try:
        state = load_monitoring_state()
        
        if last_run:
            state['last_run'] = last_run
        else:
            state['last_run'] = datetime.datetime.now()
        
        if calculate_next and state['monitoring_active']:
            state['next_run'] = state['last_run'] + datetime.timedelta(minutes=state['interval_minutes'])
        
        save_monitoring_state(state)
        logger.debug(f"Updated run timestamps: last={state['last_run']}, next={state['next_run']}")
        return True
    except Exception as e:
        logger.error(f"Error updating run timestamps: {e}")
        return False