EASY_SALES RECEIPT + ESC/POS PRINTER UPGRADE

WHAT WAS ADDED
1. After a successful sale, Easy_Sales opens a Sale Complete receipt preview.
2. The preview supports Print Receipt using the device/browser print dialog.
3. The preview supports Share Receipt using Android/browser sharing when available.
4. A clipboard fallback is used if browser sharing is unavailable.
5. The server now returns receipt line items and transaction ID from the completed sale.
6. printer_escpos.py builds standard ESC/POS receipt bytes for 58mm and 80mm paper.

IMPORTANT BLUETOOTH LIMITATION
The Flask web app cannot reliably open a raw Bluetooth Classic SPP socket from normal Android Chrome.
The ESC/POS builder therefore prepares the printer commands, but a native Android bridge is required
for direct Bluetooth Classic printer communication.

RECOMMENDED FINAL CONNECTION
Easy_Sales Android app
  -> native printer bridge
  -> Android Bluetooth permission / paired device
  -> Bluetooth Classic SPP
  -> ESC/POS thermal printer

For a browser-only deployment, use the Android/system print dialog where the printer is exposed by an
installed print service. This is separate from raw ESC/POS Bluetooth communication.

PRINTER COMPATIBILITY
Target common 58mm/80mm ESC/POS thermal receipt printers. Do not advertise universal support for every
Bluetooth printer; proprietary printers may require their own protocol or driver.
