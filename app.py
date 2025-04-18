from flask import Flask, render_template, request
import psycopg2
from psycopg2 import pool
import os
from flask import jsonify

app = Flask(__name__)

# Create a connection pool with Supabase configuration
connection_pool = pool.SimpleConnectionPool(
    1, 20,
    host="jrkbymyasrgwhxlegahu.supabase.co",
    database="postgres",
    user="postgres",
    password="GhtLRCh7ALXsMbPN",
    port=5432
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
            conn.commit()  # Add commit to ensure transaction completion
            rows = cur.fetchall()
            for row in rows:
                print(f"Row data: {row}")  # Debug print
                content.append({'name': row[1]})  # Assuming name is in second column
            print(f"Content to display: {content}")  # Debug print
            cur.close()
            connection_pool.putconn(conn)
        except Exception as e:
            print(f"Database error: {e}")
            if conn:
                connection_pool.putconn(conn)

    return render_template('index.html', content=content)

# Only close individual connections, not the entire pool
@app.teardown_appcontext
def cleanup(error):
    pass

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)