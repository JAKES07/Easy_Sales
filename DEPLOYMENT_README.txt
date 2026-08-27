EASY SALES - RENDER PERSISTENT DATABASE DEPLOYMENT
=================================================

THIS PROJECT FIXES THE DATABASE RESET PROBLEM
---------------------------------------------
Easy Sales now uses Render's persistent disk automatically when the disk
is mounted at /var/data. Both the controller and every customer store
use the same persistent location:

/var/data/controller.db
/var/data/stores/STORE001.db
/var/data/stores/STORE002.db
...

IMPORTANT: DO NOT PUT DATABASE FILES IN THE GITHUB PROJECT
---------------------------------------------------------
The application code comes from GitHub, but live customer data is created
on the Render disk at runtime. A GitHub update therefore replaces the code
without replacing controller status, passkeys, products, stock or sales.

RENDER SETUP
------------
1. Keep the Persistent Disk mounted at:

   /var/data

2. Upload this complete project to GitHub.

3. Root Directory on Render: leave it BLANK when the files are at the
   repository root.

4. Build Command:

   pip install -r requirements.txt

5. Start Command:

   gunicorn --workers 1 --threads 4 --timeout 120 app:app

6. Recommended environment variable:

   EASY_SALES_SECRET_KEY = a long private random value

OPTIONAL
--------
You can also set EASY_SALES_DATA_DIR=/var/data explicitly. The application
will already choose /var/data automatically when that persistent disk is
mounted.

FINAL TEST
----------
1. Activate STORE001.
2. Add a clearly named test product.
3. Deploy an update.
4. Confirm STORE001 is still ACTIVE.
5. Confirm the same passkey still works.
6. Confirm the product is still there.

If all three remain, the persistent live database is working correctly.
