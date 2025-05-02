"""
Admin routes for RTX 5090 Stock Tracker
"""

import datetime
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from database.db import get_session
from database.models import Retailer, Product, PriceHistory, StockHistory
from database.monitoring_state import (
    load_monitoring_state, 
    update_monitoring_interval, 
    update_price_threshold,
    toggle_monitoring_status
)
from services.monitoring import run_monitoring_now, restart_monitoring
from sqlalchemy import func

# Create blueprint
admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin')
def admin_dashboard():
    """Admin dashboard view"""
    session = get_session()
    
    try:
        # Get all retailers
        retailers = session.query(Retailer).all()
        
        # Get product and history counts
        products_count = session.query(func.count(Product.id)).scalar()
        price_records_count = session.query(func.count(PriceHistory.id)).scalar()
        stock_records_count = session.query(func.count(StockHistory.id)).scalar()
        
        # Get monitoring state
        state = load_monitoring_state()
        monitoring_active = state.get('monitoring_active', True)
        current_interval = state.get('interval_minutes', 60)
        price_threshold = state.get('price_threshold', 2500)
        
        # Format timestamps for display
        last_run_time = state.get('last_run')
        next_run_time = state.get('next_run')
        
        # Format for template
        if isinstance(last_run_time, str):
            try:
                last_run_time = datetime.datetime.fromisoformat(last_run_time)
            except ValueError:
                last_run_time = "Never"
        
        if isinstance(next_run_time, str):
            try:
                next_run_time = datetime.datetime.fromisoformat(next_run_time)
            except ValueError:
                next_run_time = "Not scheduled"
        
        # Get current year for copyright
        current_year = datetime.datetime.now().year
        
        return render_template(
            'admin.html',
            retailers=retailers,
            products_count=products_count,
            price_records_count=price_records_count,
            stock_records_count=stock_records_count,
            monitoring_active=monitoring_active,
            current_interval=current_interval,
            price_threshold=price_threshold,
            last_run_time=last_run_time,
            next_run_time=next_run_time,
            current_year=current_year
        )
    
    finally:
        session.close()

@admin_bp.route('/admin/settings', methods=['POST'])
def update_settings():
    """Update monitoring settings"""
    try:
        # Get form data
        monitoring_interval = request.form.get('monitoring_interval', 60)
        price_threshold = request.form.get('price_threshold', 2500)
        
        # Validate input
        try:
            monitoring_interval = int(monitoring_interval)
            if monitoring_interval < 5:
                monitoring_interval = 5
            elif monitoring_interval > 1440:
                monitoring_interval = 1440
        except ValueError:
            monitoring_interval = 60
        
        try:
            price_threshold = float(price_threshold)
            if price_threshold < 0:
                price_threshold = 0
        except ValueError:
            price_threshold = 2500
        
        # Update settings
        update_monitoring_interval(monitoring_interval)
        update_price_threshold(price_threshold)
        
        # Restart monitoring with new settings
        restart_monitoring()
        
        # Flash success message
        flash('Settings updated successfully!', 'success')
        
    except Exception as e:
        flash(f'Error updating settings: {e}', 'danger')
    
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/admin/toggle_retailer', methods=['POST'])
def toggle_retailer():
    """Toggle retailer active status"""
    session = get_session()
    
    try:
        retailer_id = request.form.get('retailer_id')
        
        if retailer_id:
            retailer = session.query(Retailer).get(retailer_id)
            if retailer:
                retailer.active = not retailer.active
                session.commit()
                flash(f'Retailer {retailer.name} {"enabled" if retailer.active else "disabled"} successfully!', 'success')
            else:
                flash('Retailer not found', 'danger')
        else:
            flash('Retailer ID not provided', 'danger')
    
    except Exception as e:
        flash(f'Error toggling retailer: {e}', 'danger')
        session.rollback()
    
    finally:
        session.close()
    
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/admin/run_now', methods=['POST'])
def trigger_monitoring():
    """Run monitoring now"""
    success = run_monitoring_now()
    return jsonify({'success': success})

@admin_bp.route('/admin/toggle_monitoring', methods=['POST'])
def toggle_monitoring():
    """Toggle monitoring active state"""
    try:
        new_state = toggle_monitoring_status()
        restart_monitoring()
        return jsonify({'success': True, 'active': new_state})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})