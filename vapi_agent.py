import os
import json
import requests
from datetime import datetime
from typing import Dict, Optional, List
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId
from utils.get_patient_context import build_prompt, get_patient_context
from dateutil.parser import isoparse
from openai_analysis import OpenAIAnalyzer
from hospitalization_predictor import predict_hospitalization_risk

# Load environment variables
load_dotenv()

class VAPIAgent:
    def __init__(self):
        self.api_key = os.getenv("VAPI_API_KEY")
        self.base_url = "https://api.vapi.ai"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        print("🔑 VAPI_AGENT key:", self.api_key[:8] + "…")
        print("📤 VAPI_AGENT headers:", self.headers)

        
        if not self.api_key:
            raise ValueError("VAPI_API_KEY not found in environment variables")
    
    def create_assistant(self, name: str, prompt: str) -> Dict:
        # """Create a VAPI assistant with the given prompt"""
        url = f"{self.base_url}/assistant"
        
        # payload = {
        #     "name": name,
        #     "model": {
        #         "provider": "openai",
        #         "model": "gpt-4",
        #         "temperature": 0.5,
        #         "systemPrompt": prompt
        #     },
        #     "voice": {
        #         "provider": "11labs",
        #         "voiceId": "pNInz6obpgDQGcFmaJgB"  # Default voice - can be customized
        #     },
        #     "firstMessage": "Hello! I'm calling to check in on you today.",
        #     "recordingEnabled": True,
        #     "interruptionThreshold": 500,
        #     "language": "en-US"
        # }

        # STEP 1: Minimal payload that we know works (201 OK)
        payload = {
            "name": name,
            "model": {
                "provider": "openai",
                "model": "gpt-4",
                "temperature": 0.5,
                "systemPrompt": prompt
            },
            "voice": {
                "provider": "11labs",
                "voiceId": "21m00Tcm4TlvDq8ikWAM"  # Female voice - Rachel (soothing and warm)
            },
            "firstMessage": "Hi, I'm Lisa, your home health caregiver's assistant. I'm just calling to check up on you today.",
            "recordingEnabled": True,
            "language": "en-US",
            "endCallFunctionEnabled": True,
            "endCallPhrases": ["goodbye", "bye", "end call", "hang up", "terminate"]
        }
 
        response = requests.post(url, headers=self.headers, json=payload)
        if response.status_code >= 400:
            import json as _json
            print("❌ create_assistant payload:")
            print(_json.dumps(payload, indent=2))
            print(f"❌ HTTP {response.status_code} error:")
            print(response.text)
        response.raise_for_status()
        return response.json()
        
        # response = requests.post(url, headers=self.headers, json=payload)
        # response.raise_for_status()
        # return response.json()
    
    def create_phone_call(self, assistant_id: str, phone_number: str, patient_name: str) -> Dict:
        """Create a phone call with the assistant"""
        url = f"{self.base_url}/call/phone"
        
        payload = {
            "assistantId":    assistant_id,
            "phoneNumberId":  os.getenv("VAPI_PHONE_NUMBER_ID"),
            "customer": {
                "number":     phone_number
            },
            "metadata": {
                "patient_name": patient_name,
                "call_type": "wellness_check",
                "timestamp": datetime.now().isoformat()
            }
        }
        
        response = requests.post(url, headers=self.headers, json=payload)
        if response.status_code >= 400:
            import json as _json
            print("❌ create_phone_call payload:")
            print(_json.dumps(payload, indent=2))
            print(f"❌ HTTP {response.status_code} error:")
            print(response.text)
        response.raise_for_status()
        return response.json()

    
    def get_call_status(self, call_id: str) -> Dict:
        """Get the status of a call"""
        url = f"{self.base_url}/call/{call_id}"
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_call_transcript(self, call_id: str) -> Optional[Dict]:
        """Get the transcript of a completed call"""
        # Get the full call data which includes the transcript
        url = f"{self.base_url}/call/{call_id}"
        
        response = requests.get(url, headers=self.headers)
        if response.status_code == 404:
            return None  # Call not found
        response.raise_for_status()
        
        call_data = response.json()
        
        # Check if transcript is embedded in the call data
        if call_data.get('transcript'):
            # Extract the transcript text and messages
            transcript_text = call_data['transcript']
            messages = call_data.get('messages', [])
            
            # Calculate duration from timestamps
            duration_seconds = None
            if call_data.get('startedAt') and call_data.get('endedAt'):
                from datetime import datetime
                start_time = datetime.fromisoformat(call_data['startedAt'].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(call_data['endedAt'].replace('Z', '+00:00'))
                duration_seconds = int((end_time - start_time).total_seconds())
            
            # Create the transcript object in the expected format
            transcript_data = {
                'transcript': transcript_text,
                'messages': messages,
                'duration': duration_seconds,
                'call_id': call_id,
                'status': call_data.get('status'),
                'ended_reason': call_data.get('endedReason'),
                'summary': call_data.get('summary'),
                'analysis': call_data.get('analysis')
            }
            
            print(f"✅ Transcript retrieved successfully from embedded data")
            print(f"   Duration: {duration_seconds} seconds")
            print(f"   Messages: {len(messages)}")
            print(f"   Ended Reason: {call_data.get('endedReason')}")
            
            return transcript_data
        
        # If no embedded transcript, try the separate transcript endpoint (fallback)
        print("⚠️  No embedded transcript found, trying separate endpoint...")
        transcript_url = f"{self.base_url}/call/{call_id}/transcript"
        response = requests.get(transcript_url, headers=self.headers)
        if response.status_code == 404:
            print("❌ Transcript not available from separate endpoint either")
            return None  # Transcript not available yet
        response.raise_for_status()
        return response.json()
    
    def list_calls(self, limit: int = 10) -> List[Dict]:
        """List recent calls"""
        url = f"{self.base_url}/call"
        params = {"limit": limit}
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        calls = response.json()
        
        # Calculate duration for each call
        for call in calls:
            if call.get('startedAt') and call.get('endedAt'):
                from datetime import datetime
                start_time = datetime.fromisoformat(call['startedAt'].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(call['endedAt'].replace('Z', '+00:00'))
                duration_seconds = int((end_time - start_time).total_seconds())
                call['calculated_duration'] = duration_seconds
            else:
                call['calculated_duration'] = 0
        
        return calls
    
    def save_call_summary(self, call_id: str, patient_id: str, transcript: Dict):
        """
        Save call summary and analysis to MongoDB
        """
        def convert_numpy_types(obj):
            """Convert numpy types to native Python types for MongoDB serialization"""
            import numpy as np
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {key: convert_numpy_types(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy_types(item) for item in obj]
            else:
                return obj
        
        try:
            # Set up MongoDB connection
            client = MongoClient(os.getenv("MONGODB_ATLAS_URI"))
            db = client.lisa
            visits = db.visits
            
            # Get patient context for analysis
            patient_context = get_patient_context(patient_id)
            
            # Analyze transcript with OpenAI
            transcript_text = transcript.get("transcript", "")
            analyzer = OpenAIAnalyzer()
            analysis = analyzer.analyze_transcript(transcript_text, patient_context)
            
            # Get hospitalization prediction
            prediction, confidence, prediction_input = predict_hospitalization_risk(
                patient_context, analysis, {"call_id": call_id}
            )
            
            # Convert numpy types in prediction_input
            prediction_input = convert_numpy_types(prediction_input)
            
            # Calculate timestamps
            timestamp_start = isoparse(transcript.get("startedAt", datetime.now().isoformat()))
            timestamp_end = isoparse(transcript.get("endedAt", datetime.now().isoformat()))
            
            # Prepare summary document
            summary = {
                "patientId": ObjectId(patient_id),
                "caregiver": patient_context.get("caregiver_name", "Lisa"),
                "timestamp": timestamp_end,
                "transcript": transcript_text,
                "summary": {
                    "medicationsTaken": analysis.get("medicationsTaken", False),
                    "painReport": analysis.get("painReport", 0),
                    "mood": analysis.get("mood", "unknown"),
                    "memoryIssuesNoted": analysis.get("memoryIssuesNoted", False),
                    "foodIntake": analysis.get("foodIntake", "unknown"),
                    "sleepQuality": analysis.get("sleepQuality", "unknown"),
                    "ableToLeaveHouse": analysis.get("ableToLeaveHouse", False),
                    "smallTalkTopic": analysis.get("smallTalkTopic", "General"),
                    "markers": {
                        "needsFollowUp": analysis.get("markers", {}).get("needsFollowUp", False),
                        "appointmentMissed": analysis.get("markers", {}).get("appointmentMissed", False)
                    }
                },
                # Add OpenAI analysis insights and recommendations
                "openaiAnalysis": {
                    "keyInsights": analysis.get("keyInsights", []),
                    "recommendations": analysis.get("recommendations", []),
                    "riskFactors": analysis.get("riskFactors", []),
                    "conversationContext": analysis.get("conversationContext", {}),
                    "analysisTimestamp": datetime.now()
                },
                # Add hospitalization prediction
                "hospitalizationPrediction": {
                    "riskLevel": "HIGH" if prediction == 1 else "LOW" if prediction == 0 else "UNKNOWN",
                    "prediction": int(prediction) if prediction is not None else None,
                    "confidence": float(confidence) if confidence is not None else None,
                    "predictionTimestamp": datetime.now(),
                    "modelInput": prediction_input
                }
            }
            
            try:
                visits.insert_one(summary, bypass_document_validation=True)
                print(f"✅ Call summary saved to database for patient {patient_id}")
                print(f"   Mood: {analysis.get('mood', 'unknown')}")
                print(f"   Medication: {'Taken' if analysis.get('medicationsTaken') else 'Missed'}")
                print(f"   Pain: {analysis.get('painReport', 0)}/10")
                print(f"   Memory Issues: {'Yes' if analysis.get('memoryIssuesNoted') else 'No'}")
                print(f"   Small Talk Topic: {analysis.get('smallTalkTopic', 'Unknown')}")
                
                # Print conversation context
                conv_context = analysis.get("conversationContext", {})
                if conv_context:
                    print(f"   Enthusiasm Level: {conv_context.get('enthusiasmLevel', 'Unknown')}")
                    print(f"   Topic Interest: {conv_context.get('topicInterest', 'Unknown')}")
                    print(f"   Conversation Flow: {conv_context.get('conversationFlow', 'Unknown')}")
                
                # Print additional insights if available
                if analysis.get("keyInsights"):
                    print(f"   Key Insights: {', '.join(analysis['keyInsights'][:2])}")
                if analysis.get("recommendations"):
                    print(f"   Recommendations: {', '.join(analysis['recommendations'][:2])}")
                
                # Print hospitalization prediction
                if prediction is not None:
                    risk_level = "HIGH" if prediction == 1 else "LOW"
                    print(f"   🏥 Hospitalization Risk: {risk_level} (Confidence: {confidence:.1%})")
                else:
                    print(f"   🏥 Hospitalization Risk: Model not available")
                        
            except Exception as e:
                print(f"❌ Error saving call summary: {e}")
                print("💡 This might be due to MongoDB schema validation requirements")
                
        except Exception as e:
            print(f"❌ Error in save_call_summary: {e}")
    
    def check_transcript_availability(self, call_id: str) -> bool:
        """Check if transcript is available for a call"""
        try:
            call_data = self.get_call_details(call_id)
            return call_data.get('transcript') is not None
        except Exception as e:
            print(f"Error checking transcript availability: {e}")
            return False

    def get_call_details(self, call_id: str) -> Dict:
        """Get detailed information about a call including transcript status"""
        url = f"{self.base_url}/call/{call_id}"
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        call_data = response.json()
        
        # Calculate duration from timestamps
        duration_seconds = None
        if call_data.get('startedAt') and call_data.get('endedAt'):
            from datetime import datetime
            start_time = datetime.fromisoformat(call_data['startedAt'].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(call_data['endedAt'].replace('Z', '+00:00'))
            duration_seconds = int((end_time - start_time).total_seconds())
        
        print(f"📞 Call Details for {call_id}:")
        print(f"   Status: {call_data.get('status')}")
        print(f"   Duration: {duration_seconds} seconds")
        print(f"   Created: {call_data.get('createdAt')}")
        print(f"   Ended: {call_data.get('endedAt')}")
        print(f"   Has Transcript: {call_data.get('transcript') is not None}")
        print(f"   Ended Reason: {call_data.get('endedReason')}")
        
        # Add calculated duration to the response
        call_data['calculated_duration'] = duration_seconds
        
        return call_data

def initiate_care_call(patient_id: str, phone_number: str) -> Dict:
    """Main function to initiate a care call for a patient"""
    try:
        # Initialize VAPI agent
        vapi = VAPIAgent()
        
        # Get patient context and build prompt
        prompt = build_prompt(patient_id)
        
        # Create assistant with patient-specific prompt
        assistant = vapi.create_assistant(
            name=f"{patient_id}",
            prompt=prompt
        )
        
        print(f"Created assistant: {assistant['id']}")
        
        # Get patient name for the call
        from pymongo import MongoClient
        from bson import ObjectId
        
        client = MongoClient(os.getenv("MONGODB_ATLAS_URI"))
        db = client.lisa
        patient = db.patients.find_one({"_id": ObjectId(patient_id)})
        patient_name = patient.get("preferredName", "Patient") if patient else "Patient"
        
        # Create phone call
        call = vapi.create_phone_call(
            assistant_id=assistant["id"],
            phone_number=phone_number,
            patient_name=patient_name
        )
        
        print(f"Initiated call: {call['id']}")
        print(f"Call status: {call['status']}")
        
        return {
            "call_id": call["id"],
            "assistant_id": assistant["id"],
            "status": call["status"],
            "patient_id": patient_id
        }
        
    except Exception as e:
        print(f"Error initiating call: {e}")
        raise

def monitor_call_and_get_transcript(call_id: str, patient_id: str, max_wait_minutes: int = 10) -> Optional[Dict]:
    """Monitor a call and retrieve transcript when completed"""
    import time
    
    vapi = VAPIAgent()
    
    print(f"Monitoring call {call_id}...")
    
    # Wait for call to complete
    start_time = time.time()
    while time.time() - start_time < max_wait_minutes * 60:
        status = vapi.get_call_status(call_id)
        print(f"Call status: {status['status']}")
        
        if status['status'] in ['completed', 'ended']:
            break
        elif status['status'] in ['failed', 'cancelled']:
            print(f"Call {status['status']}")
            return None
        
        time.sleep(30)  # Check every 30 seconds
    
    # Wait a bit longer for transcript processing
    print("Call ended. Waiting for transcript processing...")
    time.sleep(60)  # Wait 1 minute for transcript to be processed
    
    # Try to get transcript multiple times
    max_attempts = 5
    for attempt in range(max_attempts):
        print(f"Attempting to retrieve transcript (attempt {attempt + 1}/{max_attempts})...")
        transcript = vapi.get_call_transcript(call_id)
        
        if transcript:
            print("✅ Transcript retrieved successfully")
            # Save to database
            vapi.save_call_summary(call_id, patient_id, transcript)
            return transcript
        else:
            print(f"Transcript not available yet (attempt {attempt + 1})")
            if attempt < max_attempts - 1:
                time.sleep(30)  # Wait 30 seconds before next attempt
    
    print("❌ Transcript could not be retrieved after multiple attempts")
    print("💡 This might be due to:")
    print("   - Call was too short")
    print("   - No conversation occurred")
    print("   - VAPI processing delay")
    print("   - API configuration issue")
    
    return None

if __name__ == "__main__":
    # Example usage
    patient_id = "688c51b43b594570587685ee"  # Maggie's ID
    phone_number = "+15513394103"  # Replace with actual phone number
    
    # Check if we have valid API keys before making calls
    vapi_key = os.getenv("VAPI_API_KEY")
    if not vapi_key or vapi_key == "your_vapi_api_key_here":
        print("⚠️  VAPI API key not configured properly")
        print("Please add your VAPI_API_KEY to the .env file")
        print("Example: VAPI_API_KEY=your_actual_vapi_key_here")
        print("\nFor testing without making actual calls, run:")
        print("python test_vapi_integration.py")
        exit(1)
    
    try:
        # Test the prompt generation first
        print("📝 Testing prompt generation...")
        prompt = build_prompt(patient_id)
        print(f"✅ Prompt generated successfully ({len(prompt)} characters)")
        
        # Initiate call
        print("\n📞 Initiating care call...")
        call_info = initiate_care_call(patient_id, phone_number)
        
        # Monitor call and get transcript
        print("\n📊 Monitoring call...")
        transcript = monitor_call_and_get_transcript(call_info["call_id"], patient_id)
        
        if transcript:
            print("✅ Call completed successfully!")
            print(f"Duration: {transcript.get('duration', 'Unknown')} seconds")
            print(f"Messages: {len(transcript.get('messages', []))}")
        else:
            print("❌ Call failed or transcript not available")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Troubleshooting tips:")
        print("1. Check your VAPI_API_KEY in .env file")
        print("2. Verify your VAPI account is active")
        print("3. Ensure the phone number is valid")
        print("4. Run 'python test_vapi_integration.py' for testing") 