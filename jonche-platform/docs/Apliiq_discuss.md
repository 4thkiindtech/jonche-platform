[ ] NAME:Current Task List DESCRIPTION:Root task for conversation __NEW_AGENT__
-[ ] NAME:Fix .env.example DESCRIPTION:Fix broken Apliiq section to use proper env var format
-[ ] NAME:Create Apliiq routes blueprint DESCRIPTION:Create apps/api/routes/apliiq.py with admin endpoints to sync/check Apliiq orders
-[ ] NAME:Register blueprint in app.py DESCRIPTION:Register apliiq_bp in app.py under /api/apliiq
-[ ] NAME:Hook into order_finalizer DESCRIPTION:Update order_finalizer.py to optionally submit completed orders to Apliiq for fulfillment