from flask import Flask, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from sqlalchemy.orm import class_mapper, ColumnProperty
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy import func
from sqlalchemy import text
from sqlalchemy import Integer
import os
from werkzeug.security import generate_password_hash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_cors import CORS 
import smtplib
import random
import base64
import uuid
from flask_restful import Api
from datetime import datetime, timedelta
from textblob import TextBlob

import pymysql
pymysql.install_as_MySQLdb()

app = Flask(__name__)
CORS(app)

db_url = os.environ.get('DATABASE_URL', 'mysql+pymysql://root:wRueKONUuTQFrFJKJBWXFyIJDgLRFZXI@yamabiko.proxy.rlwy.net:24650/railway?auth_plugin_map=mysql_native_password')
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
print("DB URL is:", db_url)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback-secret')
bcrypt = Bcrypt(app)

db = SQLAlchemy(app)

EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

class Emerge(db.Model):
    __tablename__ = 'emerge'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(255), nullable=False)

@app.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json()
        required_fields = ['name', 'email', 'phone', 'password', 'confirm_password']
        if not data or not all(k in data for k in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        if data['password'] != data['confirm_password']:
            return jsonify({'error': 'Passwords do not match'}), 400
        if Emerge.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already registered'}), 409
        hashed_password = generate_password_hash(data['password'])
        new_user = Emerge(
            name=data['name'],
            email=data['email'],
            phone=data['phone'],
            password=hashed_password
        )
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'message': 'User registered successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

class Active(db.Model):
    __tablename__ = 'active'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), nullable=False)

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data or 'email' not in data or 'password' not in data:
            return jsonify({'error': 'Email and password required'}), 400
        user = Emerge.query.filter_by(email=data['email']).first()
        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401
        if not check_password_hash(user.password, data['password']):
            return jsonify({'error': 'Invalid credentials'}), 401
        active_user = Active(email=user.email)
        db.session.add(active_user)
        db.session.commit()
        return jsonify({
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'phone': user.phone
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

def send_danger_alert(to_email, noise_level):
    import sendgrid
    from sendgrid.helpers.mail import Mail
    try:
        sg = sendgrid.SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))
        message = Mail(
            from_email=EMAIL_ADDRESS,
            to_emails=to_email,
            subject='URGENT: High Noise Level Detected',
            plain_text_content=f'DANGER DETECTED: Sound level at {noise_level} dB. Please move to a safer location immediately.'
        )
        sg.send(message)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

@app.route("/send_danger_alert", methods=["POST"])
def send_danger_alert_endpoint():
    try:
        data = request.get_json()
        email = data.get("email")
        noise_level = data.get("noise_level", "unknown")
        if not email:
            return jsonify({"status": "error", "message": "Email is required"}), 400
        if send_danger_alert(email, noise_level):
            return jsonify({"status": "success", "message": "Danger alert sent successfully"}), 200
        else:
            return jsonify({"status": "error", "message": "Failed to send alert"}), 500
    except Exception as e:
        print(f"Error in send_danger_alert: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route("/get_current_user_email", methods=["GET"])
def get_current_user_email():
    try:
        last_active_user = Active.query.order_by(Active.id.desc()).first()
        if last_active_user and last_active_user.email:
            return jsonify({
                "status": "success",
                "email": last_active_user.email
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "No active user found"
            }), 404
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
