EASY_SALES EMPLOYEE MODE — STORE ADD-ON
========================================

This version changes Employee Mode to a persistent, per-store feature.

CONTROLLER
----------
1. Open Controller -> Store Details for the requested client store.
2. Employee Mode is OFF by default for every store.
3. After the client requests the feature, click "Enable Employee Mode Add-on".
4. The store will then show a password setup popup the next time the POS is opened.
5. If the client forgets the password, use "Reset Password" in Controller.
   This clears the old password and the setup popup appears again on the store's next open.
6. Disabling the add-on immediately prevents the POS from using Employee Mode.

POS
---
- There is NO Employee Mode button anymore.
- The owner creates the password in the automatic setup popup.
- To turn Employee Mode ON, type the password into the normal product search bar and press Enter.
- To turn Employee Mode OFF, type the same password into the search bar and press Enter again.
- The Employee Mode state is stored for the store in the controller database. Logging out, logging back in, refreshing the page, or restarting the server does NOT switch it off.
- The password is stored as a one-way hash. It is never displayed to the client or controller.

WHEN EMPLOYEE MODE IS ON
------------------------
Hidden/blocked:
- Add Product
- Stock Take
- Remove Stock
- Edit Product
- Other stock/report owner APIs already protected by the previous Employee Mode implementation

Still available:
- Product search
- Barcode scanner
- Checkout / sales
- Cash and card sales
- Receipt preview
- PDF receipt sharing
- Bluetooth/ESC-POS receipt functions

SECURITY
--------
The UI hides owner controls, but Flask also checks the persistent Employee Mode state
before protected API operations. This prevents an employee from bypassing the hidden
buttons by directly calling the owner APIs.

PER-STORE
---------
The feature flag, password hash, and current Employee/Owner mode are stored on the
individual controller store record. Enabling it for one store does not enable it for
other stores.
