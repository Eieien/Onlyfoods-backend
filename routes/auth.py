from flask import Blueprint, request, jsonify, make_response, session
from supabase_client import supabase
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, set_access_cookies, unset_jwt_cookies
from extensions import bcrypt
auth_bp = Blueprint("/auth", __name__)

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.json
    email = data["email"].strip().lower()
    password = data["password"]

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    if len(password) < 8:
        return jsonify({"error": "Password is too short"}), 400

    email_exists = supabase.table("users").select("id").eq("email", email).maybe_single().execute()

    if email_exists:
        return jsonify({"error": "Email already exists"}), 409
    
    # password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    # response = supabase.table("users").insert({
    #     "username": data["username"],
    #     "email": email,
    #     "password": password
    # }).execute()
    
    # return jsonify({"new_user" : response.data, "message": "User registered successfully"}), 201
    try:
        res = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data" : {"username": data["username"]}
            }
        })

        # if res.user and res.user.identities == []:
        #     return jsonify({"error": "Email already registered"}), 409

        if not res.user:
            return jsonify({"error": "Registration failed"}), 400
        
        return jsonify({
            "message": "User Registered Successfully. Please check your email to confirm.",
            "user": {"id": res.user.id, "email": res.user.email}
        }), 201
    except Exception as e:

        return jsonify({"error": str(e)}), 409

@auth_bp.route("/login", methods=["POST"])
# @jwt_required(optional=True) 
def login():
    data = request.json
    email = data["email"].strip().lower()
    password = data["password"]
    # user_id = get_jwt_identity()

    # if user_id:
    #     return jsonify({"message": "User is already logged in"}), 303

    # if not email or not password:
    #     return jsonify({"error": "Email and password are required"}), 400
    
    # user = supabase.table("users").select("id,password").eq("email", email).maybe_single().execute()

    # if not user or not bcrypt.check_password_hash(user.data["password"], password):
    #     return jsonify({"error": "Invalid email or password"}), 409
    
    # access_token = create_access_token(identity=str(user.data["id"]))
    # response =  jsonify({"message": "Logged in Successfully"})
    # set_access_cookies(response, access_token)
    
    signed_in = session.get("user")
    if signed_in:
        return jsonify({"error": "User is already logged in"}), 401
    
    try:
        res = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        user = res.user
        session["user"] = {"id": user.id, "email": user.email, "metadata": user.user_metadata}
        return jsonify({"message": "Login successful", "user": session["user"]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 401


@auth_bp.route("/logout", methods=["POST"])
# @jwt_required(optional=True)
def logout():

    # user = get_jwt_identity()
    
    # if not user:
    #     return jsonify({"message": "Already logged out"})

    # response = jsonify({"message": "Logged out successfully"})
    # unset_jwt_cookies(response)

    supabase.auth.sign_out()
    session.clear()

    return jsonify({"message": "Logged out"}), 200

@auth_bp.route("/me", methods=["GET"])
# @jwt_required()
def getMe():
    user = session.get("user")
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    return jsonify({"user": user}), 200
