EASY_SALES - EMPLOYEE MODE

Employee Mode is a store-session safety mode for the POS.

OWNER SETUP
1. Open the POS in Owner Mode.
2. Press "👤 Employee Mode".
3. The first time, create and confirm an Employee Mode password.
4. Press "TURN ON EMPLOYEE MODE" and enter that password.

WHEN EMPLOYEE MODE IS ON
Hidden/locked owner controls:
- Add Product
- Stock Control / Stocktake
- Edit Product
- Remove Product / Remove Stock actions
- Stock management APIs
- Stock reports/history APIs
- Currency-setting POST action

Still available:
- Product search
- POS barcode scanner
- Add products to cart
- Checkout
- Cash/card sales
- Receipt preview
- PDF receipt sharing
- Bluetooth printing when configured

SECURITY
The restrictions are enforced server-side by Flask as well as in the interface. Hiding a button is not the security boundary.

EXITING EMPLOYEE MODE
The Employee Mode button is intentionally hidden while Employee Mode is active.
To restore Owner Mode, tap the Easy_Sales logo five times quickly and enter the same owner password. The password is still required; the tap gesture is only a way to reveal the protected owner-mode prompt.

The password is stored as a hash in the store's private database, not as plain text.
