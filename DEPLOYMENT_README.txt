EASY SALES - RENDER PERSISTENT DATA DEPLOYMENT
================================================

THIS PACKAGE FIXES THE DATABASE RESET PROBLEM
---------------------------------------------
The controller database and every private store database use ONE live
data directory. In production the app refuses to start unless that
directory is supplied through EASY_SALES_DATA_DIR. This prevents a
Render deployment from silently creating a new database inside the app
folder.

RENDER SETUP
------------
1. In your Render Web Service, add a Persistent Disk.
2. Choose a mount path, for example:

   /var/data

3. Add these Environment Variables:

   EASY_SALES_ENV=production
   EASY_SALES_DATA_DIR=/var/data
   EASY_SALES_SECRET_KEY=<your long random secret>

4. Save the settings and redeploy.

WHAT IS STORED ON THE PERSISTENT DISK
-------------------------------------
/var/data/controller.db
/var/data/stores/STORE001.db
/var/data/stores/STORE002.db
...and every other private store database.

GitHub deployments replace application code, but they do NOT replace
the mounted persistent disk. Therefore store activation status, passkeys,
products, sales and stock remain after future updates.

IMPORTANT FIRST DEPLOYMENT NOTE
-------------------------------
A persistent disk is a new storage location. If your current live Render
data exists only in the old temporary application filesystem, attach the
disk BEFORE relying on it and make a backup/copy of the existing live
databases if you need to preserve those exact records. Once the live data
is on the persistent disk, future deployments keep using it.

SAFETY CHECK
------------
In production Easy Sales will now fail loudly if EASY_SALES_DATA_DIR is
missing instead of starting with a temporary database. That is intentional:
it protects your customer data from accidental resets.

START COMMAND
-------------
gunicorn --workers 1 --threads 4 --timeout 120 app:app

WHY ONE WORKER?
---------------
Easy Sales currently uses SQLite. One worker is the safest starting
configuration and reduces SQLite write contention.

LOCAL PYDROID
------------
Do not set EASY_SALES_ENV=production. Without EASY_SALES_DATA_DIR the
app continues to use its local database folder for development.

FINAL TEST
----------
1. Activate STORE001.
2. Add a clearly named test product.
3. Redeploy the same service.
4. Confirm STORE001 is still ACTIVE and the product is still there.

If both are still there, the persistent live database is working.
