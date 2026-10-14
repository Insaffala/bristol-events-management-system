# Before running or publishing

1. **Rotate the original MySQL account password**. It appeared in the previously shared coursework ZIP. Changing the source file is not sufficient: change the credential on the MySQL server or hosting control panel. If you no longer use that MySQL account, disable/delete it instead.
2. Copy `.env.example` to `.env`. Set `DB_USER`, your **new** `DB_PASSWORD`, and `DB_NAME`, and choose a fresh `SECRET_KEY`. `.env` must never be committed.
3. If the old database was hosted remotely, check whether the account has access to other data and rotate any reused passwords.
4. If any old version was previously pushed publicly, rewrite repository history to remove exposed credentials; rotating them remains mandatory.
5. This ZIP does **not** include a MySQL dump/schema. Restore that privately before you expect the app to run. Do not publish a database dump with real users, hashes, email addresses or booking records.
6. Flask sessions signed using the prior secret may stop working after the secret changes; users may need to log in again.
7. This is coursework and is not production-hardened. Inspect CSRF, access control and file uploads before hosting on the public internet.
