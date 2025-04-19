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


def get_db_connection():
    try:
        conn = connection_pool.getconn()
        if conn is None:
            raise Exception("failed to get connection from pool")
        return conn
    except Exception as e:
        print(f'Error getting connection from pool: {e}')

def database_table(name):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {name}")
    rows = cur.fetchall()
    keys = [desc[0] for desc in cur.description]
    cur.close()
    connection_pool.putconn(conn)
    return rows , keys
    
@app.route('/')
def index():
    return render_template('index.html' ,  content =None  , keys = None)

@app.route('/dashboard')
def dashboard():
    table = request.args.get('table')
    content = []
    rows ,keys = database_table(table)
    for row in rows:
        content.append(dict(zip(keys, row)))
    return render_template('index.html'  , table_name = table ,content = content ,keys=keys)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
