# app.py
from flask import Flask
from config import Config
from extensions import db, login_manager
from datetime import datetime, timezone
from dotenv import load_dotenv
from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.trace.samplers import ProbabilitySampler
from opencensus.ext.flask.flask_middleware import FlaskMiddleware
import logging
import os
from azure.monitor.opentelemetry import configure_azure_monitor

# Load environment variables from .env file
load_dotenv()

# Initialise Flask application
app = Flask(__name__)
# Load configuration from Config class
app.config.from_object(Config)

app_insights_conn_str = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
if app_insights_conn_str:
    logger = logging.getLogger("britedgeLogger")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(AzureLogHandler(connection_string=app_insights_conn_str))

    middleware = FlaskMiddleware(
        app,
        exporter=AzureExporter(connection_string=app_insights_conn_str),
        sampler=ProbabilitySampler(rate=1.0),
    )

    configure_azure_monitor(logger_name="britedgeLogger")
    configure_azure_monitor(enable_live_metrics=True)
   

# Initialise SQLAlchemy with the Flask app
db.init_app(app)
login_manager.init_app(app)

# Set the login view for redirection if an unauthenticated user tries to access a protected page
login_manager.login_view = 'login'
# Set the message category for flash messages when redirection occurs
login_manager.login_message_category = 'info'

# Import models and routes after initialising db and app to avoid circular imports
from models import User, Job # Import User and Job models
from routes import * # Import all routes from routes.py

# This block ensures that database tables are created if they don't exist.
# It's crucial for initial setup and for the "self-contained monolith" requirement.
# It uses app.app_context() to ensure that Flask's application context is active
# when interacting with the database, which is necessary for SQLAlchemy.
with app.app_context():
    # Create all database tables defined in models.py
    # This will only create tables if they don't already exist.
    db.create_all()
    logger.info("Database tables created.")

@app.context_processor
def inject_now():
    return {'now': datetime.now(timezone.utc)}


@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled Exception: {e}", exc_info=True)
    return "An internal error occurred.", 500

@app.errorhandler(404)
def not_found_error(e):
    logger.warning(f"404 Not Found: {request.path}")
    return "Page not found.", 404
    

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)
