from flask import Blueprint, request, jsonify, make_response, session
from supabase_client import supabase
auth_bp = Blueprint("/auth", __name__)

@auth_bp.route("/register", methods=["POST"])
def register():
    # Check if already logged in
    if session.get("user"):
        return jsonify({"error": "Already logged in, please logout first"}), 400

    data = request.json
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    username = data.get("username", "").strip()

    if not email or not password or not username:
        return jsonify({"error": "Email, password and username are required"}), 400

    if len(password) < 8:
        return jsonify({"error": "Password is too short"}), 400

    # Check if email already exists in auth
    try:
        email_check = supabase.table("users").select("id").eq("email", email).maybe_single().execute()
        if email_check.data:
            return jsonify({"error": "Email already exists"}), 409
    except Exception:
        pass 

    try:
        res = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {"username": username}
            }
        })

        if not res.user:
            return jsonify({"error": "Registration failed"}), 400

        # Supabase returns a user even if email is already registered
        # but identities will be empty — catch duplicate this way
        if res.user.identities is not None and len(res.user.identities) == 0:
            return jsonify({"error": "Email already exists"}), 409

        return jsonify({
            "message": "User registered successfully. Please check your email to confirm.",
            "user": {"id": res.user.id, "email": res.user.email}
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 409


@auth_bp.route("/login", methods=["POST"])
def login():
    if session.get("user"):
        return jsonify({"error": "Already logged in, please logout first"}), 400

    data = request.json
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    try:
        res = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        user = res.user
        session["user"] = {
            "id": user.id,
            "email": user.email,
            "metadata": user.user_metadata,
            "access_token": res.session.access_token,   # store token
            "refresh_token": res.session.refresh_token  # store refresh token
        }
        return jsonify({
            "message": "Login successful",
            "user": {
                "id": user.id,
                "email": user.email,
                "metadata": user.user_metadata
            },
            "access_token": res.session.access_token,   # add this
            "refresh_token": res.session.refresh_token  # add this
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 401


@auth_bp.route("/logout", methods=["POST"])
def logout():

    user = session.get("user")
    if not user:
        return jsonify({"error": "User not logged in"}), 400

    supabase.auth.sign_out()
    session.clear()

    return jsonify({"message": "Logged out"}), 200

@auth_bp.route("/me", methods=["GET"])
def getMe():
    user = session.get("user")
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    return jsonify({"user": user, "message": "User data retrieved successfully"}), 200

def get_current_user():
    # First try Authorization header (mobile)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        access_token = auth_header.split(" ", 1)[1]
        try:
            res = supabase.auth.get_user(access_token)
            if res and res.user:
                return res.user.id, access_token, None
        except Exception as e:
            return None, None, (jsonify({"error": "Invalid or expired token", "details": str(e)}), 401)

    # Fall back to session (web)
    user = session.get("user")
    if not user:
        return None, None, (jsonify({"error": "Not authenticated"}), 401)

    return user["id"], user["access_token"], None