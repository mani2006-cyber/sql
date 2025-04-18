from flask import Flask, render_template, request
import psycopg2
from psycopg2 import pool
import os
from flask import jsonify

app = Flask(__name__)

# Create a connection pool
connection_pool = pool.SimpleConnectionPool(
    1, 20,
    host="aws-0-ap-south-1.pooler.supabase.com",
    database="postgres",
    user="postgres.jrkbymyasrgwhxlegahu",
    password="GhtLRCh7ALXsMbPN",
    port=6543
)

def get_db_connection():
    try:
        conn = connection_pool.getconn()
        print("Database connection successful!")
        return conn
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
            connection_pool.putconn(conn)
        except Exception as e:
            print(f"Database error: {e}")
            if conn:
                connection_pool.putconn(conn)

    return render_template('index.html', content=content)

# Clean up the connection pool when the application stops
@app.teardown_appcontext
def close_pool(error):
    if connection_pool:
        connection_pool.closeall()

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)