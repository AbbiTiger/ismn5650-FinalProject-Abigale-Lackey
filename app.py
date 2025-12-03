from flask import Flask, request, jsonify, render_template
from functools import wraps
from config import API_KEY
from business import analyze_tick, get_dashboard_data
from validators import validate_tick_payload

app = Flask(__name__)

def require_auth(f):
    """Decorator to enforce API key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check multiple possible header names (case-insensitive)
        api_key = (
            request.headers.get('apikey') or 
            request.headers.get('api-key') or
            request.headers.get('x-api-key') or
            request.headers.get('Authorization')
        )
        
        # Also handle Authorization: Bearer <token> format
        if api_key and api_key.startswith('Bearer '):
            api_key = api_key[7:]  # Remove 'Bearer ' prefix
        
        # Debug logging
        print(f"Received API Key: {api_key}")
        print(f"Expected API Key: {API_KEY}")
        print(f"All headers: {dict(request.headers)}")
        
        if not api_key or api_key != API_KEY:
            return jsonify({
                "result": "failure",
                "message": "Unauthorized"
            }), 401
        
        return f(*args, **kwargs)
    return decorated_function

@app.route('/healthcheck', methods=['GET'])
@require_auth
def healthcheck():
    """Health check endpoint"""
    try:
        return jsonify({
            "result": "success",
            "message": "Ready to Trade"
        }), 200
    except Exception as e:
        return jsonify({
            "result": "failure",
            "message": str(e)
        }), 200

@app.route('/tick/<trade_id>', methods=['POST'])
@require_auth
def tick(trade_id):
    """Process trading tick data with AI recommendations"""
    try:
        # Check Content-Type
        if not request.is_json:
            return jsonify({
                "result": "failure",
                "message": "Content-Type must be application/json"
            }), 400
        
        # Get payload
        payload = request.get_json()
        
        # Validate payload
        is_valid, error_message = validate_tick_payload(payload)
        if not is_valid:
            return jsonify({
                "result": "failure",
                "message": f"Invalid payload: {error_message}"
            }), 400
        
        # Process in business layer with AI logic
        result = analyze_tick(payload, trade_id)
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            "result": "failure",
            "message": f"Server error: {str(e)}"
        }), 500

@app.route('/dashboard', methods=['GET'])
def dashboard():
    """Public dashboard page to display positions and trading history"""
    try:
        # Get data from business layer
        data = get_dashboard_data()
        
        # Render template with data
        return render_template('dashboard.html', data=data)
    
    except Exception as e:
        return f"Error loading dashboard: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)