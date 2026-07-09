"""
app.py
ZETA - entrypoint. Run with:  python app.py
"""
from flask import Flask, render_template, session, redirect, url_for, send_from_directory

from database import init_db
from settings import Config, APP_CONFIG
from auth import auth_bp, login_required, current_user
from chat import chat_bp
from api import api_bp
import models


def create_app():
    app = Flask(__name__, static_folder="statics", static_url_path="/statics")
    app.config.from_object(Config)

    init_db(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(api_bp)

    @app.route("/")
    @login_required
    def index():
        user = current_user()
        return render_template("index.html", user=user, config=APP_CONFIG)

    @app.route("/settings")
    @login_required
    def settings_page():
        user = current_user()
        return render_template("settings.html", user=user, config=APP_CONFIG)

    @app.route("/profile")
    @login_required
    def profile_page():
        user = current_user()
        return render_template("profile.html", user=user, config=APP_CONFIG)

    @app.route("/uploads/<path:filename>")
    @login_required
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    @app.context_processor
    def inject_globals():
        return {"app_config": APP_CONFIG}

    @app.errorhandler(404)
    def not_found(e):
        return render_template("index.html", user=current_user(), config=APP_CONFIG) if "user_id" in session else redirect(url_for("auth.login_page"))

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=3000)
