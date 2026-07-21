"""Single shared Supabase client for the backend API's database access.

Built once at import time - the client is a thin, stateless HTTP wrapper
(every call is its own request to Supabase's PostgREST API), so unlike a
SQLAlchemy Session there's no per-request resource to allocate/release and
no FastAPI dependency-injection lifecycle needed.
"""

from supabase import Client, create_client

from ticket_router.config import config

client: Client = create_client(config.SUPABASE_URL, config.SUPABASE_SECRET_KEY)
