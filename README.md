# 🏥 Vitalis — Smart Healthcare Assistant
# 🏥 Vitalis — Smart Healthcare Assistant

🔗 **Live demo:** https://vitalis-healthcare-assistant.onrender.com

A Flask web app that screens for **heart disease** and **diabetes** using
pre-trained scikit-learn models, then uses Google's **Gemini API** to turn
the result into a personalized diet, exercise, and lifestyle plan.
A Flask web app that screens for **heart disease** and **diabetes** using
pre-trained scikit-learn models, then uses Google's **Gemini API** to turn
the result into a personalized diet, exercise, and lifestyle plan.

> **Machine learning prediction is never re-trained or re-derived by this
> app.** It loads your already-trained `heart_model.pkl`, `heart_scaler.pkl`,
> `diabetes_model.pkl`, and `diabetes_scaler.pkl` directly from `models/` and
> uses them exactly as saved. Gemini is used **only** for generating
> recommendations and answering chatbot questions — it never predicts disease.

---

## Project structure

```
SmartHealthcareAssistant/
├── app.py                     # Flask app & routes
├── requirements.txt
├── README.md
├── models/
│   ├── heart_model.pkl
│   ├── heart_scaler.pkl
│   ├── diabetes_model.pkl
│   └── diabetes_scaler.pkl
├── prediction/
│   ├── heart_predict.py       # loads heart_model.pkl + scaler, predicts
│   └── diabetes_predict.py    # loads diabetes_model.pkl + scaler, predicts
├── chatbot/
│   └── gemini_api.py          # Gemini integration (recommendations + chat)
├── templates/
│   ├── base.html              # shared nav/footer/theme shell
│   ├── index.html             # landing page
│   ├── heart.html             # heart disease form
│   ├── diabetes.html          # diabetes form
│   ├── result.html            # prediction + AI recommendations
│   └── chatbot.html           # AI chat page
└── static/
    ├── css/style.css
    └── js/script.js
```

---

## 1. Setup

```bash
cd SmartHealthcareAssistant
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Configure your Gemini API key

Get a key from [Google AI Studio](https://aistudio.google.com/apikey), then:

```bash
export GEMINI_API_KEY="your_key_here"          # macOS/Linux
set GEMINI_API_KEY=your_key_here                # Windows (cmd)
```

Optionally set a specific model (defaults to `gemini-2.0-flash`):

```bash
export GEMINI_MODEL="gemini-2.0-flash"
```

If no key is set, the app still runs end-to-end — `chatbot/gemini_api.py`
falls back to a static recommendation template so predictions and the UI
remain fully functional for local testing/demoing.

## 3. Run the app

```bash
python app.py
```

Visit **http://localhost:5000**.

---

## Feature reference

### Heart disease model — 13 inputs
`age, sex, cp, trestbps, chol, fbs, restecg, thalach, exang, oldpeak, slope, ca, thal`

### Diabetes model — 8 inputs
`pregnancies, glucose, blood_pressure, skin_thickness, insulin, bmi, diabetes_pedigree_function, age`

Both sets of inputs are scaled with their matching `StandardScaler` before
being passed to the classifier, exactly mirroring the preprocessing used
during training.

---

## How a request flows through the app

1. User submits the heart or diabetes form.
2. `app.py` hands the form data to `prediction/heart_predict.py` or
   `prediction/diabetes_predict.py`.
3. That module validates the input, scales it with the matching `.pkl`
   scaler, and runs `.predict()` / `.predict_proba()` on the matching
   `.pkl` model — **entirely locally, no external API call**.
4. The prediction + risk level is passed to
   `chatbot/gemini_api.py::generate_recommendations()`, which asks Gemini
   for a structured JSON recommendation (diet, exercise, lifestyle, etc).
5. `result.html` renders the prediction, a confidence ring, and the
   recommendations.
6. The user can continue asking questions via `chatbot.html`, which calls
   `chatbot/gemini_api.py::ask_question()` through the `/api/chatbot`
   AJAX endpoint.

---

## Notes

- The scikit-learn version is pinned to `1.6.1` in `requirements.txt`
  to match the version used to originally train/save the `.pkl` files, to
  avoid `InconsistentVersionWarning` unpickling issues.
- This tool provides a statistical screening, not a medical diagnosis.
  Always consult a licensed physician.
