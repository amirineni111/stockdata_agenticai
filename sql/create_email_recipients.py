"""
One-time script to create email_recipients table and seed current recipients.
Run: python sql/create_email_recipients.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pyodbc
from config.settings import SQL_SERVER, SQL_DATABASE, SQL_USERNAME, SQL_PASSWORD, SQL_DRIVER


def main():
    conn_str = (
        f"DRIVER={SQL_DRIVER};SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};"
        f"UID={SQL_USERNAME};PWD={SQL_PASSWORD}"
    )
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    # Check if table already exists
    cursor.execute("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_NAME = 'email_recipients'
    """)
    exists = cursor.fetchone()[0]

    if exists:
        print("Table 'email_recipients' already exists. Skipping creation.")
    else:
        cursor.execute("""
            CREATE TABLE email_recipients (
                id INT IDENTITY(1,1) PRIMARY KEY,
                email_address VARCHAR(255) NOT NULL,
                recipient_name VARCHAR(255) NULL,
                recipient_type VARCHAR(20) NOT NULL DEFAULT 'TO',
                briefing_type VARCHAR(50) NOT NULL DEFAULT 'daily_briefing',
                is_active BIT NOT NULL DEFAULT 1,
                created_date DATETIME NOT NULL DEFAULT GETDATE(),
                modified_date DATETIME NOT NULL DEFAULT GETDATE()
            )
        """)
        conn.commit()
        print("Table 'email_recipients' created successfully.")

        # Seed with current recipients (from .env EMAIL_TO)
        recipients = [
            ("sree.amiri@gmail.com", "Sree", "BCC"),
            ("sreenivas@multizoneus.com", "Sreenivas", "BCC"),
            ("satishgudipalli9@gmail.com", "Satish", "BCC"),
        ]
        for email, name, rtype in recipients:
            cursor.execute(
                "INSERT INTO email_recipients (email_address, recipient_name, recipient_type) VALUES (?, ?, ?)",
                email, name, rtype,
            )
        conn.commit()
        print(f"Inserted {len(recipients)} recipients.")

    # Show current state
    cursor.execute(
        "SELECT id, email_address, recipient_name, recipient_type, briefing_type, is_active "
        "FROM email_recipients ORDER BY id"
    )
    print("\nCurrent recipients:")
    for row in cursor.fetchall():
        status = "ACTIVE" if row.is_active else "INACTIVE"
        print(f"  [{row.id}] {row.email_address} ({row.recipient_name}) - {row.recipient_type} - {row.briefing_type} - {status}")

    conn.close()


if __name__ == "__main__":
    main()
