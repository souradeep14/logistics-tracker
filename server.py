#!/usr/bin/env python3
"""
Location Tracking Server
A simple Flask server to receive and store location data from the tracking webpage.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
import threading
import time

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# File to store location data
LOCATION_FILE = 'locations.json'

# In-memory storage for recent locations
recent_locations = []
max_locations = 1000  # Maximum number of locations to keep in memory

def load_locations():
    """Load existing locations from file"""
    global recent_locations
    if os.path.exists(LOCATION_FILE):
        try:
            with open(LOCATION_FILE, 'r') as f:
                recent_locations = json.load(f)
        except (json.JSONDecodeError, IOError):
            recent_locations = []
    else:
        recent_locations = []

def save_locations():
    """Save locations to file"""
    try:
        with open(LOCATION_FILE, 'w') as f:
            json.dump(recent_locations, f, indent=2)
    except IOError as e:
        print(f"Error saving locations: {e}")

def cleanup_old_locations():
    """Remove old locations to prevent memory issues"""
    global recent_locations
    if len(recent_locations) > max_locations:
        recent_locations = recent_locations[-max_locations:]
        save_locations()

@app.route('/location', methods=['POST', 'OPTIONS'])
def receive_location():
    """Receive location data from the tracking webpage"""
    
    # Handle preflight requests
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Get JSON data from request
        location_data = request.get_json()
        
        if not location_data:
            return jsonify({'error': 'No location data provided'}), 400
        
        # Validate required fields
        required_fields = ['latitude', 'longitude', 'timestamp']
        for field in required_fields:
            if field not in location_data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Add server timestamp
        location_data['server_timestamp'] = datetime.now().isoformat()
        
        # Add to recent locations
        recent_locations.append(location_data)
        
        # Cleanup old locations
        cleanup_old_locations()
        
        # Save to file (in background to not slow down response)
        threading.Thread(target=save_locations).start()
        
        # Log the received location
        print(f"Location received: {location_data['latitude']:.6f}, {location_data['longitude']:.6f} "
              f"(Accuracy: {location_data.get('accuracy', 'N/A')}m)")
        
        return jsonify({
            'status': 'success',
            'message': 'Location received and stored',
            'total_locations': len(recent_locations)
        }), 200
        
    except Exception as e:
        print(f"Error processing location: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/locations', methods=['GET'])
def get_locations():
    """Get all stored locations"""
    return jsonify({
        'status': 'success',
        'locations': recent_locations,
        'total_count': len(recent_locations)
    })

@app.route('/locations/latest', methods=['GET'])
def get_latest_location():
    """Get the most recent location"""
    if recent_locations:
        return jsonify({
            'status': 'success',
            'location': recent_locations[-1]
        })
    else:
        return jsonify({
            'status': 'no_data',
            'message': 'No locations available'
        }), 404

@app.route('/locations/clear', methods=['POST'])
def clear_locations():
    """Clear all stored locations"""
    global recent_locations
    recent_locations = []
    save_locations()
    return jsonify({
        'status': 'success',
        'message': 'All locations cleared'
    })

@app.route('/status', methods=['GET'])
def server_status():
    """Get server status information"""
    return jsonify({
        'status': 'running',
        'total_locations': len(recent_locations),
        'latest_location_time': recent_locations[-1]['timestamp'] if recent_locations else None,
        'server_time': datetime.now().isoformat()
    })

@app.route('/', methods=['GET'])
def index():
    """Basic server info"""
    return jsonify({
        'service': 'Location Tracking Server',
        'status': 'running',
        'endpoints': {
            'POST /location': 'Receive location data',
            'GET /locations': 'Get all locations',
            'GET /locations/latest': 'Get latest location',
            'POST /locations/clear': 'Clear all locations',
            'GET /status': 'Server status'
        }
    })

def periodic_cleanup():
    """Periodically cleanup old locations and save data"""
    while True:
        time.sleep(300)  # Run every 5 minutes
        cleanup_old_locations()

if __name__ == '__main__':
    print("🚀 Starting Location Tracking Server...")
    print("📍 Server will run on http://localhost:8000")
    print("🌐 Make sure to serve the HTML file from a web server")
    print("📊 Locations will be saved to:", os.path.abspath(LOCATION_FILE))
    
    # Load existing locations
    load_locations()
    print(f"📥 Loaded {len(recent_locations)} existing locations")
    
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
    cleanup_thread.start()
    
    try:
        # Run the Flask server
        app.run(host='0.0.0.0', port=8000, debug=True, threaded=True)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        save_locations()
        print("💾 Locations saved before exit")