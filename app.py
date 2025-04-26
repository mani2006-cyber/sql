from flask import Flask, render_template, request ,session , jsonify , flash , redirect
import psycopg2
from psycopg2 import pool
import atexit  
import os

app = Flask(__name__)
app.secret_key = '567890'

my_secret = os.environ['DB_CONNECTION_STRING']


connection_pool = pool.SimpleConnectionPool(
    1, 20, my_secret
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
            if str(row[0]) == str(record_id):  
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
        
        for field in ['table', 'id', 'id_key']:
            data.pop(field, None)

        
        conn = get_db_connection()
        cur = conn.cursor()

        
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = %s
        """, (table,))
        column_types = {row[0]: row[1] for row in cur.fetchall()}

        
        set_clauses = []
        values = []
        for key, value in data.items():
            if key in column_types:
               
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
    return redirect(f'/dashboard?table={table}')

@app.route('/view')
def view():
    table = request.args.get('table')
    record_id = request.args.get('id')
    name_column = request.args.get('name')

    if table == 'experiment':
        view_table = 'experiment_view'
    elif table == 'researcher':
        view_table = 'researcher_view'
    else:
        return "Invalid table name", 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        query = f"""
            SELECT * FROM {view_table} AS r
            JOIN {table} AS v ON r.{name_column} = v.{name_column}
            WHERE v.{name_column} = %s
        """
        cur.execute(query, (record_id,))
        row = cur.fetchone()

        if row is None:
            return "No record found", 404

        keys = [desc[0] for desc in cur.description]
        content = dict(zip(keys, row))

        cur.close()
        connection_pool.putconn(conn)

        if table == 'experiment':
            return render_template('experiment_view.html', experiment=content ,keys=keys)
        elif table == 'researcher':
            return render_template('view.html', content=content , keys=keys)

    except Exception as e:
        return f"Error: {str(e)}", 500

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
    'experiment': ['experiment_view' , 'chemical_usage'],
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
            if not data: 
                continue

            data_copy = data.copy()

            for field in ['table', 'action']:
                if field in data_copy:
                    del data_copy[field]

            cur.execute(f'SELECT column_name FROM information_schema.columns WHERE table_name = %s', (table,))
            valid_columns = [row[0] for row in cur.fetchall()]

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
        table = request.form.get('table', table) 
    if not table:
        flash('No table specified', 'error')
        return redirect('/')

    if request.method == 'POST':
        
        data = request.form.to_dict()
        next_tables = form_tree.get(table, [])

        if 'form_data' not in session:
            session['form_data'] = {}
        session['form_data'][table] = data

        
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
