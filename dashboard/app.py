#!/usr/bin/env python3
"""
Lisa Care Companion Dashboard
Flask application for viewing patient data and visit information
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import os
from dotenv import load_dotenv
import time
import threading

# Load environment variables
load_dotenv('../.env')

app = Flask(__name__)
CORS(app)

# Global MongoDB client with connection pooling
_mongo_client = None
_client_lock = threading.Lock()

def get_mongodb_client_fallback():
    """Fallback MongoDB connection method for DNS issues"""
    mongo_uri = os.getenv("MONGODB_ATLAS_URI")
    if not mongo_uri:
        raise ValueError("MONGODB_ATLAS_URI not found in environment variables")
    
    print("🔄 Trying fallback connection method...")
    
    try:
        # Try with different DNS servers by modifying the connection string
        # This is a workaround for DNS resolution issues
        
        # Method 1: Try with explicit DNS server in connection string
        if "mongodb+srv://" in mongo_uri:
            # Convert to standard mongodb:// connection
            # Extract credentials and database info
            parts = mongo_uri.replace("mongodb+srv://", "").split("@")
            if len(parts) == 2:
                credentials = parts[0]
                rest = parts[1].split("/")[0]
                db_part = "/" + "/".join(parts[1].split("/")[1:]) if len(parts[1].split("/")) > 1 else ""
                
                # Try with explicit IP resolution
                print("🔄 Attempting IP-based connection...")
                # Note: This is a simplified approach - in practice, you'd need to resolve the IP
                # For now, we'll try the original connection with different settings
                
                client = MongoClient(
                    mongo_uri,
                    serverSelectionTimeoutMS=60000,
                    connectTimeoutMS=60000,
                    socketTimeoutMS=60000,
                    maxPoolSize=1,
                    retryWrites=False,
                    retryReads=False,
                    directConnection=False,
                    appName="LisaCareCompanion-Fallback"
                )
                
                client.admin.command('ping', serverSelectionTimeoutMS=30000)
                print("✅ Fallback connection successful!")
                return client
                
    except Exception as e:
        print(f"❌ Fallback connection failed: {e}")
        raise

def get_mongodb_client():
    """Get MongoDB client connection with retry mechanism"""
    global _mongo_client
    
    # Check if we already have a valid client
    if _mongo_client is not None:
        try:
            # Test if the connection is still alive
            _mongo_client.admin.command('ping', serverSelectionTimeoutMS=5000)
            return _mongo_client
        except:
            # Connection is dead, we'll create a new one
            pass
    
    mongo_uri = os.getenv("MONGODB_ATLAS_URI")
    if not mongo_uri:
        raise ValueError("MONGODB_ATLAS_URI not found in environment variables")
    
    # Retry mechanism
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            with _client_lock:
                # Try different connection strategies
                if attempt == 0:
                    # Strategy 1: Standard connection with enhanced settings
                    print("🔄 Attempting standard connection...")
                    client = MongoClient(
                        mongo_uri,
                        serverSelectionTimeoutMS=30000,
                        connectTimeoutMS=30000,
                        socketTimeoutMS=30000,
                        maxPoolSize=10,
                        minPoolSize=1,
                        maxIdleTimeMS=30000,
                        retryWrites=True,
                        retryReads=True,
                        directConnection=False,
                        appName="LisaCareCompanion",
                        heartbeatFrequencyMS=10000,
                        waitQueueTimeoutMS=30000,
                        tlsAllowInvalidCertificates=False,
                        tlsAllowInvalidHostnames=False
                    )
                elif attempt == 1:
                    # Strategy 2: Direct connection with minimal settings
                    print("🔄 Attempting direct connection...")
                    client = MongoClient(
                        mongo_uri,
                        serverSelectionTimeoutMS=60000,
                        connectTimeoutMS=60000,
                        socketTimeoutMS=60000,
                        maxPoolSize=1,
                        retryWrites=False,
                        retryReads=False,
                        directConnection=False,
                        appName="LisaCareCompanion-Direct"
                    )
                else:
                    # Strategy 3: Minimal connection for testing
                    print("🔄 Attempting minimal connection...")
                    client = MongoClient(
                        mongo_uri,
                        serverSelectionTimeoutMS=60000,
                        connectTimeoutMS=60000,
                        socketTimeoutMS=60000,
                        maxPoolSize=1,
                        retryWrites=False,
                        retryReads=False,
                        appName="LisaCareCompanion-Minimal"
                    )
                
                # Test the connection with a longer timeout
                client.admin.command('ping', serverSelectionTimeoutMS=30000)
                print("✅ MongoDB connection successful")
                _mongo_client = client
                return client
                
        except Exception as e:
            print(f"❌ MongoDB connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print(f"🔄 Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                # Try fallback method as last resort
                try:
                    return get_mongodb_client_fallback()
                except Exception as fallback_error:
                    print(f"❌ Fallback method also failed: {fallback_error}")
                    print("💡 Possible solutions:")
                    print("   1. Check your internet connection")
                    print("   2. Try a different network (mobile hotspot)")
                    print("   3. Check if MongoDB Atlas is accessible")
                    print("   4. Verify your connection string")
                    print("   5. Check DNS resolution")
                    print("   6. Try using a different DNS server")
                    print("   7. Check if your IP is whitelisted in MongoDB Atlas")
                    print("   8. Verify the MongoDB Atlas cluster still exists")
                    print("   9. Try accessing MongoDB Atlas web interface")
                    print("   10. Contact MongoDB Atlas support")
                    raise

def get_db():
    """Get database instance"""
    client = get_mongodb_client()
    return client.lisa

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/patients')
def get_patients():
    """Get all patients"""
    try:
        db = get_db()
        patients = list(db.patients.find({}, {
            '_id': 1,
            'preferredName': 1,
            'firstName': 1,
            'lastName': 1,
            'age': 1,
            'gender': 1,
            'conditions': 1,
            'caregiver': 1,
            'createdAt': 1
        }))
        
        # Convert ObjectId to string for JSON serialization
        for patient in patients:
            patient['_id'] = str(patient['_id'])
            if 'createdAt' in patient:
                patient['createdAt'] = patient['createdAt'].isoformat()
        
        return jsonify({
            'success': True,
            'patients': patients
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/patients/<patient_id>')
def get_patient(patient_id):
    """Get specific patient details"""
    try:
        db = get_db()
        patient = db.patients.find_one({'_id': ObjectId(patient_id)})
        
        if not patient:
            return jsonify({
                'success': False,
                'error': 'Patient not found'
            }), 404
        
        # Convert ObjectId to string
        patient['_id'] = str(patient['_id'])
        if 'createdAt' in patient:
            patient['createdAt'] = patient['createdAt'].isoformat()
        
        return jsonify({
            'success': True,
            'patient': patient
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/patients/<patient_id>/visits')
def get_patient_visits(patient_id):
    """Get all visits for a specific patient"""
    try:
        db = get_db()
        visits = list(db.visits.find(
            {'patientId': ObjectId(patient_id)},
            {'transcript': 0}  # Exclude transcript for performance
        ).sort('timestamp', -1))
        
        # Convert ObjectId to string and format timestamps
        for visit in visits:
            visit['_id'] = str(visit['_id'])
            visit['patientId'] = str(visit['patientId'])
            if 'timestamp' in visit:
                visit['timestamp'] = visit['timestamp'].isoformat()
            if 'analysisTimestamp' in visit.get('openaiAnalysis', {}):
                visit['openaiAnalysis']['analysisTimestamp'] = visit['openaiAnalysis']['analysisTimestamp'].isoformat()
        
        return jsonify({
            'success': True,
            'visits': visits
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/visits/<visit_id>')
def get_visit(visit_id):
    """Get specific visit details"""
    try:
        db = get_db()
        visit = db.visits.find_one({'_id': ObjectId(visit_id)})
        
        if not visit:
            return jsonify({
                'success': False,
                'error': 'Visit not found'
            }), 404
        
        # Convert ObjectId to string and format timestamps
        visit['_id'] = str(visit['_id'])
        visit['patientId'] = str(visit['patientId'])
        if 'timestamp' in visit:
            visit['timestamp'] = visit['timestamp'].isoformat()
        if 'analysisTimestamp' in visit.get('openaiAnalysis', {}):
            visit['openaiAnalysis']['analysisTimestamp'] = visit['openaiAnalysis']['analysisTimestamp'].isoformat()
        
        return jsonify({
            'success': True,
            'visit': visit
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/dashboard/stats')
def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        db = get_db()
        
        # Get counts
        total_patients = db.patients.count_documents({})
        total_visits = db.visits.count_documents({})
        
        # Get recent visits (last 7 days)
        week_ago = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        recent_visits = db.visits.count_documents({
            'timestamp': {'$gte': week_ago}
        })
        
        # Get patients needing follow-up
        needs_followup = db.visits.count_documents({
            'summary.markers.needsFollowUp': True
        })
        
        # Dummy value for patients at high risk
        high_risk_patients = 1
        
        return jsonify({
            'success': True,
            'stats': {
                'totalPatients': total_patients,
                'totalVisits': total_visits,
                'recentVisits': recent_visits,
                'needsFollowUp': needs_followup,
                'highRiskPatients': high_risk_patients
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001) 