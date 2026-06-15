# db.py
import time

# Static Patient Registry Table
PATIENTS = [
    { 'id':'P-001', 'name':'Arjun Mehta', 'age':67, 'ward':'ICU-A', 'gender':'M' },
    { 'id':'P-002', 'name':'Priya Sharma', 'age':45, 'ward':'ICU-B', 'gender':'F' },
    { 'id':'P-003', 'name':'Ramesh Iyer', 'age':72, 'ward':'Ward 3', 'gender':'M' },
    { 'id':'P-004', 'name':'Sunita Rao', 'age':38, 'ward':'Ward 2', 'gender':'F' },
    { 'id':'P-005', 'name':'Kavya Nair', 'age':55, 'ward':'ICU-A', 'gender':'F' },
    { 'id':'P-006', 'name':'Deepak Kumar', 'age':80, 'ward':'Ward 4', 'gender':'M' },
    { 'id':'P-007', 'name':'Anita Patel', 'age':29, 'ward':'Ward 1', 'gender':'F' },
    { 'id':'P-008', 'name':'Vijay Singh', 'age':63, 'ward':'ICU-C', 'gender':'M' },
]

# In-Memory State Containers (Emulating Database Tables)
current_vitals = {}
vitals_history = {p['id']: {'hr': [], 'spo2': [], 'temp': [], 'labels': []} for p in PATIENTS}
alerts_table = []

def save_vitals(patient_id, vitals_snapshot, time_str):
    """Commits fresh telemetry into database history frames."""
    current_vitals[patient_id] = vitals_snapshot
    hist = vitals_history[patient_id]
    
    hist['labels'].append(time_str)
    hist['hr'].append(vitals_snapshot['hr'])
    hist['spo2'].append(vitals_snapshot['spo2'])
    hist['temp'].append(vitals_snapshot['temp'])
    
    # Enforce rolling index threshold limits to preserve memory (keep last 20 ticks)
    if len(hist['labels']) > 20:
        hist['labels'].pop(0)
        hist['hr'].pop(0)
        hist['spo2'].pop(0)
        hist['temp'].pop(0)

def push_alert(alert_object):
    """Inserts a generated critical warning notification into the alerts log."""
    alerts_table.insert(0, alert_object)
    if len(alerts_table) > 50:
        alerts_table.pop()