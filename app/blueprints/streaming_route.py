from flask import Blueprint

streaming_routes = Blueprint('streaming', __name__)

@streaming_routes.route("/")
def index():
    return {"message": "Backend is running"}
