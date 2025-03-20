import subprocess
import os
import shelve

def initial_data_load():
    """
    Runs the dataRefresh2.py script to perform the initial data load.
    This function will only run once to create the database
    """
    print("Performing initial data load...")
    try:
        subprocess.run(["python", "dataRefresh2.py"], check=True)
        print("Initial data load completed.")
        with shelve.open('startVisuals.db') as start:
            start['startNow'] = True

    except subprocess.CalledProcessError as e:
        print(f"Error during initial data load: {e}")
        with shelve.open('startVisuals.db') as start:
            start['startNow'] = False

    except FileNotFoundError:
        print("Error: dataRefresh2.py not found.")
        with shelve.open('startVisuals.db') as start:
            start['startNow'] = False

            
if __name__ == "__main__":
    if not os.path.exists('EdgeDB.db'):
        initial_data_load()
    else:
        print("Database already exist, initial load skipped")

