from flask import Blueprint, jsonify, request
from supabase_client import supabase

users_bp = Blueprint("users", __name__)

@users_bp.route("/", methods=["GET"])
def get_users():
    response = supabase.table("users").select("*").execute()
    return jsonify(response.data), 200

@users_bp.route("/create", methods=["POST"])
def create_user():
    data = request.json
    response = supabase.table("users").insert({
        "username": data["username"],
        "email": data["email"],
        "password": data["password"]
    }).execute()

    return jsonify(response.data), 2016

@users_bp.route("/getall", methods=["GET"])
def get_allusers():
    response = supabase.table("users").select("*").execute()
    return jsonify(response.data), 200

@users_bp.route("/users/[id]", methods=["GET"])
def get_user():
    response = supabase.table("users").select("id").execute()
    return jsonify(response.data),200