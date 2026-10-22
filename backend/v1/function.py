"""AWS Lambda entrypoint for the whole backend API.

Terraform deploys backend/v1 with handler "function.handler". Every invocation lands here:
normal HTTP traffic (CloudFront / Function URL) is passed straight to the Mangum-wrapped FastAPI
app in app/main.py, and a direct invoke with {"action": "init_db"} runs schema creation + seeding
instead (the database is only reachable from inside the VPC, so this is how bin/init-database.sh does it).
"""
import asyncio

from app.main import handler as http_handler


def handler(event, context):
    """Route a Lambda event to either the database initializer or the HTTP app.

    init_db events may also carry "sample_data" (bool, default True) and "seed_password"
    (str, optional) -- see scripts/init_db.py. Returns init_db's result dict for init events,
    otherwise the API Gateway-style HTTP response produced by Mangum.
    """
    # Direct `aws lambda invoke` with {"action": "init_db"} creates tables and seeds data (bin/init-database.sh).
    # Function URL / CloudFront requests can't trigger this: their payload is the HTTP event shape,
    # and the request body is nested under "body", never at the top level.
    if isinstance(event, dict) and event.get("action") == "init_db":
        # imported lazily so normal HTTP cold starts don't load the seeding scripts
        from scripts.init_db import init_db

        # reuse the loop Mangum set up -- asyncio.run() would close it and break later HTTP requests
        # (a warm Lambda container keeps serving requests on the same loop after this invoke)
        return asyncio.get_event_loop().run_until_complete(
            init_db(event.get("sample_data", True), event.get("seed_password"))
        )
    return http_handler(event, context)
