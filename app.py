
from flask import Flask, render_template, jsonify
import requests

app = Flask(__name__)

# Your Supabase credentials
SUPABASE_URL = "https://jrkbymyasrgwhxlegahu.supabase.co"
SUPABASE_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpyaWJ5bXlhc3JndmFuZGxlZ2FodSIsInJvbGUiOiJhbm9uIiwiaWF0IjoxNzA5NzI5NzUwLCJleHAiOjIwMjUzMDU3NTB9.GhtLRCh7ALXsMbPN"

@app.route('/')
def index():
    headers = {
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
        "Content-Type": "application/json"
    }

    # Call the 'emp' table
    url = f"{SUPABASE_URL}/rest/v1/emp?select=*"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise error for bad status codes
        data = response.json()
        print("Data fetched:", data)
        return render_template("index.html", content=data)
    except requests.exceptions.RequestException as e:
        print("Error fetching data:", e)
        return jsonify({"error": "Could not fetch data"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
