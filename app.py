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
    cur.execute(f'SELECT * FROM "{name}"')
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

    if not table or not record_id:
        flash('Missing table or record ID', 'error')
        return redirect('/dashboard')

    try:
        rows, keys = database_table(table)
        content = None

        for row in rows:
            if str(row[0]) == str(record_id):  # Compare as strings to avoid type issues
                content = dict(zip(keys, row))
                break

        if not content:
            flash('Record not found', 'error')
            return redirect(f'/dashboard?table={table}')

        return render_template('edit.html', 
                            table_name=table, 
                            content=content, 
                            keys=keys)
    except Exception as e:
        flash(f'Error retrieving record: {str(e)}', 'error')
        return redirect(f'/dashboard?table={table}')

@app.route('/update', methods=['POST'])
def update():
    table = request.form.get('table')
    record_id = request.form.get('id')
    id_key = request.form.get('id_key')

    if not all([table, record_id, id_key]):
        flash('Missing required parameters', 'error')
        return redirect('/dashboard')

    try:
        data = request.form.to_dict()
        # Remove metadata fields
        for field in ['table', 'id', 'id_key']:
            data.pop(field, None)

        # Get column info to validate
        conn = get_db_connection()
        cur = conn.cursor()

        # Get column types for proper value handling
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = %s
        """, (table,))
        column_types = {row[0]: row[1] for row in cur.fetchall()}

        # Prepare update data
        set_clauses = []
        values = []
        for key, value in data.items():
            if key in column_types:
                # Handle empty values based on column type
                if value == '':
                    if column_types[key] in ('date', 'timestamp without time zone'):
                        value = None
                    elif column_types[key] in ('integer', 'numeric'):
                        value = None if value == '' else value

                set_clauses.append(f'"{key}" = %s')
                values.append(value)

        if not set_clauses:
            flash('No valid fields to update', 'error')
            return redirect(f'/dashboard?table={table}')

        # Add record ID for WHERE clause
        values.append(record_id)

        query = f'UPDATE "{table}" SET {", ".join(set_clauses)} WHERE "{id_key}" = %s'
        cur.execute(query, values)
        conn.commit()

        flash('Record updated successfully!', 'success')
        return redirect(f'/dashboard?table={table}')

    except Exception as e:
        conn.rollback()
        flash(f'Error updating record: {str(e)}', 'error')
        return redirect(f'/edit?table={table}&id={record_id}')
    finally:
        cur.close()
        connection_pool.putconn(conn)

@app.route('/deletee')
def deletee():
    id_name = request.args.get('id_key')
    table = request.args.get('table')
    record_id = int(request.args.get('id'))

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(f'DELETE FROM "{table}" WHERE "{id_name}" = %s', (record_id,))
        conn.commit()
        flash('Record deleted successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting record: {str(e)}', 'error')
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
    'experiment': ['chemical_usage'],
    'lab': [],
    'equipment': [],
    'chemical': [],
    'chemical_usage': [],
    'Maintenance' :[]
}

def post(tables, data_list):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        for table, data in zip(tables, data_list):
            if not data:  # Skip if no data
                continue

            # Create a copy of the data dictionary and remove non-column fields
            data_copy = data.copy()

            # Remove special fields that shouldn't be inserted into the table
            for field in ['table', 'action']:
                if field in data_copy:
                    del data_copy[field]

            # Get the actual column names from the database
            cur.execute(f'SELECT column_name FROM information_schema.columns WHERE table_name = %s', (table,))
            valid_columns = [row[0] for row in cur.fetchall()]

            # Filter out any keys that aren't actual columns in the table
            filtered_data = {k: v for k, v in data_copy.items() if k in valid_columns}

            if not filtered_data:
                continue

            keys = filtered_data.keys()
            values = [str(v) if v is not None else None for v in filtered_data.values()]
            placeholders = ', '.join(['%s'] * len(keys))
            quoted_keys = [f'"{k}"' for k in keys]

            query = f'INSERT INTO "{table}" ({", ".join(quoted_keys)}) VALUES ({placeholders})'
            cur.execute(query, list(values))

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        flash(f'Error saving data: {str(e)}', 'error')
        return False
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
