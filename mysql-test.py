import mysql.connector
from mysql.connector import Error
from time import sleep
from datetime import datetime

def log(msg):
    now = datetime.now().strftime('%H:%M:%S')
    print(f"[{now}] {msg}")

def insert_data_with_connection(connection, cursor, value):
    try:
        insert_query = "INSERT INTO test_audit VALUES (%s)"
        cursor.execute(insert_query, (value,))
        connection.commit()
        log(f"{value} → Added. Lines: {cursor.rowcount}")
    except Error as e:
        log(f"{value} → Insertion error: {e}")

def main():
    connection = None
    try:
        connection = mysql.connector.connect(
            host='.mysql.database.azure.com',
            database='',
            user='',
            password=''
        )

        if connection.is_connected():
            log("Connection established.")
            cursor = connection.cursor()

            for i in range(1000):
                insert_data_with_connection(connection, cursor, i + 1)
                sleep(0.3)

            cursor.close()
            log("Cursor is closed.")
    except Error as e:
        log(f"MySQL error: {e}")
    finally:
        if connection and connection.is_connected():
            connection.close()
            log("MySQL connection is closed.")

if __name__ == "__main__":
    main()
