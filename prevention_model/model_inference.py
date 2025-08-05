import joblib
import pandas as pd

# Load the saved pipeline
model = joblib.load('hospitalization_model.pkl')

input = {
  "medicationsTaken": 0,
  "painReport": 1,
  "mood": "tired",
  "memoryIssuesNoted": 0,
  "foodIntake": "increased",
  "sleepQuality": "normal",
  "ableToLeaveHouse": 1,
  "needsFollowUp": 1,
  "appointmentMissed": 0,
  "smallTalkTopic": "Gardening",
  "enthusiasmLevel": "medium",
  "topicInterest": "low",
  "conversationFlow": "smooth",
  "nKeyInsights": 1,
  "nRecommendations": 0,
  "nRiskFactors": 2,
  "nFollowUpTopics": 1,
  "age": 67,
  "sex": "Male",
  "race": "Hispanic",
  "livingSituation": "alone",
  "socialSupportScore": 2,
  "admissions6m": 1,
  "edVisits6m": 0,
  "pcVisits1y": 2,
  "daysSinceLastDischarge": 137,
  "priorFall": 0,
  "systolicBP": 104.0,
  "diastolicBP": 80.0,
  "heartRate": 61.0,
  "respRate": 16.0,
  "temperature": 36.8,
  "spo2": 95.0,
  "weight": 73.3,
  "height": 1.79,
  "BMI": 22.9,
  "hemoglobin": 15.9,
  "wbc": 4.2,
  "bun": 18.2,
  "creatinine": 1.15,
  "sodium": 142.4,
  "potassium": 4.6,
  "hba1c": 6.6,
  "ntprobnp": 58.4,
  "chf": 1,
  "copd": 0,
  "ckdStage": 0,
  "diabetes": 1,
  "dementia": 0,
  "arthritis": 0,
  "cancerStatus": "Remission",
  "totalMedications": 4,
  "highRiskMedCount": 2,
  "homeOxygen": 0,
  "recentMedChange": 0,
  "adlScore": 4,
  "iadlScore": 6,
  "gaitAssessment": 26.6,
  "cognitiveScore": 12,
  "advanceDirectives": 0,
  "caseManagement": 1,
  "insurance": "Private"
}

# Convert input dictionary to DataFrame
input_df = pd.DataFrame([input])

# Make prediction
prediction = model.predict(input_df)
print(f"Prediction: {prediction[0]}")