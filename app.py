import psycopg2

# Your connection string with actual password filled in
conn = psycopg2.connect(
    host="db.jrkbymyasrgwhxlegahu.supabase.co",
    database="postgres",
    user="postgres",
    password="GhtLRCh7ALXsMbPN",  # Replace this with your actual DB password
    port=5432
)

# Create a cursor to interact with the database
cur = conn.cursor()

# Example query (change 'your_table' to your actual table name)
cur.execute("SELECT * FROM emp;")

# Fetch and print all results
rows = cur.fetchall()
for row in rows:
    print(row)

# Close the cursor and connection
cur.close()
conn.close()
