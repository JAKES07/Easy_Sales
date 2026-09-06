EASY SALES - 30 DAY CLIENT SUBSCRIPTION UPGRADE

What changed:
1. Controller WhatsApp/TikTok popup removed from controller login/setup.
   The customer Store Access popup remains unchanged.
2. Controller Activate button now starts a 30-day access period.
3. Activation stores both activation date/time and expiry date/time.
4. Expired active stores are automatically marked EXPIRED by the server.
5. Expired stores cannot enter the POS until renewed/activated again.
6. Active stores have a Renew 30 Days button in the Controller.
7. Added /controller/clients - Client Status page.
8. Client Status shows store name, Store ID, status, activation date,
   expiry date and days remaining.
9. Older controller databases are migrated automatically with the new
   expires_at column. Existing ACTIVE stores without an expiry receive
   a fresh 30-day period during the first upgrade startup so they are not
   unexpectedly locked out during migration.
10. Store Details now shows subscription information and no longer displays
    the stored passkey hash.

Important:
- The subscription timer is server-side and uses 30 calendar days (30 x 24 hours)
  from the activation timestamp.
- Renewing starts a new 30-day period from the renewal timestamp.
- WhatsApp automatic messaging is NOT enabled in this version because Meta API
  credentials have not been configured.
