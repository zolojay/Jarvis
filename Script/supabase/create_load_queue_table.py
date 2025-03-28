# create_load_queue_table.py
# Run this once to create the load_queue table in Supabase with explicit schema

from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text

SUPABASE_CONN = "postgresql://postgres:pqALDR^EPhi5hE@db.annkdlllotvqnmbaedor.supabase.co:5432/postgres"
engine = create_engine(SUPABASE_CONN)
metadata = MetaData()

# Define the table schema
load_queue = Table(
    "load_queue",
    metadata,
    Column("load_id", Integer, primary_key=True),
    Column("status", String(50)),
    Column("testing_area", String(50)),
    Column("priority", Integer),
    Column("description", Text),
    Column("pcn", String(50)),
    Column("job", String(50)),
    Column("request_type", String(50)),
    Column("username", String(50)),
    Column("lab_request_number", String(50)),
)

# Create the table if it doesn't exist
metadata.create_all(engine)

print("✅ Supabase table 'load_queue' is ready.")
