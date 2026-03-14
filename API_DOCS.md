# ReadmitIQ — API Reference
## Dataset: Diabetes 130-US Hospitals for Years 1999–2008

All field names, types, and allowed values match the UCI Diabetes 130-US dataset exactly.

---

## POST `/predict`

Accepts one patient admission record and returns a 30-day readmission risk prediction.

### Headers
| Header         | Value              |
|----------------|--------------------|
| Content-Type   | application/json   |
| Accept         | application/json   |

---

## Request Body

```json
{
  "patient_id":                 "PT-4821",
  "race":                       "Caucasian",
  "gender":                     "Male",
  "age":                        68,
  "admission_type_id":          1,
  "discharge_disposition_id":   3,
  "admission_source_id":        7,
  "time_in_hospital":           7,
  "num_lab_procedures":         52,
  "num_procedures":             2,
  "num_medications":            14,
  "number_outpatient":          0,
  "number_emergency":           1,
  "number_inpatient":           3,
  "number_diagnoses":           9,
  "diag_1":                     "428",
  "max_glu_serum":              ">200",
  "A1Cresult":                  ">8",
  "metformin":                  "Steady",
  "insulin":                    "Up",
  "change":                     "Ch",
  "diabetesMed":                "Yes"
}
```

---

## Field Reference (Input)

### Demographics
| Field    | Type   | Req | Values / Notes                                                   | Dataset Column |
|----------|--------|-----|------------------------------------------------------------------|----------------|
| patient_id | string | ✅ | Any unique ID (e.g. `"PT-4821"`)                               | `encounter_id` proxy |
| race     | string | ✅ | `"Caucasian"` `"AfricanAmerican"` `"Hispanic"` `"Asian"` `"Other"` | `race` |
| gender   | string | ✅ | `"Male"` or `"Female"`                                         | `gender` |
| age      | integer | ✅ | 1–120 (dataset uses 10-year brackets: [0-10), [10-20), … [90-100)) | `age` |

### Admission
| Field                      | Type    | Req | Values / Notes                                                  | Dataset Column |
|----------------------------|---------|-----|-----------------------------------------------------------------|----------------|
| admission_type_id          | integer | ✅  | 1=Emergency, 2=Urgent, 3=Elective, 4=Newborn, 5=Not Available  | `admission_type_id` |
| discharge_disposition_id   | integer | ✅  | 1=Home, 3=SNF, 6=Home Health Agency, 11=Expired, 18=Not Available, 25=Still in hospital | `discharge_disposition_id` |
| admission_source_id        | integer | ✅  | 1=Physician Referral, 2=Clinic Referral, 4=Transfer from Hospital, 6=Transfer from SNF, 7=Emergency Room | `admission_source_id` |
| diag_1                     | string  | ✅  | ICD-9 code of primary diagnosis (e.g. `"428"`, `"250"`, `"486"`) | `diag_1` |

### Stay Details
| Field                  | Type    | Req | Range  | Notes                                      | Dataset Column |
|------------------------|---------|-----|--------|--------------------------------------------|----------------|
| time_in_hospital       | integer | ✅  | 1–14   | Days of stay                               | `time_in_hospital` |
| num_lab_procedures     | integer | ✅  | 0–132  | Number of lab tests ordered                | `num_lab_procedures` |
| num_procedures         | integer | ✅  | 0–6    | Number of non-lab procedures               | `num_procedures` |
| num_medications        | integer | ✅  | 0–81   | Distinct medications administered          | `num_medications` |
| number_outpatient      | integer | ✅  | 0–42   | Outpatient visits in prior year            | `number_outpatient` |
| number_emergency       | integer | ✅  | 0–76   | Emergency visits in prior year             | `number_emergency` |
| number_inpatient       | integer | ✅  | 0–21   | Inpatient stays in prior year              | `number_inpatient` |
| number_diagnoses       | integer | ✅  | 1–16   | Total diagnoses recorded on admission      | `number_diagnoses` |

### Diabetes & Lab Results
| Field          | Type   | Req | Allowed Values                                | Notes                                 | Dataset Column |
|----------------|--------|-----|-----------------------------------------------|---------------------------------------|----------------|
| max_glu_serum  | string | ❌  | `"None"` `">200"` `">300"` `"Norm"`          | Max serum glucose measurement         | `max_glu_serum` |
| A1Cresult      | string | ❌  | `"None"` `">7"` `">8"` `"Norm"`             | HbA1c test result                     | `A1Cresult` |
| metformin      | string | ❌  | `"No"` `"Steady"` `"Up"` `"Down"`           | Metformin dosage change               | `metformin` |
| insulin        | string | ❌  | `"No"` `"Steady"` `"Up"` `"Down"`           | Insulin dosage change                 | `insulin` |
| change         | string | ❌  | `"Ch"` (changed) or `"No"`                  | Any medication change during stay     | `change` |
| diabetesMed    | string | ❌  | `"Yes"` or `"No"`                            | Any diabetes medication prescribed    | `diabetesMed` |

---

## Response Body

```json
{
  "patient_id":           "PT-4821",
  "readmission_risk_pct": 72,
  "risk_tier":            "high",
  "will_readmit":         true,
  "confidence":           0.87,
  "top_features":         ["number_inpatient", "time_in_hospital"],
  "shap_values": {
    "number_inpatient":         0.27,
    "time_in_hospital":         0.18,
    "discharge_disposition_id": 0.18,
    "num_medications":          0.11,
    "A1Cresult":                0.13,
    "insulin":                  0.12
  },
  "inference_ms": 94,
  "timestamp":    "2025-03-14T08:42:11.023Z"
}
```

### Response Fields
| Field                  | Type    | Description |
|------------------------|---------|-------------|
| patient_id             | string  | Echoed from request |
| readmission_risk_pct   | integer | Predicted 30-day readmission probability (0–100) |
| risk_tier              | string  | `"high"` ≥65%, `"medium"` 40–64%, `"low"` <40% |
| will_readmit           | boolean | Binary: true if risk_pct ≥ 50 |
| confidence             | float   | Model confidence (0.0–1.0) |
| top_features           | array   | Top 2 feature names by SHAP magnitude |
| shap_values            | object  | Feature → SHAP contribution (for the bar chart) |
| inference_ms           | integer | Model inference time in ms |
| timestamp              | string  | UTC ISO 8601 |

---

## Error Responses
| Status | Meaning               | Body                                                        |
|--------|-----------------------|-------------------------------------------------------------|
| 422    | Validation error      | `{"detail": [{"loc": ["body", "field"], "msg": "..."}]}` |
| 500    | Model inference error | `{"detail": "Model inference failed"}`                     |
| 503    | Service unavailable   | `{"detail": "Model not loaded"}`                           |

---

## Form Field → API Field Mapping (Dashboard)

| Dashboard Label            | API Field                  | Type    | Notes |
|----------------------------|----------------------------|---------|-------|
| Patient name               | *(UI only)*                | —       | Not sent to model |
| Age                        | `age`                      | integer | |
| Gender                     | `gender`                   | string  | Full word: "Male" / "Female" |
| Race                       | `race`                     | string  | |
| Primary diagnosis (ICD-9)  | `diag_1`                   | string  | ICD-9 code string |
| Admission type             | `admission_type_id`        | integer | |
| Admission source           | `admission_source_id`      | integer | |
| Discharge disposition      | `discharge_disposition_id` | integer | |
| Time in hospital (days)    | `time_in_hospital`         | integer | |
| Num lab procedures         | `num_lab_procedures`       | integer | |
| Num procedures             | `num_procedures`           | integer | |
| Num medications            | `num_medications`          | integer | |
| Prior outpatient visits    | `number_outpatient`        | integer | |
| Prior emergency visits     | `number_emergency`         | integer | |
| Prior inpatient stays      | `number_inpatient`         | integer | |
| Number of diagnoses        | `number_diagnoses`         | integer | |
| Max glucose serum          | `max_glu_serum`            | string  | |
| HbA1c result               | `A1Cresult`                | string  | |
| Insulin                    | `insulin`                  | string  | |
| Metformin                  | `metformin`                | string  | |
| Medication changed?        | `change`                   | string  | "Ch" or "No" |
| Diabetes medication?       | `diabetesMed`              | string  | "Yes" or "No" |

---

## FastAPI Server Skeleton

```python
# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import joblib, shap, time, numpy as np
from datetime import datetime, timezone

app = FastAPI(title="ReadmitIQ — Diabetes 130-US Readmission Predictor")

app.add_middleware(CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_methods=["POST"], allow_headers=["*"])

model     = joblib.load("readmission_model.pkl")   # sklearn / XGBoost
explainer = shap.TreeExplainer(model)
FEATURES  = [...]  # your feature list in training order


class AdmissionInput(BaseModel):
    patient_id: str
    race: str
    gender: str
    age: int
    admission_type_id: int
    discharge_disposition_id: int
    admission_source_id: int
    time_in_hospital: int
    num_lab_procedures: int
    num_procedures: int
    num_medications: int
    number_outpatient: int
    number_emergency: int
    number_inpatient: int
    number_diagnoses: int
    diag_1: str
    max_glu_serum: Optional[str] = "None"
    A1Cresult: Optional[str] = "None"
    metformin: Optional[str] = "No"
    insulin: Optional[str] = "No"
    change: Optional[str] = "No"
    diabetesMed: Optional[str] = "No"


@app.post("/predict")
def predict(p: AdmissionInput):
    t0 = time.time()
    X  = preprocess(p, FEATURES)          # your feature engineering
    prob = float(model.predict_proba(X)[0][1])
    pct  = round(prob * 100)
    tier = "high" if pct >= 65 else "medium" if pct >= 40 else "low"

    sv   = explainer.shap_values(X)[0]    # SHAP values
    shap_dict = {FEATURES[i]: round(float(sv[i]), 4) for i in range(len(FEATURES))}
    top2 = sorted(shap_dict, key=shap_dict.get, reverse=True)[:2]

    return {
        "patient_id":           p.patient_id,
        "readmission_risk_pct": pct,
        "risk_tier":            tier,
        "will_readmit":         pct >= 50,
        "confidence":           round(max(prob, 1 - prob), 2),
        "top_features":         top2,
        "shap_values":          shap_dict,
        "inference_ms":         round((time.time() - t0) * 1000),
        "timestamp":            datetime.now(timezone.utc).isoformat(),
    }
```

---

## Running the Stack

```bash
# Terminal 1 — FastAPI (port 8000)
pip install fastapi uvicorn scikit-learn xgboost shap
uvicorn main:app --reload --port 8000
# Swagger UI → http://localhost:8000/docs

# Terminal 2 — Streamlit (port 8501)
pip install streamlit
streamlit run readmitiq_app.py
# Dashboard  → http://localhost:8501
```
