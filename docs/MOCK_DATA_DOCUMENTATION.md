# C.O.R.E. Mock Data - Complete Documentation

## 📦 Files Created

All files are ready to be placed in your `mock_db/` folder:

1. ✅ **pathology_db.sqlite** - SQLite database with breast cancer pathology
2. ✅ **radiology_scans.csv** - Imaging reports with signed/unsigned status
3. ✅ **clinical_notes.json** - Comprehensive EHR data
4. ✅ **genomics_data.json** - Mutation profiles and genomic test results
5. ✅ **contraindication_rules.json** - Drug safety rules and organ function requirements
6. ✅ **mdt_roster_2025-11-18.json** - Patient list for November 18, 2025 MDT meeting

---

## 🎯 Three Main Test Cases

### **Patient 123: "Perfect Case" - Autonomous Reasoning**

**Scenario:** Everything works smoothly, demonstrates clean agent workflow

**Clinical Profile:**
- 58yo postmenopausal female
- ER+/PR+/HER2- Invasive ductal carcinoma, Grade 2
- Post-lumpectomy, 2/15 nodes positive (pT2N1a)
- ECOG 0 (fully active)
- Comorbidities: Well-controlled diabetes, hypertension

**Data Completeness:**
- ✅ Pathology: Signed resection report (2023-11-10) + older biopsy
  - **Agent challenge:** Must select most recent resection over biopsy
- ✅ Radiology: Signed CT scan (2023-11-08)
- ✅ Clinical notes: Complete with labs, ECOG, medications
- ✅ Genomics: FoundationOne CDx with PIK3CA H1047R mutation + TP53 mutation

**Expected Agent Behavior:**
- CaseAgent autonomously requests all data
- PathologyAgent returns 2 reports; CaseAgent uses LLM reasoning to select resection
- GenomicsIntelligenceAgent analyzes PIK3CA mutation:
  - Flags as actionable (Tier 1)
  - Matches to alpelisib (FDA-approved for PIK3CA-mutated HR+/HER2- breast cancer)
  - Searches ClinicalTrials.gov for PI3K inhibitor trials
  - Cites SOLAR-1 trial (PMID: 31091374)
- Final status: **100% READY**

---

### **Patient 456: "Conflict Resolution Case"**

**Scenario:** Multiple data sources, agent must prioritize and resolve conflicts

**Clinical Profile:**
- 52yo perimenopausal female
- ER+/PR-/HER2+ Invasive lobular carcinoma, Grade 2
- Post-mastectomy, 4/18 nodes positive (pT2N2a)
- ECOG 1 (restricted in strenuous activity)
- Comorbidities: Hypothyroidism, anxiety
- LVEF 62% (cleared for trastuzumab)

**Data Completeness:**
- ✅ Pathology: 2 reports (biopsy showing HER2 equivocal, resection confirming HER2 IHC 3+)
  - **Agent challenge:** Must select final resection report with definitive HER2 status
- ✅ Radiology: 2 scans (initial mammogram, staging CT)
  - **Agent challenge:** Must select most recent/relevant staging CT
- ✅ Clinical notes: Complete with cardiac function (LVEF important for trastuzumab)
- ✅ Genomics: ERBB2 amplification + ESR1 Y537S mutation

**Expected Agent Behavior:**
- CaseAgent receives multiple reports from each specialist agent
- Uses LLM reasoning to:
  - Prioritize resection pathology (has final HER2 status)
  - Select staging CT over diagnostic mammogram
  - Note ESR1 mutation for endocrine therapy planning
- GenomicsIntelligenceAgent:
  - Confirms HER2 amplification (ERBB2)
  - Flags trastuzumab/pertuzumab eligibility
  - Notes ESR1 mutation (endocrine resistance marker)
- SafetyAgent checks cardiac function → LVEF 62% ✅ (trastuzumab safe)
- Final status: **100% READY** (after conflict resolution)

---

### **Patient 789: "Blocker Detection Case"**

**Scenario:** Incomplete data and contraindications, demonstrates human-in-the-loop escalation

**Clinical Profile:**
- 45yo premenopausal female
- Triple-negative breast cancer (TNBC), Grade 3
- Post-lumpectomy, micrometastasis in 1/12 nodes (pT2N1mi)
- ECOG 1 (some fatigue)
- **CRITICAL:** Chronic kidney disease stage 3a (eGFR 48 ml/min, Cr 1.4)
- Comorbidities: Obesity (BMI 31.2), vitamin D deficiency
- Social: Single mother of 2, limited support

**Data Completeness:**
- ✅ Pathology: Signed report (triple-negative confirmed)
- ⚠️ Radiology: **BLOCKER DETECTED** - MRI report is DRAFT/UNSIGNED (2023-11-12)
  - Older signed CT available (2023-11-02)
  - **Agent challenge:** Must flag unsigned report as blocker
- ✅ Clinical notes: Complete with **renal impairment** flagged
- ❌ Genomics: **NOT_FOUND** - testing not yet ordered
  - **Agent challenge:** Must flag missing genomics for TNBC case

**Expected Agent Behavior:**
- CaseAgent requests data from all specialist agents
- RadiologyAgent returns 2 scans:
  - Newer MRI (DRAFT, unsigned by Dr. Johnson)
  - Older CT (SIGNED)
- CaseAgent uses LLM reasoning:
  - Recognizes MRI is more recent but unsigned
  - Flags as blocker: "Radiology_Report_Status: INCOMPLETE_DRAFT"
  - Cannot mark case as 100% ready
- GenomicsAgent returns NOT_FOUND → flags as missing critical data for TNBC
- SafetyAgent reviews clinical notes:
  - **CONTRAINDICATION DETECTED:** eGFR 48 ml/min
  - Flags: "Renal impairment - avoid nephrotoxic agents (cisplatin contraindicated, carboplatin requires dose adjustment)"
- Final status: **80% READY - BLOCKED**
- Blockers escalated to CoordinatorAgent:
  1. Unsigned radiology report (Action: Notify Dr. Johnson)
  2. Missing genomics (Action: Order FoundationOne CDx urgently)
  3. Renal impairment (Action: Alert oncologist for dose adjustments)

---

## 📊 Data File Details

### 1. pathology_db.sqlite

**Schema:**
```sql
CREATE TABLE pathology_reports (
    report_id TEXT PRIMARY KEY,
    patient_id TEXT,
    report_date DATE,
    report_type TEXT,  -- 'biopsy' or 'resection'
    diagnosis TEXT,
    histological_type TEXT,
    grade INTEGER,
    tumor_size_mm REAL,
    er_status TEXT,
    pr_status TEXT,
    her2_status TEXT,
    ki67_percentage INTEGER,
    nodes_positive INTEGER,
    nodes_examined INTEGER,
    margins TEXT,
    signed_by TEXT,
    signed_date DATE,
    full_report_text TEXT
)
```

**Contents:**
- Patient 123: 2 reports (biopsy + resection)
- Patient 456: 2 reports (biopsy with HER2 equivocal + resection with HER2 3+)
- Patient 789: 1 report (resection with TNBC)
- Patient 234: 1 report (extra patient for robustness)

---

### 2. radiology_scans.csv

**Columns:**
- scan_id, patient_id, scan_date, modality, body_part
- report_status (SIGNED or DRAFT) ⚠️
- radiologist, report_date, findings_summary, recist_measurements

**Key Features:**
- Patient 123: 1 signed CT
- Patient 456: 2 scans (mammogram + CT) - conflict resolution test
- Patient 789: 2 scans including **1 DRAFT MRI** (blocker) + 1 older signed CT
- Patient 234: 1 signed CT

---

### 3. clinical_notes.json

**Structure per patient:**
```json
{
  "demographics": { age, sex, menopausal_status, ethnicity },
  "diagnosis": { primary, stage, date_diagnosed },
  "comorbidities": [...],
  "current_medications": [...],
  "allergies": [...],
  "performance_status": { ecog, assessment_date, notes },
  "recent_labs": { hemoglobin, creatinine, eGFR, LFTs, etc. },
  "vital_signs": { BP, HR, weight, BMI },
  "oncologist": "name",
  "oncologist_notes": "detailed clinical narrative"
}
```

**Key Features:**
- Patient 123: Well-controlled comorbidities, ECOG 0
- Patient 456: Normal cardiac function (LVEF 62%) - important for trastuzumab
- Patient 789: **Renal impairment (eGFR 48)** - contraindication flag

---

### 4. genomics_data.json

**Patient 123:**
- PIK3CA H1047R (Tier 1 actionable)
- TP53 R273H
- TMB-Low (5.2 mut/Mb)
- MSS, PD-L1 10%

**Patient 456:**
- ERBB2 amplification (HER2+)
- ESR1 Y537S mutation
- CCND1 amplification
- TMB-Low (3.1 mut/Mb)

**Patient 789:**
- Status: "NOT_FOUND"
- Reason: "Genomic testing not ordered"
- Recommendation: Order FoundationOne CDx

**Patient 234:**
- Oncotype DX score: 18 (intermediate risk)
- Limited NGS profiling

---

### 5. contraindication_rules.json

**Drug Categories:**
- Anthracyclines (Doxorubicin) - cardiac contraindications
- Taxanes (Paclitaxel) - hepatic/neuropathy contraindications
- HER2-targeted (Trastuzumab, Pertuzumab) - cardiac requirements (LVEF ≥50%)
- PI3K inhibitor (Alpelisib) - requires PIK3CA mutation, diabetes contraindication
- Platinum (Carboplatin) - renal dosing adjustments
- CDK4/6 inhibitor (Palbociclib) - hematologic monitoring
- PARP inhibitor (Olaparib) - requires BRCA mutation

**Special Population Rules:**
- Renal impairment categories (mild/moderate/severe)
- Hepatic impairment guidelines
- Cardiac disease contraindications

---

### 6. mdt_roster_2025-11-18.json

**Meeting Details:**
- Date: November 18, 2025 at 14:00
- Location: Conference Room A
- Chair: Dr. Sarah Chen
- 10 attendees (oncologists, pathologists, radiologists, surgeon, etc.)

**Patient List:**
- Patient 123 (Case 1) - 20 min discussion, medium complexity
- Patient 456 (Case 2) - 25 min discussion, medium complexity
- Patient 789 (Case 3) - 30 min discussion, **HIGH complexity with alerts**

**Alerts for Patient 789:**
- "URGENT: Radiology MRI report unsigned as of 2023-11-15"
- "WARNING: Renal impairment (eGFR 48) - avoid nephrotoxic agents"
- "NOTE: Genomic profiling not yet completed - order urgently"

---

## 🎯 Agent Testing Scenarios

### **Scenario 1: Smooth Workflow (Patient 123)**
```
CoordinatorAgent → spawns CaseAgent_123
CaseAgent_123 → broadcasts data request
PathologyAgent → returns 2 reports
CaseAgent_123 → LLM reasons: "Resection is most recent and complete"
RadiologyAgent → returns signed CT
EHRAgent → returns complete notes
GenomicsAgent → analyzes PIK3CA mutation → searches ClinicalTrials.gov → cites SOLAR-1
CaseAgent_123 → updates checklist: ALL_FOUND_AND_VALIDATED
CoordinatorAgent → dashboard shows: Patient 123 [100% READY ✅]
```

### **Scenario 2: Conflict Resolution (Patient 456)**
```
CaseAgent_456 → broadcasts data request
PathologyAgent → returns 2 reports (biopsy HER2 equivocal, resection HER2 3+)
CaseAgent_456 → LLM reasons: "Resection has definitive HER2 status, use that"
RadiologyAgent → returns 2 scans (mammogram, staging CT)
CaseAgent_456 → LLM reasons: "Staging CT is more comprehensive, use that"
GenomicsAgent → confirms ERBB2 amplification → matches trastuzumab/pertuzumab
SafetyAgent → checks LVEF: 62% ✅ → cleared for anti-HER2 therapy
CaseAgent_456 → ALL_FOUND_AND_VALIDATED (after resolving conflicts)
CoordinatorAgent → dashboard shows: Patient 456 [100% READY ✅]
```

### **Scenario 3: Blocker Detection & Escalation (Patient 789)**
```
CaseAgent_789 → broadcasts data request
PathologyAgent → returns signed TNBC report ✅
RadiologyAgent → returns 2 scans:
  - MRI 2023-11-12: report_status=DRAFT ⚠️
  - CT 2023-11-02: report_status=SIGNED ✅
CaseAgent_789 → LLM reasons: "MRI is more recent but UNSIGNED - this is a blocker"
CaseAgent_789 → updates: Radiology_Report_Status: INCOMPLETE_DRAFT
GenomicsAgent → returns NOT_FOUND ❌
CaseAgent_789 → flags: "Genomics_Status: NOT_FOUND - urgent for TNBC"
EHRAgent → returns clinical notes
SafetyAgent → analyzes labs:
  - eGFR 48 ml/min → flags CONTRAINDICATION
  - "Avoid cisplatin, dose-reduce carboplatin"
CaseAgent_789 → CANNOT complete goal (has blockers)
CaseAgent_789 → escalates to CoordinatorAgent:
  BLOCKER 1: Radiology report unsigned
  BLOCKER 2: Genomics data missing
  BLOCKER 3: Renal impairment requires dose adjustment
CoordinatorAgent → dashboard shows: Patient 789 [80% READY ⚠️ BLOCKED]
CoordinatorAgent → generates action items:
  - Notify Dr. Johnson to sign MRI report
  - Order FoundationOne CDx for Patient 789 urgently
  - Alert Dr. Chen about renal dosing requirements
```

---

## 📋 Next Steps

1. **Move files to your project:**
   ```bash
   mkdir -p mock_db
   mv *.sqlite mock_db/
   mv *.csv mock_db/
   mv *.json mock_db/
   ```

2. **Test data access:**
   ```python
   # Test SQLite
   import sqlite3
   conn = sqlite3.connect('mock_db/pathology_db.sqlite')
   cursor = conn.cursor()
   cursor.execute("SELECT * FROM pathology_reports WHERE patient_id='123'")
   print(cursor.fetchall())
   
   # Test CSV
   import pandas as pd
   df = pd.read_csv('mock_db/radiology_scans.csv')
   print(df[df['patient_id'] == '789'])
   
   # Test JSON
   import json
   with open('mock_db/clinical_notes.json') as f:
       data = json.load(f)
       print(data['patient_123']['performance_status'])
   ```

3. **Build your agents** to query this data!

---

## 🏆 Why This Mock Data is Excellent for Your Capstone

✅ **Realistic** - Based on actual breast cancer clinical scenarios  
✅ **Demonstrates all agent capabilities** - reasoning, conflict resolution, blocker detection  
✅ **Shows LLM intelligence** - agents must make clinical decisions, not just retrieve data  
✅ **Highlights your differentiator** - GenomicsIntelligenceAgent with actionable mutations  
✅ **Tests edge cases** - unsigned reports, missing data, contraindications  
✅ **Clinically accurate** - reflects real MDT preparation challenges  
✅ **Impressive to judges** - shows deep healthcare domain knowledge  

---

**Your mock data is production-ready! 🚀**
