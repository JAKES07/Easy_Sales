EASY SALES - DEPLOYMENT PACKAGE

WHAT TO REPLACE / ADD
---------------------
1. Replace your project app.py with the app.py in this package.
2. Add requirements.txt, Procfile, .gitignore, .env.example and wsgi.py
   to the ROOT of your Easy_Sales project.

IMPORTANT: DATABASES
--------------------
Easy Sales uses SQLite databases stored in the database/ folder.
Your hosting platform MUST provide persistent storage for this folder.
Do not deploy to a platform where the filesystem is erased on restart,
unless the database folder is mounted on persistent storage.

PRODUCTION ENVIRONMENT VARIABLES
--------------------------------
Set these on the hosting platform:

EASY_SALES_ENV=production
EASY_SALES_SECRET_KEY=<a long random secret>

Do NOT put your real secret key inside app.py or commit it publicly.

START COMMAND
-------------
gunicorn --workers 1 --threads 4 --timeout 120 app:app

WHY ONE WORKER?
---------------
The current Easy Sales system uses SQLite files. One application worker is
the safest starting point for this deployment architecture and avoids
unnecessary SQLite write contention.

BEFORE GOING LIVE
-----------------
- Make a backup of the complete database/ folder.
- Confirm the host provides persistent storage.
- Confirm HTTPS is enabled.
- Test Controller login.
- Test Store Access.
- Test STORE001 and STORE002 have different products/data.
- Test deactivation immediately removes POS access.
- Test data remains after restarting the deployed service.

LOCAL PYDROID
------------
You can still run the updated app.py locally with:
python app.py

Production mode is only enabled when EASY_SALES_ENV=production is set.
