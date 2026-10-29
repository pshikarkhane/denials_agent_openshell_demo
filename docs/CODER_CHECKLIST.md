# Coder checklist

For a coding / revenue-cycle professional. **Every item was chosen by an AI assistant from general knowledge and has not been verified.** Code descriptions are paraphrases, not AMA/CMS text. All data is synthetic. Please mark each line OK or wrong and say what the correct code would be.

This list contains only what is **in use in the generated cases now**. Generated from `data/` by `scripts/make_coder_checklist.py`.

## 1. CPT + ICD-10 pairings meant to be valid

- 27447 (Total knee arthroplasty) + M17.11 (Primary OA, right knee)  | categories [3, 4, 11]  | [ ] OK  [ ] wrong  Notes: 
- 29881 (Knee arthroscopy with meniscectomy) + M23.221 (Old meniscus tear, post horn medial, right knee)  | categories [3, 4]  | [ ] OK  [ ] wrong  Notes: 
- 29881 (Knee arthroscopy with meniscectomy) + M23.222 (Old meniscus tear, post horn medial, left knee)  | categories [4]  | [ ] OK  [ ] wrong  Notes: 
- 63030 (Lumbar laminotomy/discectomy) + M51.26 (Other disc displacement, lumbar)  | categories [4]  | [ ] OK  [ ] wrong  Notes: 
- 72148 (MRI lumbar spine without contrast) + M51.16 (Disc disorder w/ radiculopathy, lumbar)  | categories [1, 2]  | [ ] OK  [ ] wrong  Notes: 
- 72148 (MRI lumbar spine without contrast) + M51.17 (Disc disorder w/ radiculopathy, lumbosacral)  | categories [11]  | [ ] OK  [ ] wrong  Notes: 
- 72148 (MRI lumbar spine without contrast) + M51.26 (Other disc displacement, lumbar)  | categories [1, 2]  | [ ] OK  [ ] wrong  Notes: 
- 72148 (MRI lumbar spine without contrast) + M54.16 (Radiculopathy, lumbar)  | categories [1, 2]  | [ ] OK  [ ] wrong  Notes: 
- 72148 (MRI lumbar spine without contrast) + M54.17 (Radiculopathy, lumbosacral)  | categories [2]  | [ ] OK  [ ] wrong  Notes: 
- 73721 (MRI lower-extremity joint without contrast) + M23.221 (Old meniscus tear, post horn medial, right knee)  | categories [6]  | [ ] OK  [ ] wrong  Notes: 
- 73721 (MRI lower-extremity joint without contrast) + M25.561 (Pain in right knee)  | categories [6, 10]  | [ ] OK  [ ] wrong  Notes: 
- 73721 (MRI lower-extremity joint without contrast) + M25.562 (Pain in left knee)  | categories [5]  | [ ] OK  [ ] wrong  Notes: 
- 85025 (Complete blood count with differential) + D64.9 (Anemia, unspecified)  | categories [7]  | [ ] OK  [ ] wrong  Notes: 
- 93000 (ECG with interpretation) + I10 (Essential hypertension)  | categories [5, 6, 11]  | [ ] OK  [ ] wrong  Notes: 
- 93000 (ECG with interpretation) + R07.9 (Chest pain, unspecified)  | categories [5]  | [ ] OK  [ ] wrong  Notes: 
- 97110 (Therapeutic exercise) + M25.511 (Pain in right shoulder)  | categories [12]  | [ ] OK  [ ] wrong  Notes: 
- 97110 (Therapeutic exercise) + M25.561 (Pain in right knee)  | categories [10]  | [ ] OK  [ ] wrong  Notes: 
- 97110 (Therapeutic exercise) + M25.562 (Pain in left knee)  | categories [8]  | [ ] OK  [ ] wrong  Notes: 
- 97110 (Therapeutic exercise) + M54.50 (Low back pain, unspecified)  | categories [10]  | [ ] OK  [ ] wrong  Notes: 
- 97112 (Neuromuscular re-education) + M54.16 (Radiculopathy, lumbar)  | categories [12]  | [ ] OK  [ ] wrong  Notes: 
- 97112 (Neuromuscular re-education) + M54.50 (Low back pain, unspecified)  | categories [12]  | [ ] OK  [ ] wrong  Notes: 
- 97140 (Manual therapy) + M25.561 (Pain in right knee)  | categories [9]  | [ ] OK  [ ] wrong  Notes: 
- 97140 (Manual therapy) + M51.16 (Disc disorder w/ radiculopathy, lumbar)  | categories [9]  | [ ] OK  [ ] wrong  Notes: 
- 97140 (Manual therapy) + M54.50 (Low back pain, unspecified)  | categories [9]  | [ ] OK  [ ] wrong  Notes: 
- 97530 (Therapeutic activities) + M25.561 (Pain in right knee)  | categories [12]  | [ ] OK  [ ] wrong  Notes: 
- 97530 (Therapeutic activities) + M62.81 (Muscle weakness)  | categories [12]  | [ ] OK  [ ] wrong  Notes: 
- 99213 (Established patient visit, low) + E11.9 (Type 2 diabetes without complications)  | categories [10]  | [ ] OK  [ ] wrong  Notes: 
- 99213 (Established patient visit, low) + E78.5 (Hyperlipidemia)  | categories [8]  | [ ] OK  [ ] wrong  Notes: 
- 99213 (Established patient visit, low) + I10 (Essential hypertension)  | categories [5, 6, 8]  | [ ] OK  [ ] wrong  Notes: 
- 99213 (Established patient visit, low) + J02.9 (Acute pharyngitis)  | categories [6, 7]  | [ ] OK  [ ] wrong  Notes: 
- 99213 (Established patient visit, low) + J06.9 (Acute upper respiratory infection)  | categories [7, 8]  | [ ] OK  [ ] wrong  Notes: 
- 99213 (Established patient visit, low) + M54.50 (Low back pain, unspecified)  | categories [8]  | [ ] OK  [ ] wrong  Notes: 

Categories 1-2 carry exactly one diagnosis per claim (no Excludes1 pairs). Please confirm that no claim in this dataset reports M54.1x together with M51.1x.

## 2. Pairings that are deliberately WRONG (category 11, CO-11); the corrected diagnosis is in section 1

- 27447 (Total knee arthroplasty) billed with J02.9 (Acute pharyngitis): is it a clear mismatch that a payer edit would deny?  | [ ] OK  [ ] wrong  Notes: 
- 27447 (Total knee arthroplasty) billed with J06.9 (Acute upper respiratory infection): is it a clear mismatch that a payer edit would deny?  | [ ] OK  [ ] wrong  Notes: 
- 72148 (MRI lumbar spine without contrast) billed with D64.9 (Anemia, unspecified): is it a clear mismatch that a payer edit would deny?  | [ ] OK  [ ] wrong  Notes: 
- 93000 (ECG with interpretation) billed with D64.9 (Anemia, unspecified): is it a clear mismatch that a payer edit would deny?  | [ ] OK  [ ] wrong  Notes: 
- 93000 (ECG with interpretation) billed with E78.5 (Hyperlipidemia): is it a clear mismatch that a payer edit would deny?  | [ ] OK  [ ] wrong  Notes: 

## 3. CARC / RARC pairings in use

RARCs were **omitted** (none shown on the remit) for CO-197, CO-4, CO-18 and CO-16 until you recommend one. If you give a RARC for these, say whether it appears with the scenario shown.

- CO-11 (The diagnosis is inconsistent with the procedure.) with RARC M76  | scenario: Diagnosis inconsistent with procedure  | [ ] OK  [ ] wrong  Notes: 
- CO-151 (Payment adjusted because the information submitted does not support this many services or this frequency.) with RARC N640  | scenario: Frequency / visit-limit exceeded  | [ ] OK  [ ] wrong  Notes: 
- CO-16 (The claim lacks information needed for adjudication.) with RARC none  | scenario: Missing/invalid information or modifier  | [ ] OK  [ ] wrong  Notes: 
- CO-18 (Exact duplicate of a claim/service already adjudicated.) with RARC none  | scenario: Duplicate claim  | [ ] OK  [ ] wrong  Notes: 
- CO-197 (Precertification/authorization/notification was absent.) with RARC none  | scenario: No prior auth, retro-auth available; No prior auth, not retro-eligible  | [ ] OK  [ ] wrong  Notes: 
- CO-29 (The time limit for filing has expired.) with RARC none  | scenario: Timely filing, proof exists; Timely filing, expired, no proof  | [ ] OK  [ ] wrong  Notes: 
- CO-4 (The procedure code is inconsistent with the modifier used, or a required modifier is missing.) with RARC none  | scenario: Missing/invalid information or modifier  | [ ] OK  [ ] wrong  Notes: 
- CO-50 (The service was not deemed medically necessary by the plan.) with RARC N115  | scenario: Medical necessity, record supports; Medical necessity, record does not support  | [ ] OK  [ ] wrong  Notes: 
- CO-50 (The service was not deemed medically necessary by the plan.) with RARC N386  | scenario: Medical necessity, record supports; Medical necessity, record does not support  | [ ] OK  [ ] wrong  Notes: 
- CO-97 (The benefit for this service is included in the payment for another service already adjudicated.) with RARC N20  | scenario: Bundling / NCCI-style  | [ ] OK  [ ] wrong  Notes: 
- PR-1 (Amount applied to the patient's deductible.) with RARC none  | scenario: Patient responsibility (deductible)  | [ ] OK  [ ] wrong  Notes: 

## 4. Bundling pairs (CO-97 / N20, distinct-service modifier 59 or XS)

`97530 + 97140` is new in this round (it replaced `20610 + 76942`, which CPT rules do not allow to be billed together). Please also say whether 97110 + 97140 has an edit at all.

- Column 1: 97110 (Therapeutic exercise); denied column 2: 97140 (Manual therapy)  | 2 case(s)  | edit exists? modifier 59/XS allowed? [ ] OK  [ ] wrong  Notes: 
- Column 1: 97530 (Therapeutic activities); denied column 2: 97140 (Manual therapy)  | 3 case(s)  | edit exists? modifier 59/XS allowed? [ ] OK  [ ] wrong  Notes: 

## 5. Modifier / claim-data scenarios (CO-4, CO-16)

- CO-4: modifier GP missing on therapy (97110) (CPT 97110)  | 1 case(s)  | right CARC for this scenario? [ ] OK  [ ] wrong  Notes: 
- CO-16: place of service code missing (CPT 99213)  | 3 case(s)  | right CARC for this scenario? [ ] OK  [ ] wrong  Notes: 
- CO-16: rendering provider identifier missing (CPT 99213)  | 1 case(s)  | right CARC for this scenario? [ ] OK  [ ] wrong  Notes: 

## 6. Changed this round (flagged: coder to confirm)

- 99214 was replaced by 99213 everywhere (simple diagnoses). Confirm 99213 fits each pairing in section 1.
- CBC (85025) is now paired with D64.9 (anemia) or R53.83 (other fatigue) instead of hypertension.
- Categories 1-2: one diagnosis per claim (from M54.16, M54.17, M51.16, M51.17, M51.26) for CPT 72148.
- Bundling pair 20610 + 76942 replaced by 97530 + 97140 (candidates considered: 97530/97140, 97112/97140, 97110/97530).
- RARCs omitted for CO-197, CO-4, CO-18, CO-16.
- Kept as is: category 3 'urgent' scenario uses elective orthopedic procedures (27447, 29881, 63030) with an urgent-evaluation note; tell us if that is too unrealistic.

