
from flask import Flask, render_template, request
import psycopg2
import os
from flask import jsonify

app = Flask(__name__)

def get_db_connection():
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            conn = psycopg2.connect(
                host="db.jrkbymyasrgwhxlegahu.supabase.co",
                database="postgres",
                user="postgres",
                password="GhtLRCh7ALXsMbPN",
                port=5432,
                connect_timeout=30,
                tcp_keepalives=1,
                application_name='my_flask_app'
            )
            print("Database connection successful!")
            return conn
        except psycopg2.OperationalError as e:
            retry_count += 1
            print(f"Attempt {retry_count} failed. Retrying...")
            if retry_count == max_retries:
                print(f"Failed to connect after {max_retries} attempts: {e}")
                return None
    except psycopg2.OperationalError as e:
        print(f"Error connecting to database: {e}")
        return None

@app.route('/')
def index():
    conn = get_db_connection()
    content = []
    
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM emp;")
            rows = cur.fetchall()
            for row in rows:
                content.append({'name': row[1]})  # Assuming name is in second column
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Database error: {e}")
            
    return render_template('index.html', content=content)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
