# How to run the Smart Flood System - step by step (Windows)

You only do Steps 1-6 once. After that, running the project is just Steps 7-8.

---

## Step 1 - Install Python
1. Go to https://www.python.org/downloads/ and install Python (3.14 was used to build this; 3.12/3.13 should also work).
2. **Tick "Add Python to PATH"** on the first installer screen, then click Install.
3. Check it worked: open **Command Prompt** and type `python --version`. You should see a version number.

## Step 2 - Install and start MySQL (XAMPP)
1. Install XAMPP from https://www.apachefriends.org/ (only **MySQL** is needed).
2. Open the **XAMPP Control Panel** and click **Start** next to **MySQL**. The name turns green.
   (Leave XAMPP open whenever you use the project.)

## Step 3 - Unzip the project
Unzip `smart_flood_system.zip`, for example to `C:\Users\USER\Downloads\`.
Open the unzipped folder. You must see `backend`, `frontend`, `setup.bat` and `run.bat` directly inside it.
If you see another `smart_flood_system` folder inside, open that one.

## Step 4 - (Recommended) back up your old database
Only if you already have a `smart_flood_system` database you want to keep:
1. Open http://localhost/phpmyadmin
2. Click `smart_flood_system` on the left, then **Export**, then **Go**. Keep the `.sql` file somewhere safe.

## Step 5 - Check the `.env` file
Open `.env` with Notepad. The default works with a fresh XAMPP:

    DATABASE_URL=mysql+pymysql://root:@localhost:3306/smart_flood_system

If you gave MySQL's root user a password, write it after the colon:
`root:MYPASSWORD@localhost`. Save the file.

## Step 6 - First-time setup
Double-click **`setup.bat`** and wait 2-5 minutes. It will:
1. create a private Python environment (`.venv`) and install the packages,
2. create the database, tables and 6 cities,
3. load the saved weather data and verified flood days.

You should see lines like:

    Database and tables are ready.
    Added 6 starter locations.          (or "Locations already exist - left unchanged.")
    Imported/updated 12768 daily weather rows.
    Finished. Positive label rows processed/upserted: 13

Then press any key to close it. If you see **"Could not connect to MySQL"**, MySQL isn't started
in XAMPP or the password in `.env` is wrong (fix it, run `setup.bat` again).

## Step 7 - Start the app
1. Make sure MySQL is green in XAMPP.
2. Double-click **`run.bat`**. A black window opens and your browser opens
   http://127.0.0.1:8000/
3. In the black window you should see `Application startup complete` and, a few seconds later,
   `NASA auto-sync: starting`. The app is now downloading the newest NASA weather into the
   database in the background (needs internet; the first time on an empty database can take a
   minute or two).

**Keep the black window open** while you use the dashboard.

## Step 8 - Use the dashboard
1. Pick a city from the dropdown (Dhaka, Mumbai, Jakarta, London, New Orleans, Tokyo).
2. Look at the map, weather graphs, flood history and rainfall indicator.
3. Press **Predict** to get the experimental flood-risk estimate (Haor model - research demo only).
4. Press the **update** button any time to download missing NASA weather right now.
5. API pages for testing: http://127.0.0.1:8000/docs

## Step 9 - Stop and run again later
- **Stop:** click the black window and press `Ctrl + C`, then close it.
- **Next time:** start MySQL in XAMPP, then double-click `run.bat`. (Don't run `setup.bat` again.)

---

## Where does my big data go?
Put NASA IMERG satellite files in `data/imerg_downloads/`. The dashboard doesn't need them,
so you can skip this. See `data/README.md`.

## Turn off the automatic NASA download
In `.env` set `AUTO_SYNC_NASA=false`, then restart `run.bat`.

## Problems?
| Message / symptom | Fix |
|---|---|
| `python` is not recognized | Reinstall Python and tick **Add Python to PATH**, then reopen the window |
| Could not connect to MySQL | Start MySQL in XAMPP; check the password in `.env` |
| `pip install` fails | Check your internet connection and run `setup.bat` again |
| Dropdown is empty | Run `python scripts/setup_database.py` (see below) |
| Graphs empty / "No weather observations" | Press the update button, or run `python scripts/import_weather_csv.py` |
| Browser says "127.0.0.1 refused to connect" | The server isn't running (yet). Wait ~10 seconds and press Refresh. If it still fails, look at the black window: it must still be open and show `Application startup complete`. If it closed or shows an error, run `run.bat` again and read the last lines |
| Port 8000 already in use | Close the other black window, or edit `run.bat` and add `--port 8001` |
| Page won't load after closing the black window | The app stops when that window closes - run `run.bat` again |

To run a script manually: open Command Prompt in the project folder and type
`.venv\Scripts\activate` and then the command, e.g. `python scripts/setup_database.py`.
