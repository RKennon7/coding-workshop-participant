# Lambda entrypoint: terraform deploys backend/v1 with handler "function.handler"
import asyncio

from app.main import handler as http_handler


def handler(event, context):
    # Direct `aws lambda invoke` with {"action": "init_db"} creates tables and seeds data (bin/init-database.sh).
    # Function URL / CloudFront requests can't trigger this: their payload is the HTTP event shape,
    # and the request body is nested under "body", never at the top level.
    if isinstance(event, dict) and event.get("action") == "init_db":
        from scripts.init_db import init_db

        # reuse the loop Mangum set up -- asyncio.run() would close it and break later HTTP requests
        return asyncio.get_event_loop().run_until_complete(
            init_db(event.get("sample_data", True), event.get("seed_password"))
        )
    return http_handler(event, context)
