import random
import requests
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import db  # local db.py file

app = FastAPI(title="Caretaker AI Core Engine")

# Allow frontend dashboard and external smartphones to connect seamlessly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def compute_ai_risk(hr, spo2, sbp, rr, temp, age):
    """
    AI Rule Engine:
    Evaluates patient vitals and generates a risk score from 0 to 100.
    """
    score = 0

    # SpO2 risk
    if spo2 < 85:
        score += 35
    elif spo2 < 90:
        score += 20
    elif spo2 < 94:
        score += 8

    # Heart rate risk
    if hr > 140 or hr < 40:
        score += 30
    elif hr > 110 or hr < 55:
        score += 15

    # Temperature risk
    if temp > 39:
        score += 20
    elif temp > 38:
        score += 8

    # Blood pressure risk
    if sbp < 90:
        score += 25
    elif sbp < 100:
        score += 10

    # Respiratory rate risk
    if rr > 25:
        score += 10
    elif rr > 20:
        score += 5

    # Age risk
    if age > 70:
        score += 8
    elif age > 60:
        score += 4

    # Small random variation for demo simulation consistency
    score += random.uniform(0, 5)

    return min(100, round(score))


def analyze_and_create_alerts(p, v, time_str):
    """
    Clinical Decision Support pipeline logic:
    Creates alerts when patient vitals enter critical range.
    """
    msgs = []

    if v["spo2"] < 85:
        msgs.append({
            "msg": f"SpO₂ critically low at {v['spo2']}%",
            "actions": ["Monitor oxygen supply immediately", "Notify ICU staff"],
            "level": "critical"
        })

    if v["hr"] > 140:
        msgs.append({
            "msg": f"Tachycardia — HR {v['hr']} bpm",
            "actions": ["12-lead ECG immediately", "Notify cardiologist"],
            "level": "critical"
        })

    if v["sbp"] < 90:
        msgs.append({
            "msg": f"Hypotension — BP {v['sbp']}/{v['dbp']} mmHg",
            "actions": ["IV fluid resuscitation", "Alert ICU immediately"],
            "level": "critical"
        })

    for m in msgs:
        db.push_alert({
            "patient": p["name"],
            "patientId": p["id"],
            "ward": p["ward"],
            "msg": m["msg"],
            "actions": m["actions"],
            "level": m["level"],
            "time": time_str
        })


def generate_llm_advice(patient, vitals, patient_alerts):
    """
    Uses local Ollama LLM llama3.2 to generate medical decision-support advice.
    """
    alert_text = "No major alerts."

    if patient_alerts:
        alert_text = "\n".join([
            f"- {a['msg']} | Actions: {', '.join(a['actions'])}"
            for a in patient_alerts[:3]
        ])

    prompt = f"""
You are CriticalCare AI, a hospital patient monitoring assistant.

Analyze the patient condition and give:
1. Short patient summary
2. Risk explanation
3. Immediate action
4. Nurse/doctor alert message

Patient Details:
Name: {patient['name']}
Patient ID: {patient['id']}
Age: {patient['age']}
Gender: {patient['gender']}
Ward: {patient['ward']}

Current Vitals:
Heart Rate: {vitals['hr']} bpm
SpO2: {vitals['spo2']}%
Blood Pressure: {vitals['sbp']}/{vitals['dbp']} mmHg
Temperature: {vitals['temp']} Celsius
Respiratory Rate: {vitals['rr']} /min
Risk Score: {vitals['risk']}/100
Risk Level: {vitals['level']}

Existing Alerts:
{alert_text}

Important:
Do not give a final diagnosis.
Give only decision-support guidance.
Keep the answer short, clear, and useful for nurses/doctors.
"""

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2",
                "prompt": prompt,
                "stream": False
            },
            timeout=40
        )
        response.raise_for_status()
        result = response.json()
        return result.get("response", "No LLM response generated.")

    except Exception as e:
        return f"""
LLM is not connected.

Fallback Advice:
Patient {patient['name']} is currently marked as {vitals['level'].upper()} with risk score {vitals['risk']}/100.

Immediate Action:
Check abnormal vitals, verify patient condition, and notify medical staff if needed.

Error Details:
{str(e)}
"""


@app.get("/")
def home():
    return {
        "message": "CriticalCare AI Backend is running",
        "update_api": "/api/update",
        "llm_api": "/api/llm/{patient_id}"
    }


@app.get("/api/update")
def execute_system_tick():
    """
    Runs data simulation, AI scoring, alert creation, 
    and logs updates for all patient beds.
    """
    time_str = datetime.now().strftime("%H:%M:%S")

    for p in db.PATIENTS:
        # 70% Stable, 20% Warning, 10% Critical random spread for live telemetry demonstration
        state = random.choices(
            ["stable", "warning", "critical"],
            weights=[70, 20, 10]
        )[0]

        prev = db.current_vitals.get(p["id"])

        if state == "critical":
            hr = random.choice([
                random.randint(35, 39),
                random.randint(142, 155)
            ])
            spo2 = round(random.uniform(79, 84), 1)
            sbp = random.randint(75, 88)
            temp = round(random.uniform(39.1, 40.5), 1)
            rr = random.randint(24, 30)
        else:
            hr = max(
                55,
                min(
                    100,
                    (prev["hr"] + random.randint(-3, 3))
                    if prev else random.randint(65, 85)
                )
            )
            spo2 = max(
                95,
                min(
                    100,
                    (prev["spo2"] + random.uniform(-0.4, 0.4))
                    if prev else random.uniform(97, 99)
                )
            )
            sbp = max(
                100,
                min(
                    130,
                    (prev["sbp"] + random.randint(-3, 3))
                    if prev else random.randint(105, 125)
                )
            )
            temp = max(
                36.3,
                min(
                    37.5,
                    (prev["temp"] + random.uniform(-0.1, 0.1))
                    if prev else random.uniform(36.5, 37.2)
                )
            )
            rr = random.randint(14, 18)

        dbp = max(50, sbp - random.randint(30, 45))
        spo2 = round(spo2, 1)
        temp = round(temp, 1)

        risk = compute_ai_risk(
            hr=hr,
            spo2=spo2,
            sbp=sbp,
            rr=rr,
            temp=temp,
            age=p["age"]
        )

        level = "critical" if risk >= 70 else "warning" if risk >= 40 else "stable"

        vitals_snapshot = {
            "hr": hr,
            "spo2": spo2,
            "sbp": sbp,
            "dbp": dbp,
            "temp": temp,
            "rr": rr,
            "risk": risk,
            "level": level
        }

        db.save_vitals(p["id"], vitals_snapshot, time_str)
        analyze_and_create_alerts(p, vitals_snapshot, time_str)

    return {
        "patients": db.PATIENTS,
        "current_vitals": db.current_vitals,
        "vitals_history": db.vitals_history,
        "alerts": db.alerts_table
    }


@app.get("/api/llm/{patient_id}")
def get_patient_llm_advice(patient_id: str):
    """
    Generates LLM advice for selected patient.
    Frontend calls this API when user requests Decision Support analytics.
    """
    patient = next(
        (p for p in db.PATIENTS if p["id"] == patient_id),
        None
    )

    if not patient:
        return {"error": "Patient not found"}

    vitals = db.current_vitals.get(patient_id)

    if not vitals:
        return {"error": "Vitals not available yet. Wait for one system update."}

    patient_alerts = [
        a for a in db.alerts_table
        if a["patientId"] == patient_id
    ]

    advice = generate_llm_advice(
        patient=patient,
        vitals=vitals,
        patient_alerts=patient_alerts
    )

    return {
        "patientId": patient_id,
        "patient": patient["name"],
        "llm_advice": advice
    }


if __name__ == "__main__":
    import uvicorn
    # Bound to host "0.0.0.0" to open public communication to mobile web links
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )