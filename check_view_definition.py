"""
Check the view definition for vw_PowerBI_AI_Technical_Combos
to understand why AMD's recent signals are being filtered out.
"""
import pyodbc
from config.settings import (
    SQL_SERVER,
    SQL_DATABASE,
    SQL_DRIVER,
    SQL_USERNAME,
    SQL_PASSWORD,
    SQL_TRUSTED_CONNECTION
)

def get_connection():
    """Create database connection."""
    if SQL_TRUSTED_CONNECTION.lower() == 'yes':
        conn_str = (
            f"DRIVER={SQL_DRIVER};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"Trusted_Connection=yes;"
        )
    else:
        conn_str = (
            f"DRIVER={SQL_DRIVER};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"UID={SQL_USERNAME};"
            f"PWD={SQL_PASSWORD};"
        )
    return pyodbc.connect(conn_str)

conn = get_connection()
cursor = conn.cursor()

print("="*100)
print("VIEW DEFINITION: vw_PowerBI_AI_Technical_Combos")
print("="*100)

# Get the view definition
query = """
SELECT OBJECT_DEFINITION(OBJECT_ID('vw_PowerBI_AI_Technical_Combos')) AS view_definition
"""

cursor.execute(query)
row = cursor.fetchone()

if row and row.view_definition:
    print(row.view_definition)
else:
    print("Could not retrieve view definition")

cursor.close()
conn.close()
