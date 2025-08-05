#!/usr/bin/env python3
"""
Complete Lisa Care Companion Pipeline
Orchestrates the entire workflow: fetch patient data → make call → analyze → save data
"""

import os
import time
import json
from datetime import datetime
from typing import Dict, Optional
from dotenv import load_dotenv

# Import our modules
from utils.get_patient_context import get_patient_context, build_prompt
from vapi_agent import VAPIAgent, initiate_care_call, monitor_call_and_get_transcript
from openai_analysis import OpenAIAnalyzer
from hospitalization_predictor import predict_hospitalization_risk

# Load environment variables
load_dotenv()

class LisaCarePipeline:
    def __init__(self):
        """Initialize the complete care pipeline"""
        self.vapi_agent = VAPIAgent()
        self.openai_analyzer = OpenAIAnalyzer()
        print("🚀 Lisa Care Pipeline initialized")
    
    def fetch_patient_data(self, patient_id: str) -> Dict:
        """
        Fetch comprehensive patient data and context
        
        Args:
            patient_id: Patient's MongoDB ObjectId
            
        Returns:
            Dictionary with patient context and prompt
        """
        print(f"\n📋 Fetching patient data for {patient_id}...")
        
        try:
            # Get patient context
            patient_context = get_patient_context(patient_id)
            
            # Build personalized prompt
            prompt = build_prompt(patient_id)
            
            print(f"✅ Patient data fetched successfully")
            print(f"   Name: {patient_context.get('patient_name', 'Unknown')}")
            print(f"   Age: {patient_context.get('patient_age', 'Unknown')}")
            print(f"   Conditions: {patient_context.get('condition_list', 'Unknown')}")
            print(f"   Medications: {patient_context.get('medication_list_and_times', 'Unknown')}")
            print(f"   Interests: {patient_context.get('hobby_list', 'Unknown')}")
            
            return {
                "patient_context": patient_context,
                "prompt": prompt,
                "patient_id": patient_id
            }
            
        except Exception as e:
            print(f"❌ Error fetching patient data: {e}")
            raise
    
    def initiate_call(self, patient_data: Dict, phone_number: str) -> Dict:
        """
        Initiate a care call using the patient's personalized prompt
        
        Args:
            patient_data: Patient data and prompt from fetch_patient_data
            phone_number: Patient's phone number
            
        Returns:
            Call information including call_id and status
        """
        print(f"\n📞 Initiating care call...")
        
        try:
            # Get patient name for call metadata
            patient_name = patient_data["patient_context"].get("patient_name", "Patient")
            
            # Initiate the call
            call_info = initiate_care_call(
                patient_id=patient_data["patient_id"],
                phone_number=phone_number
            )
            
            print(f"✅ Call initiated successfully")
            print(f"   Call ID: {call_info['call_id']}")
            print(f"   Status: {call_info['status']}")
            print(f"   Patient: {patient_name}")
            
            return call_info
            
        except Exception as e:
            print(f"❌ Error initiating call: {e}")
            raise
    
    def monitor_and_get_transcript(self, call_id: str, patient_id: str, max_wait_minutes: int = 15) -> Optional[Dict]:
        """
        Monitor the call and retrieve transcript when completed
        
        Args:
            call_id: VAPI call ID
            patient_id: Patient's MongoDB ObjectId
            max_wait_minutes: Maximum time to wait for call completion
            
        Returns:
            Call transcript and metadata
        """
        print(f"\n📊 Monitoring call {call_id}...")
        
        try:
            # Monitor call and get transcript
            transcript = monitor_call_and_get_transcript(
                call_id=call_id,
                patient_id=patient_id,
                max_wait_minutes=max_wait_minutes
            )
            
            if transcript:
                print(f"✅ Call completed successfully")
                print(f"   Duration: {transcript.get('duration', 'Unknown')} seconds")
                print(f"   Messages: {len(transcript.get('messages', []))}")
                print(f"   Ended Reason: {transcript.get('ended_reason', 'Unknown')}")
                return transcript
            else:
                print(f"❌ Call failed or transcript not available")
                return None
                
        except Exception as e:
            print(f"❌ Error monitoring call: {e}")
            return None
    
    def analyze_transcript(self, transcript: Dict, patient_context: Dict) -> Dict:
        """
        Analyze call transcript using OpenAI and predict hospitalization risk
        
        Args:
            transcript: Call transcript from VAPI
            patient_context: Patient context for better analysis
            
        Returns:
            Structured analysis results including hospitalization prediction
        """
        print(f"\n🤖 Analyzing transcript with OpenAI...")
        
        try:
            # Extract transcript text
            transcript_text = transcript.get("transcript", "")
            
            if not transcript_text:
                print("⚠️ No transcript text available for analysis")
                return {}
            
            # Analyze with OpenAI
            analysis = self.openai_analyzer.analyze_transcript(
                transcript=transcript_text,
                patient_context=patient_context
            )
            
            # Get hospitalization prediction
            print(f"\n🏥 Predicting hospitalization risk...")
            prediction, confidence, prediction_input = predict_hospitalization_risk(
                patient_context, analysis, {"call_id": transcript.get("call_id", "unknown")}
            )
            
            # Add hospitalization prediction to analysis results
            analysis["hospitalizationPrediction"] = {
                "riskLevel": "HIGH" if prediction == 1 else "LOW" if prediction == 0 else "UNKNOWN",
                "prediction": prediction,
                "confidence": confidence,
                "predictionTimestamp": datetime.now(),
                "modelInput": prediction_input
            }
            
            print(f"✅ Analysis completed successfully")
            print(f"   Mood: {analysis.get('mood', 'Unknown')}")
            print(f"   Pain Level: {analysis.get('painReport', 'Unknown')}/10")
            print(f"   Medication: {'Taken' if analysis.get('medicationsTaken') else 'Missed'}")
            print(f"   Memory Issues: {'Yes' if analysis.get('memoryIssuesNoted') else 'No'}")
            print(f"   Food Intake: {analysis.get('foodIntake', 'Unknown')}")
            print(f"   Sleep Quality: {analysis.get('sleepQuality', 'Unknown')}")
            print(f"   Able to Leave House: {'Yes' if analysis.get('ableToLeaveHouse') else 'No'}")
            
            # Print hospitalization prediction
            if prediction is not None:
                risk_level = "HIGH" if prediction == 1 else "LOW"
                print(f"   🏥 Hospitalization Risk: {risk_level} (Confidence: {confidence:.1%})")
            else:
                print(f"   🏥 Hospitalization Risk: Model not available")
            
            # Print insights and recommendations
            if analysis.get("keyInsights"):
                print(f"   Key Insights: {', '.join(analysis['keyInsights'][:2])}")
            if analysis.get("recommendations"):
                print(f"   Recommendations: {', '.join(analysis['recommendations'][:2])}")
            
            return analysis
            
        except Exception as e:
            print(f"❌ Error analyzing transcript: {e}")
            return {}
    
    def save_visit_data(self, call_id: str, patient_id: str, transcript: Dict, analysis: Dict) -> bool:
        """
        Save complete visit data to MongoDB
        
        Args:
            call_id: VAPI call ID
            patient_id: Patient's MongoDB ObjectId
            transcript: Call transcript from VAPI
            analysis: OpenAI analysis results
            
        Returns:
            True if saved successfully, False otherwise
        """
        print(f"\n💾 Saving visit data to MongoDB...")
        
        try:
            # Save using the VAPI agent's method
            self.vapi_agent.save_call_summary(
                call_id=call_id,
                patient_id=patient_id,
                transcript=transcript
            )
            
            print(f"✅ Visit data saved successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error saving visit data: {e}")
            return False
    
    def run_complete_pipeline(self, patient_id: str, phone_number: str, max_wait_minutes: int = 15) -> Dict:
        """
        Run the complete Lisa care pipeline
        
        Args:
            patient_id: Patient's MongoDB ObjectId
            phone_number: Patient's phone number
            max_wait_minutes: Maximum time to wait for call completion
            
        Returns:
            Complete pipeline results
        """
        print("=" * 60)
        print("🏥 LISA CARE COMPANION - COMPLETE PIPELINE")
        print("=" * 60)
        
        start_time = datetime.now()
        results = {
            "success": False,
            "patient_id": patient_id,
            "phone_number": phone_number,
            "start_time": start_time,
            "end_time": None,
            "duration": None,
            "steps": {}
        }
        
        try:
            # Step 1: Fetch patient data
            print(f"\n🔄 STEP 1: Fetching patient data...")
            patient_data = self.fetch_patient_data(patient_id)
            results["steps"]["patient_data"] = {
                "success": True,
                "patient_context": patient_data["patient_context"]
            }
            
            # Step 2: Initiate call
            print(f"\n🔄 STEP 2: Initiating care call...")
            call_info = self.initiate_call(patient_data, phone_number)
            results["steps"]["call_initiation"] = {
                "success": True,
                "call_id": call_info["call_id"],
                "status": call_info["status"]
            }
            
            # Step 3: Monitor call and get transcript
            print(f"\n🔄 STEP 3: Monitoring call and retrieving transcript...")
            transcript = self.monitor_and_get_transcript(
                call_id=call_info["call_id"],
                patient_id=patient_id,
                max_wait_minutes=max_wait_minutes
            )
            
            if not transcript:
                results["steps"]["call_monitoring"] = {"success": False, "error": "No transcript available"}
                raise Exception("Call failed or transcript not available")
            
            results["steps"]["call_monitoring"] = {
                "success": True,
                "duration": transcript.get("duration"),
                "messages": len(transcript.get("messages", [])),
                "ended_reason": transcript.get("ended_reason")
            }
            
            # Step 4: Analyze transcript
            print(f"\n🔄 STEP 4: Analyzing transcript with OpenAI...")
            analysis = self.analyze_transcript(transcript, patient_data["patient_context"])
            results["steps"]["analysis"] = {
                "success": True,
                "analysis": analysis
            }
            
            # Step 5: Save visit data
            print(f"\n🔄 STEP 5: Saving visit data to MongoDB...")
            save_success = self.save_visit_data(
                call_id=call_info["call_id"],
                patient_id=patient_id,
                transcript=transcript,
                analysis=analysis
            )
            results["steps"]["data_save"] = {
                "success": save_success
            }
            
            # Calculate duration
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            results.update({
                "success": True,
                "end_time": end_time,
                "duration": duration,
                "call_id": call_info["call_id"],
                "transcript": transcript,
                "analysis": analysis
            })
            
            print(f"\n🎉 PIPELINE COMPLETED SUCCESSFULLY!")
            print(f"   Total Duration: {duration:.1f} seconds")
            print(f"   Call Duration: {transcript.get('duration', 'Unknown')} seconds")
            print(f"   Patient: {patient_data['patient_context'].get('patient_name', 'Unknown')}")
            print(f"   Mood: {analysis.get('mood', 'Unknown')}")
            print(f"   Follow-up Needed: {'Yes' if analysis.get('markers', {}).get('needsFollowUp') else 'No'}")
            
            # Print hospitalization risk
            hospitalization_pred = analysis.get('hospitalizationPrediction', {})
            if hospitalization_pred.get('prediction') is not None:
                risk_level = hospitalization_pred.get('riskLevel', 'UNKNOWN')
                confidence = hospitalization_pred.get('confidence', 0)
                print(f"   🏥 Hospitalization Risk: {risk_level} (Confidence: {confidence:.1%})")
            else:
                print(f"   🏥 Hospitalization Risk: Model not available")
            
        except Exception as e:
            print(f"\n❌ PIPELINE FAILED: {e}")
            results["success"] = False
            results["error"] = str(e)
            results["end_time"] = datetime.now()
            results["duration"] = (results["end_time"] - start_time).total_seconds()
        
        return results

def run_lisa_care_call(patient_id: str, phone_number: str, max_wait_minutes: int = 15) -> Dict:
    """
    Convenience function to run a complete Lisa care call
    
    Args:
        patient_id: Patient's MongoDB ObjectId
        phone_number: Patient's phone number
        max_wait_minutes: Maximum time to wait for call completion
        
    Returns:
        Complete pipeline results
    """
    pipeline = LisaCarePipeline()
    return pipeline.run_complete_pipeline(patient_id, phone_number, max_wait_minutes)

if __name__ == "__main__":
    # Example usage
    patient_id = "688c51b43b594570587685ee"  # Maggie's ID
    phone_number = "+15513394103"  # Replace with actual phone number
    # phone_number = "+12153014812"
    
    # Check environment variables
    required_vars = ["MONGODB_ATLAS_URI", "VAPI_API_KEY", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please add them to your .env file")
        exit(1)
    
    # Run the complete pipeline
    results = run_lisa_care_call(patient_id, phone_number)
    
    # Print summary
    if results["success"]:
        print(f"\n📊 PIPELINE SUMMARY:")
        print(f"   Status: ✅ Success")
        print(f"   Duration: {results['duration']:.1f} seconds")
        print(f"   Call ID: {results['call_id']}")
        
        analysis = results.get("analysis", {})
        if analysis:
            print(f"   Patient Mood: {analysis.get('mood', 'Unknown')}")
            print(f"   Pain Level: {analysis.get('painReport', 'Unknown')}/10")
            print(f"   Follow-up Needed: {'Yes' if analysis.get('markers', {}).get('needsFollowUp') else 'No'}")
            
            # Print hospitalization risk
            hospitalization_pred = analysis.get('hospitalizationPrediction', {})
            if hospitalization_pred.get('prediction') is not None:
                risk_level = hospitalization_pred.get('riskLevel', 'UNKNOWN')
                confidence = hospitalization_pred.get('confidence', 0)
                print(f"   🏥 Hospitalization Risk: {risk_level} (Confidence: {confidence:.1%})")
            else:
                print(f"   🏥 Hospitalization Risk: Model not available")
    else:
        print(f"\n❌ PIPELINE FAILED: {results.get('error', 'Unknown error')}") 