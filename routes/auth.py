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

@auth_bp.route("/reset-password", methods=["POST"])
def request_password_reset():
    """
    POST /auth/reset-password
    Sends a password reset email to the user.
    No authentication required.

    Request Body:
    {
        "email": "user@example.com"
    }

    Response (200):
    {
        "message": "Password reset email sent"
    }

    Error Responses:
        400 - Email is required
        500 - Failed to send reset email
    """
    data  = request.get_json()
    email = data.get("email") if data else None

    if not email:
        return jsonify({"error": "Email is required"}), 400

    try:
        supabase.auth.reset_password_email(
            email,
            options={"redirect_to": "yourapp://reset-password"}  # change to your app's deep link or web URL
        )
        # Always return 200 even if email doesn't exist — prevents user enumeration
        return jsonify({"message": "Password reset email sent"}), 200
    except Exception as e:
        return jsonify({"error": "Failed to send reset email", "details": str(e)}), 500



@auth_bp.route("/reset-password/confirm", methods=["POST"])
def confirm_password_reset():
    """
    POST /auth/reset-password/confirm
    Updates the user's password after they've clicked the reset link.
    The user must be authenticated via the reset token from the email link.

    Auth Required: Yes (reset token from email, passed as Bearer token)

    Request Body:
    {
        "password":         "newpassword123",
        "confirm_password": "newpassword123"
    }

    Response (200):
    {
        "message": "Password updated successfully"
    }

    Error Responses:
        400 - Missing fields or passwords do not match
        400 - Password too short
        401 - Invalid or expired reset token
        500 - Failed to update password
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body is required"}), 400

    password         = data.get("password")
    confirm_password = data.get("confirm_password")

    if not password or not confirm_password:
        return jsonify({"error": "password and confirm_password are required"}), 400

    if password != confirm_password:
        return jsonify({"error": "Passwords do not match"}), 400

    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    # Get the access token from Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid authorization token"}), 401

    access_token = auth_header.split(" ")[1]

    try:
        client = get_authenticated_client(access_token)
        client.auth.update_user({"password": password})
        return jsonify({"message": "Password updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": "Failed to update password", "details": str(e)}), 500


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