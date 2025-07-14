#!/usr/bin/env python3
"""
Location Map Viewer
Displays tracked locations on an OpenStreetMap using folium.
Can run in both one-time view mode and live tracking mode.
"""

import folium
import json
import requests
import time
import webbrowser
import os
from datetime import datetime
from typing import List, Dict, Optional
import argparse

class LocationMapViewer:
    def __init__(self, server_url: str = "http://localhost:8000", 
                 output_file: str = "tracking_map.html",
                 local_file: str = "locations.json"):
        self.server_url = server_url
        self.output_file = output_file
        self.local_file = local_file
        self.last_location_count = 0
        
    def get_locations_from_server(self) -> Optional[List[Dict]]:
        """Fetch locations from the tracking server"""
        try:
            response = requests.get(f"{self.server_url}/locations", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('locations', [])
            else:
                print(f"❌ Server responded with status {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Could not connect to server: {e}")
            return None
    
    def get_locations_from_file(self) -> Optional[List[Dict]]:
        """Load locations from local JSON file"""
        try:
            if os.path.exists(self.local_file):
                with open(self.local_file, 'r') as f:
                    locations = json.load(f)
                return locations
            else:
                print(f"❌ File {self.local_file} not found")
                return None
        except (json.JSONDecodeError, IOError) as e:
            print(f"❌ Error reading file: {e}")
            return None
    
    def get_locations(self) -> Optional[List[Dict]]:
        """Get locations from server first, fallback to file"""
        locations = self.get_locations_from_server()
        if locations is None:
            print("🔄 Trying to load from local file...")
            locations = self.get_locations_from_file()
        return locations
    
    def create_map(self, locations: List[Dict]) -> folium.Map:
        """Create a folium map with the given locations"""
        if not locations:
            # Default map centered on a generic location
            center_lat, center_lon = 13.0827, 80.2707  # Chennai, India
            m = folium.Map(location=[center_lat, center_lon], zoom_start=10)
            
            # Add a message for no data
            folium.Marker(
                [center_lat, center_lon],
                popup="No tracking data available yet",
                icon=folium.Icon(color='red', icon='info-sign')
            ).add_to(m)
            
            return m
        
        # Calculate center point
        lats = [loc['latitude'] for loc in locations]
        lons = [loc['longitude'] for loc in locations]
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        
        # Create map
        m = folium.Map(location=[center_lat, center_lon], zoom_start=13)
        
        # Add path line if multiple locations
        if len(locations) > 1:
            path_coords = [[loc['latitude'], loc['longitude']] for loc in locations]
            folium.PolyLine(
                path_coords,
                color='blue',
                weight=3,
                opacity=0.8,
                popup=f"Tracking Path ({len(locations)} points)"
            ).add_to(m)
        
        # Add markers for each location
        for i, location in enumerate(locations):
            lat = location['latitude']
            lon = location['longitude']
            timestamp = location.get('timestamp', 'Unknown')
            accuracy = location.get('accuracy', 'Unknown')
            
            # Format timestamp
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                time_str = timestamp
            
            # Different icons for first, last, and middle points
            if i == 0:
                icon_color = 'green'
                icon_symbol = 'play'
                popup_text = f"🏁 START<br>Time: {time_str}<br>Accuracy: {accuracy}m"
            elif i == len(locations) - 1:
                icon_color = 'red'
                icon_symbol = 'stop'
                popup_text = f"📍 CURRENT<br>Time: {time_str}<br>Accuracy: {accuracy}m<br>Lat: {lat:.6f}<br>Lon: {lon:.6f}"
            else:
                icon_color = 'blue'
                icon_symbol = 'record'
                popup_text = f"📌 Point {i+1}<br>Time: {time_str}<br>Accuracy: {accuracy}m"
            
            folium.Marker(
                [lat, lon],
                popup=folium.Popup(popup_text, max_width=200),
                icon=folium.Icon(color=icon_color, icon=icon_symbol)
            ).add_to(m)
        
        # Add summary information
        if locations:
            latest = locations[-1]
            summary_html = f"""
            <div style='font-family: Arial; font-size: 14px;'>
                <h4>📊 Tracking Summary</h4>
                <b>Total Points:</b> {len(locations)}<br>
                <b>Latest Update:</b> {time_str}<br>
                <b>Current Location:</b> {latest['latitude']:.6f}, {latest['longitude']:.6f}<br>
                <b>Map Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </div>
            """
            
            folium.Marker(
                [center_lat + 0.001, center_lon + 0.001],
                popup=folium.Popup(summary_html, max_width=300),
                icon=folium.Icon(color='darkgreen', icon='info-sign')
            ).add_to(m)
        
        return m
    
    def generate_map(self) -> bool:
        """Generate and save the map"""
        print("🗺️  Generating map...")
        
        locations = self.get_locations()
        if locations is None:
            print("❌ No location data available")
            return False
        
        print(f"📍 Found {len(locations)} location points")
        
        # Create the map
        m = self.create_map(locations)
        
        # Save the map
        m.save(self.output_file)
        print(f"✅ Map saved as {self.output_file}")
        
        return True
    
    def live_tracking(self, refresh_interval: int = 10, auto_open: bool = True):
        """Run live tracking with automatic map updates"""
        print(f"🔴 Starting live tracking mode (refresh every {refresh_interval}s)")
        print("Press Ctrl+C to stop")
        
        # Generate initial map
        if self.generate_map() and auto_open:
            webbrowser.open(f"file://{os.path.abspath(self.output_file)}")
        
        try:
            while True:
                time.sleep(refresh_interval)
                
                locations = self.get_locations()
                if locations and len(locations) != self.last_location_count:
                    print(f"🔄 Update detected: {len(locations)} locations (was {self.last_location_count})")
                    self.generate_map()
                    self.last_location_count = len(locations)
                else:
                    print("⏱️  No new locations...")
                    
        except KeyboardInterrupt:
            print("\n🛑 Live tracking stopped")

def main():
    parser = argparse.ArgumentParser(description='Location Tracking Map Viewer')
    parser.add_argument('--mode', choices=['once', 'live'], default='once',
                        help='Run mode: generate map once or live tracking')
    parser.add_argument('--server', default='http://localhost:8000',
                        help='Server URL (default: http://localhost:8000)')
    parser.add_argument('--output', default='tracking_map.html',
                        help='Output HTML file (default: tracking_map.html)')
    parser.add_argument('--file', default='locations.json',
                        help='Local JSON file to read from (default: locations.json)')
    parser.add_argument('--interval', type=int, default=10,
                        help='Refresh interval for live mode in seconds (default: 10)')
    parser.add_argument('--no-open', action='store_true',
                        help='Don\'t automatically open the map in browser')
    
    args = parser.parse_args()
    
    viewer = LocationMapViewer(
        server_url=args.server,
        output_file=args.output,
        local_file=args.file
    )
    
    if args.mode == 'once':
        print("📍 Single map generation mode")
        if viewer.generate_map():
            if not args.no_open:
                webbrowser.open(f"file://{os.path.abspath(args.output)}")
                print(f"🌐 Map opened in browser: {args.output}")
        else:
            print("❌ Failed to generate map")
    
    elif args.mode == 'live':
        viewer.live_tracking(
            refresh_interval=args.interval,
            auto_open=not args.no_open
        )

if __name__ == '__main__':
    print("🗺️  Location Tracking Map Viewer")
    print("=" * 40)
    main()