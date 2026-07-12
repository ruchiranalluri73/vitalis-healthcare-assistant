"""
gemini_api.py
-------------
Handles all communication with Google's Gemini API.

Responsibilities:
  1. generate_recommendations(prediction_result, user_data) -> dict
     Produces the structured post-prediction health guidance shown on
     result.html (overview, foods to eat/avoid, diet plan, exercise
     plan, lifestyle tips, water intake, doctor advice).
  2. ask_question(question, context, history) -> str
     Powers the free-form chatbot page for follow-up health questions,
     using a real multi-turn Gemini chat session so it remembers the
     conversation instead of re-introducing itself every message.

IMPORTANT: Gemini NEVER predicts disease. Disease prediction is always
done locally via the scikit-learn .pkl models in prediction/. Gemini is
only used to generate personalized, human-readable recommendations and
to answer general follow-up questions.

Set your API key as an environment variable before running the app:
    export GEMINI_API_KEY="your_key_here"

If no API key is configured, this module gracefully falls back to a
built-in static template so the app still functions end-to-end.
"""
import os
import json
from dotenv import load_dotenv
from google import genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

print("API KEY:", GEMINI_API_KEY[:10] if GEMINI_API_KEY else "NOT FOUND")

client = genai.Client(api_key=GEMINI_API_KEY)

GEMINI_MODEL = "gemini-3.5-flash"


def _call_gemini(prompt: str) -> str:
    """Send a single one-shot prompt to Gemini using the official SDK.
    Used for generate_recommendations, which doesn't need conversation memory."""

    if not GEMINI_API_KEY:
        raise RuntimeError("Gemini API Key not found.")

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )

        print("Gemini Response:")
        print(response.text)

        return response.text

    except Exception as e:
        print("Gemini SDK Error:", e)
        raise


def _fallback_recommendations(disease: str, prediction_label: str) -> dict:
    """Static fallback used only if Gemini is unreachable / not configured."""
    positive = "Detected" in prediction_label and "No" not in prediction_label
    return {
        "overview": (
            f"This is a general information summary about {disease}. "
            "Please consult a certified physician for an official diagnosis "
            "and treatment plan."
        ),
        "foods_to_eat": [
            "Leafy green vegetables", "Whole grains", "Lean proteins (fish, legumes)",
            "Nuts and seeds", "Fresh fruits (in moderation)"
        ],
        "foods_to_avoid": [
            "Sugary drinks and snacks", "Deep-fried foods", "Excess red/processed meat",
            "High-sodium packaged foods", "Refined carbohydrates"
        ],
        "weekly_diet_plan": (
            "Mon-Fri: balanced meals with vegetables, lean protein, and whole grains. "
            "Weekend: lighter portions, more fruit and hydration, limit processed food."
        ),
        "exercise_plan": (
            "30 minutes of moderate aerobic activity (brisk walking, cycling) "
            "5 days a week, plus light strength training twice a week. "
            "Consult your doctor before starting any new exercise routine."
        ),
        "lifestyle_tips": [
            "Maintain a consistent sleep schedule (7-8 hours)",
            "Manage stress through mindfulness or light yoga",
            "Avoid smoking and limit alcohol consumption",
            "Schedule regular health checkups"
        ],
        "water_intake": "Aim for 8-10 glasses (about 2-2.5 liters) of water daily.",
        "doctor_consultation": (
            "This result is high risk, please consult a doctor promptly for further tests."
            if positive else
            "Continue routine annual checkups to monitor your health."
        ),
    }

def _fallback_diet_plan(disease: str, label: str, plan_days: int, duration_label: str) -> dict:
    """Static fallback used only if Gemini is unreachable / not configured."""
    template_days = [
        {"day_label": f"Day {i+1}",
         "breakfast": "Oatmeal with berries and a handful of nuts",
         "lunch": "Grilled chicken or lentils with mixed greens and olive oil",
         "dinner": "Baked fish or tofu with steamed vegetables and quinoa",
         "snacks": "Greek yogurt or a piece of fruit"}
        for i in range(plan_days)
    ]
    return {
        "duration_label": duration_label,
        "summary": (
            f"This is a general-purpose meal plan template related to your {disease} "
            f"screening result ({label}). Please consult a doctor or registered "
            "dietitian for a plan tailored specifically to you."
        ),
        "daily_calorie_target": "Approx. 1800-2200 kcal/day (general guidance only)",
        "days": template_days,
        "shopping_list_highlights": [
            "Leafy greens", "Oats", "Greek yogurt", "Lean protein (chicken/fish/tofu)",
            "Mixed nuts", "Olive oil"
        ],
        "general_notes": (
            "This is a general template, not personalized medical nutrition advice — "
            "please review it with a doctor or registered dietitian before following it."
        ),
    }


def generate_diet_plan(prediction_result: dict, user_data: dict, duration_days: int) -> dict:
    """
    Builds a personalized day-by-day meal plan based on the screening result
    and the user's own submitted form data (age, BMI, glucose, cholesterol,
    etc. — whichever screening it was).

    duration_days: 3, 7, 14, or 30 (validated/clamped by the caller).
    For durations > 7, a 7-day rotating template is generated instead of
    a unique plan for every single day, and the response notes that it
    should be repeated for the full period.
    """
    disease = prediction_result.get("disease", "the condition")
    label = prediction_result.get("label", "")
    risk_level = prediction_result.get("risk_level", "")
    confidence = prediction_result.get("confidence", "")

    plan_days = min(duration_days, 7)
    duration_label = {3: "3 Days", 7: "7 Days", 14: "14 Days", 30: "30 Days"}.get(
        duration_days, f"{duration_days} Days"
    )

    repeat_note = (
        f"\nNote: the user selected a longer duration ({duration_days} days total). "
        f"Design this as a {plan_days}-day repeatable weekly template they can cycle "
        "through for the full period, and mention that in the summary."
        if duration_days > 7 else ""
    )

    prompt = f"""
You are a certified nutrition and dietetics assistant embedded inside a
medical screening web app. A local ML model (NOT you) already produced
this result — do not diagnose or re-predict anything, only build a diet plan.

Disease screened: {disease}
Result: {label}
Risk level: {risk_level}
Model confidence: {confidence}%
Patient's own submitted details (JSON): {json.dumps(user_data)}

Build a personalized {plan_days}-day meal plan appropriate for this
person's risk level and screening details. If this relates to diabetes,
favor low-glycemic-index, balanced-carbohydrate choices. If this relates
to heart disease, favor low-sodium, low-saturated-fat, heart-healthy
choices. Vary the meals across the days for variety, don't repeat the
exact same meal twice.
{repeat_note}

Respond ONLY with valid minified JSON (no markdown, no backticks) matching
exactly this schema:
{{
  "duration_label": "{duration_label}",
  "summary": "2-3 sentence framing of this plan given the result",
  "daily_calorie_target": "short phrase, e.g. approx 1800-2000 kcal/day (general guidance only)",
  "days": [
    {{"day_label": "Day 1", "breakfast": "...", "lunch": "...", "dinner": "...", "snacks": "..."}}
  ],
  "shopping_list_highlights": ["item1","item2","item3","item4","item5","item6"],
  "general_notes": "1-2 sentences of practical advice, including a brief reminder to review with a doctor or registered dietitian"
}}

The "days" array must contain exactly {plan_days} entries.
"""

    try:
        raw_text = _call_gemini(prompt)

        cleaned = raw_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        plan = json.loads(cleaned)
        plan.setdefault("duration_label", duration_label)
        return plan
    except Exception as e:
        print("Gemini Diet Plan Error:", e)
        return _fallback_diet_plan(disease, label, plan_days, duration_label)
def generate_recommendations(prediction_result: dict, user_data: dict) -> dict:
    """
    prediction_result: output dict from heart_predict / diabetes_predict
    user_data: the raw form input the user submitted
    Returns a structured dict of AI-generated health recommendations.
    """
    disease = prediction_result.get("disease", "the condition")
    label = prediction_result.get("label", "")
    risk_level = prediction_result.get("risk_level", "")
    confidence = prediction_result.get("confidence", "")

    prompt = f"""
You are a certified health & nutrition assistant embedded inside a medical
screening web app. A local machine learning model (NOT you) has already
produced the following screening result:

Disease screened: {disease}
Result: {label}
Risk level: {risk_level}
Model confidence: {confidence}%
Patient input data: {json.dumps(user_data)}

Do NOT diagnose or re-predict anything yourself; just build personalized,
supportive, medically-sound lifestyle guidance based on this result.

Respond ONLY with valid minified JSON (no markdown, no backticks) matching
exactly this schema:
{{
  "overview": "2-3 sentence plain-language explanation of this result",
  "foods_to_eat": ["item1","item2","item3","item4","item5"],
  "foods_to_avoid": ["item1","item2","item3","item4","item5"],
  "weekly_diet_plan": "short paragraph describing a sample weekly diet plan",
  "exercise_plan": "short paragraph describing a suitable weekly exercise plan",
  "lifestyle_tips": ["tip1","tip2","tip3","tip4"],
  "water_intake": "one sentence of water intake advice",
  "doctor_consultation": "one sentence advising whether/when to see a doctor"
}}
"""

    try:
        raw_text = _call_gemini(prompt)

        cleaned = raw_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]

        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        cleaned = cleaned.strip()

        return json.loads(cleaned)
    except Exception as e:
        print("Gemini Error:", e)
        return _fallback_recommendations(disease, label)


def ask_question(question: str, context: str = "", history: list = None) -> str:
    """
    Powers the chatbot page using a REAL multi-turn Gemini chat session,
    so the assistant remembers earlier turns instead of restarting cold
    on every single message.

    context: JSON string with the user's last screening result + raw
             form values (so it can answer direct factual questions like
             BMI category using real numbers instead of deflecting).
    history: list of prior turns in Gemini's content format:
             [{"role": "user", "parts": [{"text": "..."}]},
              {"role": "model", "parts": [{"text": "..."}]}, ...]
    """
    system_instruction = f"""
You are Vitalis, a warm, direct AI health assistant chatbot inside the
Smart Healthcare Assistant screening app. Talk like a real, caring
assistant having an ongoing conversation — not like a disclaimer machine.

Rules:
- You do not diagnose diseases yourself (a separate ML model already did
  the screening) — but straightforward factual questions using the
  user's own numbers (e.g. classifying a given BMI as underweight/
  normal/overweight/obese with standard clinical cutoffs) are NOT a
  diagnosis. Answer those directly and plainly.
- Only bring up seeing a doctor when the question is genuinely about
  diagnosis, treatment, medication, or symptoms needing evaluation —
  not as a reflexive add-on to every reply.
- Don't re-explain or re-introduce the user's screening result each
  message. You already told them once; refer back to it briefly only
  when it's relevant to their current question.
- Keep replies conversational and proportionate — usually 2-5 sentences,
  longer only if the question genuinely calls for more detail.
- Remember what's already been said in this conversation. Don't repeat
  yourself.

{f"User's recent screening data (JSON): {context}" if context else "No recent screening on file yet for this user."}
"""

    try:
        chat = client.chats.create(
            model=GEMINI_MODEL,
            history=history or [],
            config={"system_instruction": system_instruction},
        )
        response = chat.send_message(question)
        return response.text.strip()
    except Exception as e:
        print("Gemini Chat Error:", e)
        return (
            "I'm currently unable to reach the AI assistant service "
            "(the Gemini API key may not be configured, or the request "
            "failed). In the meantime, please consult a licensed "
            "healthcare professional for personalized advice, or try "
            "again shortly."
        )