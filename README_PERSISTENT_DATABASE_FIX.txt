EASY SALES — PERSISTENT DATABASE FIX
======================================

THE PROBLEM FIXED
-----------------
Before this change, Easy Sales stored:
- controller store activation/status in the deployed app's local database folder
- each store's product/sales database in that same deployed app folder

A Render deployment can replace that filesystem. When that happened, Easy Sales
created new empty databases, which made active stores appear inactive/available
and made product tiles disappear.

THE FIX
-------
All databases now use ONE shared data location controlled by:

    EASY_SALES_DATA_DIR

For Render production, configure:

    EASY_SALES_DATA_DIR=/var/data

Then attach a Render Persistent Disk and mount it at:

    /var/data

The following files were changed:
- storage.py                NEW shared persistent data location
- database.py               main database follows EASY_SALES_DATA_DIR
- store_database.py         every private store DB follows EASY_SALES_DATA_DIR
- store_controller.py       store activation/status follows EASY_SALES_DATA_DIR

controller_auth.py uses the controller connection, so its data follows the same
persistent controller database automatically.

IMPORTANT DEPLOYMENT TEST
-------------------------
1. Configure the Persistent Disk and EASY_SALES_DATA_DIR first.
2. Deploy these files.
3. Activate a test store.
4. Add a clearly named test product.
5. Deploy a harmless code-only update.
6. Check that:
   - the store is still ACTIVE
   - the test product is still present

Do not market the system as deployment-safe until this test passes.

NOTE ABOUT DATA ALREADY LOST
----------------------------
Data that disappeared in previous deployments cannot be recovered by this code
change unless a backup/copy of the old database still exists somewhere. This fix
protects data going forward once the persistent disk is configured correctly.
