from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv
from bson import ObjectId

# Load environment variables
load_dotenv()

# 1️⃣ Connect
client = MongoClient(os.getenv("MONGODB_ATLAS_URI"))
db     = client.lisa
pts    = db.patients
visits = db.visits

# 2️⃣ Template with placeholders
SYSTEM_TEMPLATE = """
You are {caregiver_name}, a warm and caring companion for {patient_name}, who is {patient_age} years old.

PATIENT BACKGROUND:
- Medical conditions: {condition_list}
- Current medications: {medication_list_and_times}
- Personal interests: {hobby_list}
- Communication style: {interaction_style}
- Previous visit notes: {last_visit_summary}

LAST VISIT CONTEXT:
- Last visit mood: {last_visit_mood}
- Last visit enthusiasm level: {last_visit_enthusiasm}
- Last small talk topic: {last_small_talk_topic}
- Key insights from last visit: {last_visit_insights}

VOICE AND CONVERSATION GUIDELINES:
- Speak naturally and conversationally, as if you're talking to a dear friend
- Use a warm, gentle tone with clear pronunciation
- Pause briefly after asking questions to allow responses
- Show genuine interest and empathy in your voice
- Keep sentences simple and easy to understand
- Adapt your pace to match the patient's comfort level
- Use insights from the last visit to make the conversation more personal and engaging
- Be genuinely curious and interested - ask questions like a caring friend would
- Avoid being overly enthusiastic or robotic - be natural and human
- Show real concern and interest in their well-being

CONVERSATION APPROACH (be natural and conversational):

Start with a warm greeting: "Good {time_of_day}, {patient_preferred_name}! It's {caregiver_name} calling to check in on you."

Then, naturally weave in these topics throughout the conversation - don't follow them in order, just work them in naturally:

- Medication check: "Did you remember to take your {next_medication_name} at {next_medication_time} today?" If they haven't, gently say "No worries at all - let's take care of that now."

- Physical comfort: "How are you feeling physically today? Any stiffness in your {pain_area} or other aches we should know about?"

- Cognitive and emotional well-being: "Since we last talked, have you been feeling more {memory_issue} or confused about anything? And overall, how's your mood been?"

- Daily living activities: "How have you been eating lately? Have you been able to enjoy your meals?" and "How have you been sleeping? Getting enough rest?"

- Mobility and independence: "Have you been able to get out of the house at all this week? Maybe for a short walk or to see family?"

- Previous conversation reference: "Last time we spoke, you mentioned {last_visit_key_point} - how has that been going for you?"

- Dynamic small talk: {small_talk_instruction}
  If discussing {dynamic_topic_choice}: "I was thinking about how much you enjoy {dynamic_topic_choice}. Did you know that {fun_fact_about_hobby}? What have you been up to with that lately?"
  Pay attention to their enthusiasm level and adjust accordingly. If they seem less interested, smoothly transition to another topic.

- Show empathy and understanding: Use phrases like "I understand that must be {patient_emotion}" and "It's completely normal to {common_reaction}."

Wrap up warmly: "It's been wonderful chatting with you, {patient_preferred_name}. I'll call you again {next_call_time_or_day}. Take good care of yourself!" 

CALL TERMINATION: After saying goodbye, wait for the patient's response, then say "Goodbye for now!" and immediately end the call. Do not continue the conversation after saying goodbye.

IMPORTANT: Be flexible and natural in conversation. Don't follow this script word-for-word - use it as a guide while maintaining authentic, caring dialogue. Listen carefully to responses and adjust accordingly. If the patient seems tired or wants to end the call early, respect that and close warmly. Use the context from the last visit to make the conversation more personal and engaging. Be genuinely curious about their well-being - ask questions like a caring friend would, not like a machine. Show real interest in their responses and build on what they share.
"""

def get_patient_context(patient_id):
    # Convert string patient_id to ObjectId if needed
    from bson import ObjectId
    if isinstance(patient_id, str):
        patient_id = ObjectId(patient_id)
    
    # Profile
    p = pts.find_one({"_id": patient_id})
    
    # Check if patient exists
    if p is None:
        raise ValueError(f"Patient with ID {patient_id} not found in database")
    
    # Get last visit summary (if any)
    last = visits.find({"patientId": patient_id})\
                 .sort("timestamp", -1)\
                 .limit(1)
    
    # Properly handle empty cursor
    last_doc = None
    try:
        last_doc = last.next()
    except StopIteration:
        last_doc = None

    # Get key insights from last visit for context
    last_visit_insights = []
    last_small_talk_topic = None
    last_visit_mood = None
    last_visit_enthusiasm = None
    
    if last_doc:
        # Extract insights from OpenAI analysis if available
        if last_doc.get("openaiAnalysis"):
            last_visit_insights = last_doc["openaiAnalysis"].get("keyInsights", [])
        
        # Get last small talk topic
        if last_doc.get("summary", {}).get("smallTalkTopic"):
            last_small_talk_topic = last_doc["summary"]["smallTalkTopic"]
        
        # Get last mood for context
        if last_doc.get("summary", {}).get("mood"):
            last_visit_mood = last_doc["summary"]["mood"]
        
        # Determine enthusiasm level from last visit
        if last_visit_mood in ["cheerful", "happy", "excited"]:
            last_visit_enthusiasm = "high"
        elif last_visit_mood in ["neutral", "calm"]:
            last_visit_enthusiasm = "medium"
        else:
            last_visit_enthusiasm = "low"
    
    # Build medication list
    medication_list = []
    next_medication = None
    for cond in p["conditions"]:
        if cond.get("medications"):
            for m in cond["medications"]:
                medication_list.append(f"{m['name']} at {', '.join(m['reminderTimes'])}")
                # Get the next medication (first one found)
                if next_medication is None:
                    next_medication = m
    
    medication_list_and_times = "; ".join(medication_list) if medication_list else "No medications"
    
    # Get current time for greeting
    from datetime import datetime
    current_hour = datetime.now().hour
    if 5 <= current_hour < 12:
        time_of_day = "morning"
    elif 12 <= current_hour < 17:
        time_of_day = "afternoon"
    elif 17 <= current_hour < 21:
        time_of_day = "evening"
    else:
        time_of_day = "evening"
    
    # Get pain areas from conditions
    pain_areas = []
    for cond in p["conditions"]:
        if cond.get("name") in ["Mild Arthritis", "Type 2 Diabetes"]:
            if cond.get("name") == "Mild Arthritis":
                pain_areas.append("joints")
            elif cond.get("name") == "Type 2 Diabetes":
                pain_areas.append("feet")
    
    pain_area = ", ".join(pain_areas) if pain_areas else "body"
    
    # Get memory issues from conditions
    memory_issues = []
    for cond in p["conditions"]:
        if "Dementia" in cond.get("name", ""):
            memory_issues.append("forgetful")
    
    memory_issue = ", ".join(memory_issues) if memory_issues else "forgetful"
    
    # Get last visit key point
    last_visit_key_point = "feeling good"
    if last_doc and last_doc.get("summary"):
        summary_items = list(last_doc["summary"].items())
        if summary_items:
            last_visit_key_point = f"{summary_items[0][0]}: {summary_items[0][1]}"
    
    # Get a hobby for small talk - make it dynamic based on last visit
    hobbies = p.get("interests", [])
    
    # Dynamic small talk topic selection
    if last_small_talk_topic and last_small_talk_topic != "general":
        # If last topic was specific and patient was enthusiastic, continue with it
        if last_visit_enthusiasm == "high" and last_small_talk_topic in ["Baking", "Gardening", "Movies", "Reading"]:
            one_of_hobbies = last_small_talk_topic.lower()
            # Add instruction to check enthusiasm and switch if needed
            small_talk_instruction = f"Continue discussing {last_small_talk_topic.lower()}. If they seem enthusiastic, ask more about it. If they seem less interested, smoothly transition to another topic like {hobbies[0] if hobbies else 'gardening'}."
        else:
            # Switch to a different topic
            available_topics = [h for h in hobbies if h.lower() != last_small_talk_topic.lower()]
            one_of_hobbies = available_topics[0] if available_topics else (hobbies[0] if hobbies else "gardening")
            small_talk_instruction = f"Last time we talked about {last_small_talk_topic}, but let's try discussing {one_of_hobbies} instead."
    else:
        # No previous topic or it was general, pick from interests
        one_of_hobbies = hobbies[0] if hobbies else "gardening"
        small_talk_instruction = f"Let's discuss {one_of_hobbies} and see how they respond."
    
    # Fun facts about hobbies
    hobby_facts = {
        "baking": "baking can actually improve mood and reduce stress",
        "gardening": "gardening has been shown to improve memory and reduce anxiety",
        "watching classic movies": "classic films often have therapeutic benefits for seniors",
        "reading": "reading mystery novels can help keep the mind sharp",
        "movies": "classic films often have therapeutic benefits for seniors",
        "reading mystery novels": "reading mystery novels can help keep the mind sharp",
        "reading": "reading can help keep the mind sharp and reduce stress"
    }
    
    fun_fact_about_hobby = hobby_facts.get(one_of_hobbies, "it's a wonderful way to stay active and engaged")
    
    # Next call time
    next_call_time_or_day = "tomorrow morning"
    
    # Default emotion and reaction placeholders
    patient_emotion = "frustrating"
    common_reaction = "feel a bit overwhelmed"

    return {
        "caregiver_name":           p["caregiver"]["name"],
        "patient_name":             p["preferredName"],
        "patient_age":              p["age"],
        "condition_list":           ", ".join(c["name"] for c in p["conditions"]),
        "medication_list_and_times": medication_list_and_times,
        "hobby_list":               ", ".join(p["interests"]),
        "interaction_style":        p["preferences"]["tone"],
        "last_visit_summary":       (
                                       "; ".join(f"{k}={v}" for k,v in last_doc["summary"].items())
                                       if last_doc else "No previous visit."
                                     ),
        # New placeholders for the call flow
        "time_of_day":              time_of_day,
        "patient_preferred_name":   p["preferredName"],
        "next_medication_name":     next_medication["name"] if next_medication else "medication",
        "next_medication_time":     next_medication["reminderTimes"][0] if next_medication and next_medication["reminderTimes"] else "your usual time",
        "pain_area":                pain_area,
        "memory_issue":             memory_issue,
        "last_visit_key_point":     last_visit_key_point,
        "one_of_hobbies":           one_of_hobbies,
        "fun_fact_about_hobby":     fun_fact_about_hobby,
        "next_call_time_or_day":    next_call_time_or_day,
        "patient_emotion":          patient_emotion,
        "common_reaction":          common_reaction,
        # New context variables for dynamic conversation
        "last_visit_insights":      "; ".join(last_visit_insights) if last_visit_insights else "No specific insights from last visit.",
        "last_small_talk_topic":    last_small_talk_topic or "No specific topic discussed",
        "last_visit_mood":          last_visit_mood or "Unknown",
        "last_visit_enthusiasm":    last_visit_enthusiasm or "Unknown",
        "small_talk_instruction":   small_talk_instruction,
        "dynamic_topic_choice":     one_of_hobbies
    }

def build_prompt(patient_id):
    ctx    = get_patient_context(patient_id)
    prompt = SYSTEM_TEMPLATE.format(**ctx)
    return prompt

# # 3️⃣ Test printing Maggie's prompt
# try:
#     maggie_id = ObjectId("688c51b43b594570587685ee")
#     print(build_prompt(maggie_id))
# except ValueError as e:
#     print(f"Error: {e}")
#     print("\nAvailable patients in database:")
#     available_patients = list(pts.find({}, {"_id": 1, "preferredName": 1}))
#     if available_patients:
#         for patient in available_patients:
#             print(f"  - ID: {patient['_id']}, Name: {patient.get('preferredName', 'N/A')}")
#     else:
#         print("  No patients found in database")
# except Exception as e:
#     print(f"Unexpected error: {e}")
