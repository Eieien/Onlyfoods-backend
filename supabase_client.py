import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(url, key)

def get_authenticated_client(access_token: str) -> Client:
    """Returns a Supabase client with the user's JWT so RLS works correctly."""
    authenticated_client = create_client(url, key)
    authenticated_client.postgrest.auth(access_token)
    return authenticated_client