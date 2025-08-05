#!/usr/bin/env python3
"""
Example usage of the Lisa Care Companion System
Demonstrates various ways to use the system components
"""

from complete_pipeline import run_lisa_care_call, LisaCarePipeline
from utils.get_patient_context import build_prompt, get_patient_context
from vapi_agent import VAPIAgent
from openai_analysis import analyze_call_with_openai

def example_complete_pipeline():
    """Example of running the complete pipeline"""
    print("🏥 Example: Complete Lisa Care Pipeline")
    print("=" * 50)
    
    # Patient information
    patient_id = "688c51b43b594570587685ee"  # Maggie's ID
    phone_number = "+12016736379"  # Replace with actual phone number
    
    # Run the complete pipeline
    results = run_lisa_care_call(patient_id, phone_number, max_wait_minutes=15)
    
    if results["success"]:
        print(f"✅ Pipeline completed successfully!")
        print(f"   Duration: {results['duration']:.1f} seconds")
        print(f"   Call ID: {results['call_id']}")
        
        # Show analysis results
        analysis = results.get("analysis", {})
        if analysis:
            print(f"\n📊 Health Assessment:")
            print(f"   Mood: {analysis.get('mood', 'Unknown')}")
            print(f"   Pain Level: {analysis.get('painReport', 'Unknown')}/10")
            print(f"   Medication: {'Taken' if analysis.get('medicationsTaken') else 'Missed'}")
            print(f"   Food Intake: {analysis.get('foodIntake', 'Unknown')}")
            print(f"   Sleep Quality: {analysis.get('sleepQuality', 'Unknown')}")
            print(f"   Follow-up Needed: {'Yes' if analysis.get('markers', {}).get('needsFollowUp') else 'No'}")
    else:
        print(f"❌ Pipeline failed: {results.get('error', 'Unknown error')}")

def example_patient_context_only():
    """Example of just getting patient context and prompt"""
    print("\n📋 Example: Patient Context Only")
    print("=" * 50)
    
    patient_id = "688c51b43b594570587685ee"
    
    try:
        # Get patient context
        context = get_patient_context(patient_id)
        print(f"✅ Patient Context Retrieved:")
        print(f"   Name: {context.get('patient_name')}")
        print(f"   Age: {context.get('patient_age')}")
        print(f"   Conditions: {context.get('condition_list')}")
        print(f"   Medications: {context.get('medication_list_and_times')}")
        print(f"   Interests: {context.get('hobby_list')}")
        
        # Build prompt
        prompt = build_prompt(patient_id)
        print(f"\n📝 Generated Prompt Length: {len(prompt)} characters")
        print(f"   Prompt includes enhanced health questions: {'Yes' if 'How have you been eating lately?' in prompt else 'No'}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def example_vapi_operations():
    """Example of VAPI operations"""
    print("\n📞 Example: VAPI Operations")
    print("=" * 50)
    
    try:
        vapi = VAPIAgent()
        
        # List recent calls
        calls = vapi.list_calls(limit=5)
        print(f"✅ Recent Calls: {len(calls)} found")
        
        for call in calls[:3]:  # Show first 3
            call_id = call.get('id', 'Unknown')
            status = call.get('status', 'Unknown')
            duration = call.get('calculated_duration', 0)
            print(f"   Call {call_id[:8]}... | {status} | {duration}s")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def example_openai_analysis():
    """Example of OpenAI analysis"""
    print("\n🤖 Example: OpenAI Analysis")
    print("=" * 50)
    
    # Sample transcript
    sample_transcript = """
    AI: Good evening, Maggie! It's Lisa calling to check in on you.
    User: Hello Lisa, how are you?
    AI: I'm doing well, thank you for asking! Did you remember to take your Metformin at 8 today?
    User: Yes, I did take it this morning.
    AI: That's wonderful, Maggie. How are you feeling physically today?
    User: I'm feeling pretty good today, no pain.
    AI: How have you been eating lately? Have you been able to enjoy your meals?
    User: I've been eating well, enjoying my meals.
    AI: And how have you been sleeping? Getting enough rest?
    User: I've been sleeping well, about 7-8 hours a night.
    AI: Have you been able to get out of the house at all this week?
    User: Yes, I went for a walk in the garden yesterday.
    AI: It's been wonderful chatting with you, Maggie. Take good care of yourself!
    User: Thank you, Lisa. Goodbye!
    AI: Goodbye for now!
    """
    
    try:
        # Analyze with OpenAI
        analysis = analyze_call_with_openai(sample_transcript)
        
        print(f"✅ Analysis Results:")
        print(f"   Mood: {analysis.get('mood', 'Unknown')}")
        print(f"   Pain Level: {analysis.get('painReport', 'Unknown')}/10")
        print(f"   Medication: {'Taken' if analysis.get('medicationsTaken') else 'Missed'}")
        print(f"   Food Intake: {analysis.get('foodIntake', 'Unknown')}")
        print(f"   Sleep Quality: {analysis.get('sleepQuality', 'Unknown')}")
        print(f"   Able to Leave House: {'Yes' if analysis.get('ableToLeaveHouse') else 'No'}")
        
        if analysis.get("keyInsights"):
            print(f"\n💡 Key Insights:")
            for insight in analysis["keyInsights"]:
                print(f"   • {insight}")
        
        if analysis.get("recommendations"):
            print(f"\n🎯 Recommendations:")
            for rec in analysis["recommendations"]:
                print(f"   • {rec}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """Run all examples"""
    print("🚀 Lisa Care Companion System - Examples")
    print("=" * 60)
    
    # Run examples
    example_patient_context_only()
    example_vapi_operations()
    example_openai_analysis()
    
    print(f"\n🏥 Complete Pipeline Example:")
    print("   To run a complete care call, use:")
    print("   python complete_pipeline.py")
    print("   or")
    print("   from complete_pipeline import run_lisa_care_call")
    print("   results = run_lisa_care_call(patient_id, phone_number)")

if __name__ == "__main__":
    main() 