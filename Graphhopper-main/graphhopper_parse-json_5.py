from flask import Flask, render_template, request, session, redirect, url_for
import requests
import urllib.parse
import folium
import polyline
import os
from datetime import datetime

# Initialize the Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key'

# GraphHopper API details
route_url = "https://graphhopper.com/api/1/route?"
key = "fec63287-65f6-43b4-99e6-30b7330312b5"  # Replace with your GraphHopper API key

# Available vehicle options, add vehicle options here
valid_vehicles = ['car', 'bike', 'foot', 'scooter', 'truck']

# Function to perform geocoding
def geocoding(location, key):
    geocode_url = "https://graphhopper.com/api/1/geocode?"
    url = geocode_url + urllib.parse.urlencode({"q": location, "limit": "1", "key": key})
    
    replydata = requests.get(url)
    json_data = replydata.json()
    json_status = replydata.status_code
    
    if json_status == 200 and len(json_data["hits"]) != 0:
        lat = json_data["hits"][0]["point"]["lat"]
        lng = json_data["hits"][0]["point"]["lng"]
        name = json_data["hits"][0]["name"]
        state = json_data["hits"][0].get("state", "")
        country = json_data["hits"][0].get("country", "")
        new_loc = f"{name}, {state}, {country}" if state else name
    else:
        lat, lng, new_loc = "null", "null", location
    
    return json_status, lat, lng, new_loc

# Flask route for the homepage
@app.route('/')
def index():
    return render_template('index.html')  # Render the homepage where user will input details

# Flask route to handle form submission and generate the map
@app.route('/route', methods=['POST'])
def route():
    vehicle = request.form.get('vehicle', 'car')  # Default to 'car'
    loc1 = request.form['start_location']
    loc2 = request.form['end_location']
    unit = request.form.get('unit', 'km')  # Get the selected unit
    travel_date = request.form.get('date', '')  # Travel date input

    # Validate and convert date if present
    if travel_date:
        try:
            travel_datetime = datetime.strptime(travel_date, '%Y-%m-%d %H:%M:%S')  # Example format
        except ValueError:
            return "Invalid date format. Please use YYYY-MM-DD HH:MM:SS", 400
    else:
        travel_datetime = datetime.now()  # Default to current date/time if not provided

    orig = geocoding(loc1, key)
    dest = geocoding(loc2, key)

    if orig[0] == 200 and dest[0] == 200:
        op = f"&point={orig[1]}%2C{orig[2]}"
        dp = f"&point={dest[1]}%2C{dest[2]}"
        paths_url = route_url + urllib.parse.urlencode({"key": key, "vehicle": vehicle}) + op + dp
        paths_data = requests.get(paths_url).json()

        if "paths" in paths_data and len(paths_data["paths"]) > 0:
            distance_km = paths_data["paths"][0]["distance"] / 1000
            duration_sec = paths_data["paths"][0]["time"] / 1000
            hr, min = divmod(duration_sec // 60, 60)

            # Convert distance based on selected unit
            if unit == 'miles':
                distance = distance_km * 0.621371  # Convert km to miles
            elif unit == 'yards':
                distance = distance_km * 1094.0  # Convert km to yards
            elif unit == 'meters':
                distance = distance_km * 1000  # Convert km to meters
            else:
                distance = distance_km  # Kilometers (default)

            # Create route map
            decoded_points = polyline.decode(paths_data["paths"][0]["points"])
            m = folium.Map(location=[orig[1], orig[2]], zoom_start=10)
            folium.PolyLine(decoded_points).add_to(m)

            # Ensure the 'static' directory exists
            static_dir = 'static'
            if not os.path.exists(static_dir):
                os.makedirs(static_dir)

            # Save map to 'static/route_map.html'
            map_path = os.path.join(static_dir, 'route_map.html')
            m.save(map_path)

            # Prepare data to render in HTML
            trip_data = {
                'orig': orig[3],
                'dest': dest[3],


                'distance': f"{distance:.2f} {unit}",  # Display distance with selected unit
                'duration': f"{int(hr)} hr {int(min)} min",
                'map_url': map_path,
                'travel_datetime': travel_datetime.strftime('%Y-%m-%d %H:%M:%S')  # Include travel date/time

            }
            return render_template('route.html', trip_data=trip_data)

        else:
            return "No valid paths found. Please try with a different vehicle or locations.", 400
    else:
        return "Error in geocoding. Check your inputs.", 400

@app.route('/toggle_theme')
def toggle_theme():
    current_theme = session.get('theme', 'light')
    session['theme'] = 'dark' if current_theme == 'light' else 'light'
    return redirect(request.referrer or url_for('index'))

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True, port=5001)