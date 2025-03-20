import subprocess
import os
import shelve

# Create a shelve object to store the startNow variable
with shelve.open('startVisuals.db') as start:
    start['startNow'] = False

def check_and_run_initial_data_load():
    """
    Checks if the database exists. If it doesn't, it runs initial_data_load.py.
    """
    print("Checking for the existence of the database...")
    if not os.path.exists('EdgeDB.db'):
        print("Database does not exist. Starting initial data load process...")
        try:
            subprocess.run(["python", "initial_data_load.py"], check=True)
            print("Initial data load process completed.")
            with shelve.open('startVisuals.db') as start:
                start['startNow'] = True
            
        except subprocess.CalledProcessError as e:
            print(f"Error running initial_data_load script: {e}")
            with shelve.open('startVisuals.db') as start:
                start['startNow'] = False   

    else:
        print("Database already exists. Skipping initial data load.")
        with shelve.open('startVisuals.db') as start:
            start['startNow'] = True


if __name__ == "__main__":
    check_and_run_initial_data_load()
