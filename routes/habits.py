from flask import Blueprint, request, jsonify
from supabase_client import supabase
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

habits_bp = Blueprint("/habits", __name__)


@habits_bp.route("/<id>", methods=["GET"])
def get_habits(id):

    return id

@habits_bp.route("/create/<id>", methods=["POST"])
def create_habit(id):
    
    data = request.json
    name = data["name"]

    if not name:
        return jsonify({"error": "Habit name must not be empty"}), 400
    
    response = supabase.table("habits").insert({
        "name": name
    }).execute()

    return jsonify({"habit": response.data, "message": "Habit created Successfully"})