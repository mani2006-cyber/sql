from flask import Flask, render_template, request ,session , jsonify , flash , redirect
import psycopg2
from psycopg2 import pool
import atexit  # to clean up at app exit

app = Flask(__name__)
app.secret_key = '567890'

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

@app.route('/edit')
def edit():
    table = request.args.get('table')
    record_id = request.args.get('id')

    rows, keys = database_table(table)

    content = None  # Make it a dict

    for row in rows:
        if row[0] == int(record_id):
            content = dict(zip(keys, row))
            break  # No need to keep looping

    return render_template('edit.html', table_name=table, content=content, keys=keys)

@app.route('/update', methods=['POST'])
def update():
    table = request.form.get('table')
    record_id = request.form.get('id')
    data = request.form.to_dict()
    data.pop('table')
    conn = get_db_connection()
    cur = conn.cursor()
    set_clause = ', '.join([f"{key} = %s" for key in data.keys()])
    cur.execute(f"UPDATE {table} SET {set_clause} WHERE id = %s", list(data.values()) + [record_id])
    conn.commit()
    cur.close()
    connection_pool.putconn(conn)
    flash('Record updated successfully!', 'success')
    if table == 'researcher_view':
        return redirect('/dashboard?table=researcher')
    return redirect('/dashboard?table=' + table)

@app.route('/deletee')
def deletee():
    table = request.args.get('table')
    record_id = int(request.args.get('id'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM {table} WHERE id = %s", (record_id,))
    conn.commit()
    cur.close()
    connection_pool.putconn(conn)

    flash('Record deleted successfully!', 'success')
    return redirect(f'/dashboard?table={table}')

@app.route('/view')
def view():
    table = request.args.get('table')
    record_id = request.args.get('id')
    conn = get_db_connection()
    cur = conn.cursor()

    # Correcting the query syntax
    cur.execute(f"SELECT * FROM researcher as r JOIN researcher_view as v ON r.id = v.id WHERE v.id = %s", (record_id,))

    row = cur.fetchone()  # Fetch the first matching record
    keys = [desc[0] for desc in cur.description]  # Get column names
    cur.close()
    connection_pool.putconn(conn)

    # Combine keys and row data into a dictionary
    content = dict(zip(keys, row))

    # Pass content and keys to the template for rendering
    return render_template('view.html', table_name = table, content=content, keys=keys)

@app.route('/back')
def back():
    table = request.args.get('table')
    return redirect(f'/dashboard?table={table}')

@app.route('/add')
def add():
    table = request.args.get('table')
    rows , keys = database_table(table)
    return render_template('add.html' , table_name = table , keys = keys)

form_tree = {
    'researcher': ['researcher_view'],
    'researcher_view': [],
    'experiment': ['lab', 'equipment', 'chemical', 'chemical_usage'],
    'lab': [],
    'equipment': [],
    'chemical': [],
    'chemical_usage': []
}

def post(tables, data_list):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        for table, data in zip(tables, data_list):
            if not data:  # Skip if no data
                continue
            keys = data.keys()
            values = [str(v) if v is not None else None for v in data.values()]
            placeholders = ', '.join(['%s'] * len(keys))
            query = f"INSERT INTO {table} ({', '.join(keys)}) VALUES ({placeholders})"
            cur.execute(query, list(values))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        connection_pool.putconn(conn)

@app.route('/addrow', methods=['GET', 'POST'])
def addrow():
    table = request.args.get('table')
    if request.method == 'POST':
        table = request.form.get('table', table)  # Get table from form data if available
    if not table:
        flash('No table specified', 'error')
        return redirect('/')

    if request.method == 'POST':
        # Handle form submission
        data = request.form.to_dict()
        next_tables = form_tree.get(table, [])

        # Store current data in session for multi-step forms
        if 'form_data' not in session:
            session['form_data'] = {}
        session['form_data'][table] = data

        # Check if there are more steps
        if next_tables:
            next_table = next_tables[0]  # Get first child table
            rows, keys = database_table(next_table)
            is_last = len(next_tables) == 1 and not form_tree.get(next_table, [])
            return render_template('add.html', 
                                table_name=next_table, 
                                keys=keys,
                                is_last=is_last,
                                current_step=next_table)
        else:
            # Final submission - collect all data from session
            all_tables = []
            all_data = []

            # Determine the root table (the first one in the hierarchy)
            root_table = table
            while True:
                found = False
                for k, v in form_tree.items():
                    if root_table in v:
                        root_table = k
                        found = True
                        break
                if not found:
                    break

            # Collect all data in hierarchy order
            tables_to_process = [root_table]
            while tables_to_process:
                current = tables_to_process.pop(0)
                if current in session.get('form_data', {}):
                    all_tables.append(current)
                    all_data.append(session['form_data'][current])
                tables_to_process.extend(form_tree.get(current, []))

            # Post all data
            post(all_tables, all_data)

            # Clear session data
            session.pop('form_data', None)

            flash('Record added successfully!', 'success')
            return redirect(f'/dashboard?table={root_table}')

    # GET request - show form for current table
    rows, keys = database_table(table)
    next_tables = form_tree.get(table, [])
    is_last = not bool(next_tables)
    return render_template('add.html', 
                         table_name=table, 
                         keys=keys,
                         is_last=is_last,
                         current_step=table)
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
