# from functools import wraps
# from flask import request, jsonify
# from supabase_client import supabase

# def require_auth(optional=False):
#     def decorator(f):
#         @wraps(f)
#         def decorated(*args, **kwargs):
#             token = request.cookies.get("access_token")
#             refresh_token = request.cookies.get("refresh_token")

#             if not token:
#                 if optional:
#                     request.user = None
#                     return f(*args, **kwargs)
#                 return jsonify({"error": "unauthorized"}), 402
            
#             try:
#                 res = supabase.auth.get_user(token)
#                 request.user = res.user
#                 return f(*args, **kwargs)
            
#             except Exception:
#                 # Try refreshing if access token expired
#                 if not refresh_token:
#                     if optional:
#                         request.user = None
#                         return f(*args, **kwargs)
#                     return jsonify({"error": "session expired"}), 401
#                 try:
#                     refreshed = supabase.auth.refresh_session(refresh_token)
#                     request.user = refreshed.user
#                     resp = make_response(f(*args, **kwargs))
#                     _set_auth_cookies(resp, refreshed.session)
#                     return resp
#                 except Exception:
#                     if optional:
#                         request.user = None
#                         return f(*args, **kwargs)
#                     return jsonify({"error": "session expired, please sign in again"}), 401

#         return decorated
#     return decorator