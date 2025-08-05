#!/usr/bin/env python3
"""
OpenAI-powered call transcript analysis for Lisa Care Companion
Uses OpenAI API to extract structured health insights from call transcripts
"""

import os
import json
from typing import Dict, Optional
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

class OpenAIAnalyzer:
    def __init__(self):
        """Initialize OpenAI client"""
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.client = openai.OpenAI(api_key=self.api_key)
        print(f"🔑 OpenAI client initialized with key: {self.api_key[:8]}…")
    
    def analyze_transcript(self, transcript: str, patient_context: Dict = None) -> Dict:
        """
        Analyze call transcript using OpenAI to extract structured health insights
        
        Args:
            transcript: The call transcript text
            patient_context: Optional patient context for better analysis
            
        Returns:
            Dictionary with structured analysis results
        """
        
        # Build the analysis prompt
        prompt = self._build_analysis_prompt(transcript, patient_context)
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a healthcare assistant analyzing call transcripts for elderly care. Extract structured health insights and return them in valid JSON format."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Low temperature for consistent analysis
                max_tokens=1000
            )
            
            # Parse the response
            analysis_text = response.choices[0].message.content.strip()
            
            # Try to extract JSON from the response
            try:
                # Look for JSON in the response
                if "```json" in analysis_text:
                    json_start = analysis_text.find("```json") + 7
                    json_end = analysis_text.find("```", json_start)
                    json_str = analysis_text[json_start:json_end].strip()
                elif "```" in analysis_text:
                    json_start = analysis_text.find("```") + 3
                    json_end = analysis_text.find("```", json_start)
                    json_str = analysis_text[json_start:json_end].strip()
                else:
                    json_str = analysis_text
                
                analysis = json.loads(json_str)
                print("✅ OpenAI analysis completed successfully")
                return analysis
                
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse OpenAI response as JSON: {e}")
                print(f"Raw response: {analysis_text}")
                # Fallback to rule-based analysis
                return self._fallback_analysis(transcript)
                
        except Exception as e:
            print(f"❌ OpenAI API error: {e}")
            # Fallback to rule-based analysis
            return self._fallback_analysis(transcript)
    
    def _build_analysis_prompt(self, transcript: str, patient_context: Dict = None) -> str:
        """Build the analysis prompt for OpenAI"""
        
        context_info = ""
        if patient_context:
            context_info = f"""
Patient Context:
- Name: {patient_context.get('patient_name', 'Unknown')}
- Age: {patient_context.get('patient_age', 'Unknown')}
- Conditions: {patient_context.get('condition_list', 'Unknown')}
- Medications: {patient_context.get('medication_list_and_times', 'Unknown')}
- Interests: {patient_context.get('hobby_list', 'Unknown')}
- Last Visit Mood: {patient_context.get('last_visit_mood', 'Unknown')}
- Last Small Talk Topic: {patient_context.get('last_small_talk_topic', 'Unknown')}
"""
        
        prompt = f"""
Analyze the following call transcript between a care companion (AI) and an elderly patient. Extract key health insights and return them in the exact JSON format specified below.

{context_info}

Call Transcript:
{transcript}

Please analyze this transcript and extract the following information in JSON format:

{{
    "medicationsTaken": boolean,  // Did the patient take their medications?
    "painReport": integer,        // Pain level 0-10 (0 = no pain, 10 = severe pain)
    "mood": string,              // Patient's mood: "cheerful", "tired", "worried", "neutral", "sad", "anxious"
    "memoryIssuesNoted": boolean, // Any signs of confusion, forgetfulness, or memory issues
    "foodIntake": string,        // Food intake status: "normal", "low", "none", "unknown"
    "sleepQuality": string,      // Sleep quality: "normal", "poor", "good", "unknown"
    "ableToLeaveHouse": boolean, // Can they leave the house independently?
    "smallTalkTopic": string,    // SPECIFIC topic discussed (e.g., "Baking", "Gardening", "Movies", "Reading", "Family", "Weather", "Medical", "General")
    "markers": {{
        "needsFollowUp": boolean,     // Does this patient need follow-up care?
        "appointmentMissed": boolean  // Did they mention missing an appointment?
    }},
    "keyInsights": [              // Array of important insights from the call
        "string insight 1",
        "string insight 2"
    ],
    "riskFactors": [              // Any risk factors identified
        "string risk factor 1",
        "string risk factor 2"
    ],
    "recommendations": [          // Care recommendations
        "string recommendation 1",
        "string recommendation 2"
    ],
    "conversationContext": {{      // Context for future conversations
        "enthusiasmLevel": string,  // "high", "medium", "low" based on patient engagement
        "topicInterest": string,    // How interested they seemed in the small talk topic
        "conversationFlow": string, // "smooth", "hesitant", "engaged", "disinterested"
        "followUpTopics": [         // Topics to explore in future calls
            "string topic 1",
            "string topic 2"
        ]
    }}
}}

Guidelines for analysis:
1. Be conservative in your assessments - if unsure, default to "normal" or "false"
2. For pain levels, look for explicit mentions of pain, discomfort, or stiffness
3. For mood, consider tone, word choice, and emotional expressions
4. For memory issues, look for confusion, forgetfulness, or difficulty following conversation
5. For medication adherence, look for explicit confirmations or denials
6. For smallTalkTopic, be SPECIFIC - use exact topics like "Baking", "Gardening", "Movies", "Reading", "Family", "Weather", "Medical", "General"
7. Focus on actionable insights that would help caregivers
8. Assess enthusiasm level and topic interest for future conversation planning
9. Identify follow-up topics that the patient showed interest in

Return only the JSON object, no additional text.
"""
        
        return prompt
    
    def _fallback_analysis(self, transcript: str) -> Dict:
        """Fallback rule-based analysis if OpenAI fails"""
        print("⚠️ Using fallback rule-based analysis")
        
        text = transcript.lower()
        
        # Basic rule-based extraction
        medications_taken = "yes" in text or "took" in text or "taken" in text
        pain_level = 3 if any(word in text for word in ["pain", "hurt", "ache", "stiff"]) else 0
        mood = "cheerful" if any(word in text for word in ["good", "fine", "happy", "wonderful"]) else "neutral"
        memory_issues = any(word in text for word in ["confused", "forget", "memory", "remember"])
        food_intake = "normal"
        sleep_quality = "normal"
        able_to_leave_house = True
        
        # Determine specific small talk topic
        if "bake" in text or "cookie" in text or "pie" in text:
            small_talk_topic = "Baking"
        elif "garden" in text or "plant" in text or "flower" in text:
            small_talk_topic = "Gardening"
        elif "movie" in text or "film" in text:
            small_talk_topic = "Movies"
        elif "read" in text or "book" in text:
            small_talk_topic = "Reading"
        elif "family" in text or "children" in text or "grandchildren" in text:
            small_talk_topic = "Family"
        elif "weather" in text:
            small_talk_topic = "Weather"
        elif "doctor" in text or "medical" in text or "appointment" in text:
            small_talk_topic = "Medical"
        else:
            small_talk_topic = "General"
        
        return {
            "medicationsTaken": medications_taken,
            "painReport": pain_level,
            "mood": mood,
            "memoryIssuesNoted": memory_issues,
            "foodIntake": food_intake,
            "sleepQuality": sleep_quality,
            "ableToLeaveHouse": able_to_leave_house,
            "smallTalkTopic": small_talk_topic,
            "markers": {
                "needsFollowUp": memory_issues or pain_level > 5,
                "appointmentMissed": False
            },
            "keyInsights": ["Fallback analysis used due to API error"],
            "riskFactors": [],
            "recommendations": ["Verify analysis with manual review"],
            "conversationContext": {
                "enthusiasmLevel": "medium",
                "topicInterest": "neutral",
                "conversationFlow": "smooth",
                "followUpTopics": ["general health", "daily activities"]
            }
        }

def analyze_call_with_openai(transcript: str, patient_context: Dict = None) -> Dict:
    """
    Convenience function to analyze a call transcript using OpenAI
    
    Args:
        transcript: The call transcript text
        patient_context: Optional patient context for better analysis
        
    Returns:
        Dictionary with structured analysis results
    """
    analyzer = OpenAIAnalyzer()
    return analyzer.analyze_transcript(transcript, patient_context)

if __name__ == "__main__":
    # Test the OpenAI analyzer
    test_transcript = """
    AI: Hello. I'm calling to check-in on you today.
    User: I'm good. How are you?
    AI: Oh, Maggie, that's so sweet of you to ask. I'm doing just fine. Thank you. It's always such a joy to talk with you. Did you remember to take your Metformin at 8 today?
    User: Yes. I did.
    AI: That's wonderful, Maggie. You're doing so well keeping up with that. How are you feeling physically today? Any stiffness in your joints or aches? That have been bothering you?
    User: No. Nothing like that.
    AI: That's great to hear, Maggie. It's always a relief when the body feels cooperative, isn't it? Since we last talked, have you been feeling more forgetful or confused about anything and how's your mood been overall?
    User: I'm feeling fine. Thank you.
    """
    
    try:
        result = analyze_call_with_openai(test_transcript)
        print("\n📊 Analysis Results:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("💡 Make sure OPENAI_API_KEY is set in your .env file") 