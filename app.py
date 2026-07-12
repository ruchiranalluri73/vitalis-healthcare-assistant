"""
app.py
------
Smart Healthcare Assistant - Flask entry point.

Routes:
  GET  /                -> index.html (landing page)
  GET  /heart            -> heart.html (heart disease form)
  GET  /diabetes          -> diabetes.html (diabetes form)
  POST /predict/heart     -> runs local .pkl prediction + Gemini recs -> result.html
  POST /predict/diabetes  -> runs local .pkl prediction + Gemini recs -> result.html
  GET  /chatbot           -> chatbot.html
  POST /api/chatbot       -> AJAX endpoint, returns JSON {answer: "..."}
  POST /api/diet-plan     -> AJAX endpoint, returns JSON meal plan
  POST /api/find-doctors  -> AJAX endpoint, returns JSON nearby doctors

ML prediction ALWAYS happens locally via the pre-trained .pkl models.
Gemini is only used for personalized recommendations / chatbot answers,
never for disease prediction.
"""

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, jsonify, session
import os
import json

from prediction.heart_predict import predict_heart, FEATURE_ORDER as HEART_FEATURES
from prediction.diabetes_predict import predict_diabetes, FEATURE_ORDER as DIABETES_FEATURES
from chatbot.gemini_api import generate_recommendations, ask_question, generate_diet_plan
from doctor_finder import find_nearby_doctors

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")

MAX_CHAT_TURNS = 12  # keep last N exchanges (user+model pairs) to bound session size


# ---------------------------------------------------------------------
# Static pages
# ---------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/heart")
def heart_form():
    return render_template("heart.html")


@app.route("/diabetes")
def diabetes_form():
    return render_template("diabetes.html")


@app.route("/chatbot")
def chatbot_page():
    return render_template("chatbot.html")


# ---------------------------------------------------------------------
# Prediction routes
# ---------------------------------------------------------------------

@app.route("/predict/heart", methods=["POST"])
def predict_heart_route():
    form_data = request.form.to_dict()

    try:
        result = predict_heart(form_data)
    except ValueError as e:
        return render_template("heart.html", error=str(e), form_data=form_data)
    except Exception as e:
        return render_template("heart.html", error=f"Prediction failed: {e}", form_data=form_data)

    recommendations = generate_recommendations(result, form_data)

    session["last_result"] = json.dumps({
        "disease": result["disease"],
        "label": result["label"],
        "risk_level": result["risk_level"],
        "confidence": result["confidence"],
        "details": form_data
    })
    session["chat_history"] = []

    return render_template("result.html", result=result, rec=recommendations)


@app.route("/predict/diabetes", methods=["POST"])
def predict_diabetes_route():
    form_data = request.form.to_dict()

    try:
        result = predict_diabetes(form_data)
    except ValueError as e:
        return render_template("diabetes.html", error=str(e), form_data=form_data)
    except Exception as e:
        return render_template("diabetes.html", error=f"Prediction failed: {e}", form_data=form_data)

    recommendations = generate_recommendations(result, form_data)

    session["last_result"] = json.dumps({
        "disease": result["disease"],
        "label": result["label"],
        "risk_level": result["risk_level"],
        "confidence": result["confidence"],
        "details": form_data
    })
    session["chat_history"] = []

    return render_template("result.html", result=result, rec=recommendations)


# ---------------------------------------------------------------------
# Chatbot AJAX API
# ---------------------------------------------------------------------

@app.route("/api/chatbot", methods=["POST"])
def api_chatbot():
    data = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()

    if not question:
        return jsonify({"answer": "Please type a question first."}), 400

    context = session.get("last_result", "")
    history = session.get("chat_history", [])

    answer = ask_question(question, context, history)

    history.append({"role": "user", "parts": [{"text": question}]})
    history.append({"role": "model", "parts": [{"text": answer}]})
    session["chat_history"] = history[-(MAX_CHAT_TURNS * 2):]

    return jsonify({"answer": answer})


# ---------------------------------------------------------------------
# Diet plan AJAX API
# ---------------------------------------------------------------------

@app.route("/api/diet-plan", methods=["POST"])
def api_diet_plan():
    data = request.get_json(silent=True) or {}
    duration_raw = data.get("duration", "7")

    last_result_raw = session.get("last_result", "")
    if not last_result_raw:
        return jsonify({"error": "No recent screening found. Please run a screening first."}), 400

    try:
        last_result = json.loads(last_result_raw)
    except (TypeError, ValueError):
        return jsonify({"error": "Screening context could not be read. Please run a screening again."}), 400

    try:
        duration_days = int(duration_raw)
    except (TypeError, ValueError):
        duration_days = 7
    duration_days = max(1, min(duration_days, 30))

    prediction_result = {
        "disease": last_result.get("disease", "the condition"),
        "label": last_result.get("label", ""),
        "risk_level": last_result.get("risk_level", ""),
        "confidence": last_result.get("confidence", ""),
    }
    user_data = last_result.get("details", {})

    plan = generate_diet_plan(prediction_result, user_data, duration_days)
    return jsonify(plan)


# ---------------------------------------------------------------------
# Doctor finder AJAX API
# ---------------------------------------------------------------------

@app.route("/api/find-doctors", methods=["POST"])
def api_find_doctors():
    data = request.get_json(silent=True) or {}
    location = data.get("location", "").strip()

    if not location:
        return jsonify({"error": "Please enter a location."}), 400

    last_result_raw = session.get("last_result", "")
    if not last_result_raw:
        return jsonify({"error": "No recent screening found. Please run a screening first."}), 400

    try:
        last_result = json.loads(last_result_raw)
    except (TypeError, ValueError):
        return jsonify({"error": "Screening context could not be read. Please run a screening again."}), 400

    disease = last_result.get("disease", "")

    try:
        result = find_nearby_doctors(disease, location)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Something went wrong: {e}"}), 500

    return jsonify(result)


# ---------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return render_template("index.html"), 404


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)