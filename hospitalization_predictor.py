#!/usr/bin/env python3
"""
Hospitalization Prediction Module
Integrates ML model to predict hospitalization risk based on patient data and visit analysis
"""

import joblib
import pandas as pd
import os
from typing import Dict, Optional, Tuple
from datetime import datetime

class HospitalizationPredictor:
    def __init__(self, model_path: str = "prevention_model/hospitalization_model.pkl"):
        """
        Initialize the hospitalization predictor
        
        Args:
            model_path: Path to the saved ML model
        """
        self.model_path = model_path
        self.model = None
        self.load_model()
    
    def load_model(self):
        """Load the hospitalization prediction model"""
        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                print(f"✅ Hospitalization model loaded from {self.model_path}")
            else:
                print(f"⚠️ Model file not found at {self.model_path}")
                self.model = None
        except Exception as e:
            print(f"❌ Error loading hospitalization model: {e}")
            self.model = None
    
    def prepare_input_data(self, patient_context: Dict, analysis: Dict, visit_data: Dict) -> Dict:
        """
        Prepare input data for the hospitalization prediction model
        
        Args:
            patient_context: Patient context from get_patient_context
            analysis: OpenAI analysis results
            visit_data: Visit data from VAPI
            
        Returns:
            Dictionary with all required features for prediction
        """
        # Extract basic visit metrics
        summary = analysis.get('summary', {}) if isinstance(analysis, dict) else analysis
        
        # Get patient demographics
        patient_age = patient_context.get('patient_age', 65)
        patient_gender = patient_context.get('patient_gender', 'Unknown')
        
        # Extract conversation context
        conversation_context = analysis.get('conversationContext', {})
        
        # Count insights and recommendations
        n_key_insights = len(analysis.get('keyInsights', []))
        n_recommendations = len(analysis.get('recommendations', []))
        n_risk_factors = len(analysis.get('riskFactors', []))
        n_follow_up_topics = len(conversation_context.get('followUpTopics', []))
        
        # Prepare input data with defaults for missing values
        input_data = {
            # Visit-based metrics
            "medicationsTaken": 1 if summary.get('medicationsTaken') else 0,
            "painReport": summary.get('painReport', 0),
            "mood": summary.get('mood', 'neutral'),
            "memoryIssuesNoted": 1 if summary.get('memoryIssuesNoted') else 0,
            "foodIntake": summary.get('foodIntake', 'normal'),
            "sleepQuality": summary.get('sleepQuality', 'normal'),
            "ableToLeaveHouse": 1 if summary.get('ableToLeaveHouse') else 0,
            "needsFollowUp": 1 if summary.get('markers', {}).get('needsFollowUp') else 0,
            "appointmentMissed": 1 if summary.get('markers', {}).get('appointmentMissed') else 0,
            "smallTalkTopic": summary.get('smallTalkTopic', 'General'),
            
            # Conversation context
            "enthusiasmLevel": conversation_context.get('enthusiasmLevel', 'medium'),
            "topicInterest": conversation_context.get('topicInterest', 'neutral'),
            "conversationFlow": conversation_context.get('conversationFlow', 'smooth'),
            "nKeyInsights": n_key_insights,
            "nRecommendations": n_recommendations,
            "nRiskFactors": n_risk_factors,
            "nFollowUpTopics": n_follow_up_topics,
            
            # Patient demographics (with defaults)
            "age": patient_age,
            "sex": "Male" if patient_gender.lower() in ['male', 'm'] else "Female",
            "race": "White",  # Default - should be updated with actual data
            "livingSituation": "alone",  # Default - should be updated with actual data
            "socialSupportScore": 2,  # Default - should be updated with actual data
            
            # Historical data (with defaults)
            "admissions6m": 0,  # Default - should be updated with actual data
            "edVisits6m": 0,    # Default - should be updated with actual data
            "pcVisits1y": 2,    # Default - should be updated with actual data
            "daysSinceLastDischarge": 365,  # Default - should be updated with actual data
            "priorFall": 0,     # Default - should be updated with actual data
            
            # Vital signs (with defaults)
            "systolicBP": 120.0,  # Default - should be updated with actual data
            "diastolicBP": 80.0,  # Default - should be updated with actual data
            "heartRate": 72.0,    # Default - should be updated with actual data
            "respRate": 16.0,     # Default - should be updated with actual data
            "temperature": 37.0,  # Default - should be updated with actual data
            "spo2": 98.0,        # Default - should be updated with actual data
            "weight": 70.0,      # Default - should be updated with actual data
            "height": 1.70,      # Default - should be updated with actual data
            "BMI": 24.0,         # Default - should be updated with actual data
            
            # Lab values (with defaults)
            "hemoglobin": 14.0,   # Default - should be updated with actual data
            "wbc": 7.0,          # Default - should be updated with actual data
            "bun": 15.0,         # Default - should be updated with actual data
            "creatinine": 1.0,   # Default - should be updated with actual data
            "sodium": 140.0,     # Default - should be updated with actual data
            "potassium": 4.0,    # Default - should be updated with actual data
            "hba1c": 6.0,        # Default - should be updated with actual data
            "ntprobnp": 50.0,    # Default - should be updated with actual data
            
            # Medical conditions (extracted from patient context)
            "chf": 1 if any('heart' in cond.lower() or 'chf' in cond.lower() 
                           for cond in patient_context.get('condition_list', [])) else 0,
            "copd": 1 if any('copd' in cond.lower() or 'lung' in cond.lower() 
                            for cond in patient_context.get('condition_list', [])) else 0,
            "ckdStage": 0,       # Default - should be updated with actual data
            "diabetes": 1 if any('diabetes' in cond.lower() 
                                for cond in patient_context.get('condition_list', [])) else 0,
            "dementia": 1 if any('dementia' in cond.lower() or 'alzheimer' in cond.lower() 
                                for cond in patient_context.get('condition_list', [])) else 0,
            "arthritis": 1 if any('arthritis' in cond.lower() 
                                 for cond in patient_context.get('condition_list', [])) else 0,
            "cancerStatus": "None",  # Default - should be updated with actual data
            
            # Medication and functional data (with defaults)
            "totalMedications": len(patient_context.get('medication_list_and_times', '').split(',')) if patient_context.get('medication_list_and_times') else 0,
            "highRiskMedCount": 0,  # Default - should be updated with actual data
            "homeOxygen": 0,        # Default - should be updated with actual data
            "recentMedChange": 0,   # Default - should be updated with actual data
            "adlScore": 6,          # Default - should be updated with actual data
            "iadlScore": 8,         # Default - should be updated with actual data
            "gaitAssessment": 30.0, # Default - should be updated with actual data
            "cognitiveScore": 15,   # Default - should be updated with actual data
            "advanceDirectives": 0, # Default - should be updated with actual data
            "caseManagement": 0,    # Default - should be updated with actual data
            "insurance": "Private"  # Default - should be updated with actual data
        }
        
        return input_data
    
    def predict_hospitalization_risk(self, patient_context: Dict, analysis: Dict, visit_data: Dict) -> Tuple[Optional[int], Optional[float], Dict]:
        """
        Predict hospitalization risk for a patient
        
        Args:
            patient_context: Patient context from get_patient_context
            analysis: OpenAI analysis results
            visit_data: Visit data from VAPI
            
        Returns:
            Tuple of (prediction, confidence, input_data)
            - prediction: 0 (low risk) or 1 (high risk)
            - confidence: Confidence score (0-1)
            - input_data: The input data used for prediction
        """
        if not self.model:
            print("⚠️ Hospitalization model not available")
            return None, None, {}
        
        try:
            # Prepare input data
            input_data = self.prepare_input_data(patient_context, analysis, visit_data)
            
            # Convert to DataFrame
            input_df = pd.DataFrame([input_data])
            
            # Make prediction
            prediction = self.model.predict(input_df)[0]
            
            # Get prediction probability if available
            try:
                prediction_proba = self.model.predict_proba(input_df)[0]
                confidence = max(prediction_proba)  # Higher probability
            except:
                confidence = 0.8 if prediction == 1 else 0.2  # Default confidence
            
            print(f"🏥 Hospitalization Prediction:")
            print(f"   Risk Level: {'HIGH' if prediction == 1 else 'LOW'}")
            print(f"   Confidence: {confidence:.2%}")
            print(f"   Key Factors: Pain={input_data['painReport']}, Mood={input_data['mood']}, Follow-up={input_data['needsFollowUp']}")
            
            return prediction, confidence, input_data
            
        except Exception as e:
            print(f"❌ Error making hospitalization prediction: {e}")
            return None, None, {}

def predict_hospitalization_risk(patient_context: Dict, analysis: Dict, visit_data: Dict) -> Tuple[Optional[int], Optional[float], Dict]:
    """
    Convenience function to predict hospitalization risk
    
    Args:
        patient_context: Patient context from get_patient_context
        analysis: OpenAI analysis results
        visit_data: Visit data from VAPI
        
    Returns:
        Tuple of (prediction, confidence, input_data)
    """
    predictor = HospitalizationPredictor()
    return predictor.predict_hospitalization_risk(patient_context, analysis, visit_data)

if __name__ == "__main__":
    # Test the predictor
    test_patient_context = {
        "patient_age": 75,
        "patient_gender": "Female",
        "condition_list": ["Diabetes", "Hypertension", "Heart Disease"],
        "medication_list_and_times": "Metformin 500mg daily, Lisinopril 10mg daily"
    }
    
    test_analysis = {
        "mood": "tired",
        "painReport": 6,
        "medicationsTaken": False,
        "memoryIssuesNoted": True,
        "foodIntake": "low",
        "sleepQuality": "poor",
        "ableToLeaveHouse": False,
        "markers": {"needsFollowUp": True, "appointmentMissed": False},
        "smallTalkTopic": "Medical",
        "conversationContext": {
            "enthusiasmLevel": "low",
            "topicInterest": "low",
            "conversationFlow": "hesitant",
            "followUpTopics": ["medical concerns"]
        },
        "keyInsights": ["Patient seems to be declining"],
        "recommendations": ["Schedule follow-up appointment"],
        "riskFactors": ["High pain level", "Poor sleep quality"]
    }
    
    test_visit_data = {"call_id": "test123"}
    
    prediction, confidence, input_data = predict_hospitalization_risk(
        test_patient_context, test_analysis, test_visit_data
    )
    
    print(f"\nTest Results:")
    print(f"Prediction: {prediction}")
    print(f"Confidence: {confidence}")
    print(f"Risk Level: {'HIGH' if prediction == 1 else 'LOW'}") 