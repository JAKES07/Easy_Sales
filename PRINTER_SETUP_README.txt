EASY_SALES RECEIPT + BLUETOOTH ESC/POS PRINTER UPGRADE

WHAT WAS ADDED
1. Sale Complete receipt preview remains after every successful sale.
2. System Print / PDF remains available exactly as before.
3. Share Receipt remains available.
4. Bluetooth Print was added.
5. Connect Bluetooth Printer was added.
6. Easy_Sales now builds ESC/POS commands in the browser and sends them to compatible BLE thermal printers.
7. The receipt is sent directly to the printer; the user does not have to save a PDF first.

HOW TO USE
1. Open Easy_Sales over HTTPS (the Render HTTPS address is suitable).
2. Turn on the compatible Bluetooth thermal printer.
3. Pairing is normally handled by the browser's Bluetooth chooser; follow the Android prompt.
4. Complete a sale.
5. On Sale Complete, press Connect Bluetooth Printer, select the printer, then press Bluetooth Print.
6. Once connected during that browser session, Bluetooth Print can be used for later receipts.

IMPORTANT COMPATIBILITY NOTE
There are two common kinds of Bluetooth receipt printers:
- Bluetooth Low Energy (BLE): this upgrade can communicate with compatible ESC/POS BLE printers directly from supported Android browsers.
- Bluetooth Classic SPP: normal Android Chrome cannot open the raw SPP socket from a web page. These printers need a native Android bridge/app or a compatible Android print service.

Therefore, do NOT assume that every printer advertised simply as "Bluetooth" will work directly from the website.
When buying a printer for direct browser printing, specifically ask the seller whether it supports BLE/Web Bluetooth and ESC/POS.
If you buy a Bluetooth Classic SPP printer, the Easy_Sales Android wrapper/native printer bridge can be added later without removing the current receipt/PDF features.

PRINTER SIZE
The browser Bluetooth receipt defaults to 58mm formatting. The ESC/POS builder supports the existing 58mm/80mm formats on the server side as well.

FALLBACK
If Bluetooth printing is not supported by the browser or printer, System Print / PDF still works through the Android print dialog.
