import sqlite3
from datetime import datetime, timedelta

def delete_old_rows(db_file, table_name, days_to_keep):
    """
    Deletes rows older than the specified number of days from the SQLite database.

    Args:
        db_file (str): Path to the SQLite database file.
        table_name (str): Name of the table to clean up.
        days_to_keep (int): Number of days of data to retain.
    """
    try:
        conn = sqlite3.connect(db_file)
        conn.execute('PRAGMA journal_mode=WAL')  # Enable Write-Ahead Logging
        cursor = conn.cursor()

        threshold = datetime.now() - timedelta(days=days_to_keep)
        threshold_str = threshold.strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute(f"DELETE FROM {table_name} WHERE LogTimestamp < ?", (threshold_str,))
        conn.commit()

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()


def delete_old_refresh_logs(db_file, table_name, days_to_keep):
    """
    Deletes rows older than the specified number of days from the refresh logs.

    Args:
        db_file (str): Path to the SQLite database file.
        table_name (str): Name of the table to clean up.
        days_to_keep (int): Number of days of data to retain.
    """
    try:
        conn = sqlite3.connect(db_file)
        conn.execute('PRAGMA journal_mode=WAL')  # Enable Write-Ahead Logging
        cursor = conn.cursor()

        threshold = datetime.now() - timedelta(days=days_to_keep)
        threshold_str = threshold.strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute(f"DELETE FROM {table_name} WHERE refresh_time < ?", (threshold_str,))
        conn.commit()

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()

def delete_old_lastupdateTIme(db_file, table_name, days_to_keep):
    """
    Deletes rows older than the specified number of days from the SQLite database.

    Args:
        db_file (str): Path to the SQLite database file.
        table_name (str): Name of the table to clean up.
        days_to_keep (int): Number of days of data to retain.
    """
    try:
        conn = sqlite3.connect(db_file)
        conn.execute('PRAGMA journal_mode=WAL')  # Enable Write-Ahead Logging
        cursor = conn.cursor()

        threshold = datetime.now() - timedelta(days=days_to_keep)
        threshold_str = threshold.strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute(f"DELETE FROM {table_name} WHERE last_update_time < ?", (threshold_str,))
        conn.commit()

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()