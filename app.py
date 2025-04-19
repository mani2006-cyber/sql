from flask import Flask, render_template, request , jsonify
import psycopg2
from psycopg2 import pool
import atexit  # to clean up at app exit

app = Flask(__name__)

# Initialize connection pool globally
connection_pool = pool.SimpleConnectionPool(
    1, 20, "postgresql://postgres.jrkbymyasrgwhxlegahu:GhtLRCh7ALXsMbPN@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"
)

conn = connection_pool.getconn()

content = []

with conn.cursor() as cur:
    cur.execute('Select*from emp;')
    rows =cur.fetchall()
    for row in rows:
        print(type(row))
        content.append( {'id' : row[0] , 'name' : row[1] ,'dep' : row[2] })

@app.route('/')
def index():
    return render_template('index.html', content=content)

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/researcher')
def researcher():
    return render_template('researcher.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
