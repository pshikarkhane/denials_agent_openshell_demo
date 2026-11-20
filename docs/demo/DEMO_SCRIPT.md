# Demo script: sandboxed denial-appeals agent

Put this file at `demo/script.md`. Total talk time about 8 to 9 minutes, plus questions.

Items in **[FILL]** brackets must be completed from the final data before you present. The script is written for the cached GUI plus the architecture slide, so it needs no VM, no network and no API key on the day.

## The one-sentence message

A Hermes agent inside an OpenShell sandbox works a claim denial from end to end, decides whether to appeal, and writes the deliverable; independent judges score it; and the runtime, not the model, keeps patient data inside.

## Before you start (not part of the talk)

- [ ] On the laptop you will present from: `npm run build && npm run preview` in the GUI folder; open every page once (Home, Case C-0005, Case C-0030, Containment, Scorecard) and confirm nothing is blank.
- [ ] Browser zoom set so text is readable from the back of the room; notifications off; charger plugged in.
- [ ] The architecture slide exported as a PDF and saved on the same laptop.
- [ ] A screen recording of the full walkthrough saved locally, as a fallback.
- [ ] Open the Scorecard and check each number against `docs/HERMES_RUN_REPORT.md` and `docs/RUN_REPORT.md`.
- [ ] On the Containment page, confirm each scenario's label says **natural** or **scripted**, and that you can say which one you are showing.
- [ ] The VM and the API key are not needed. Do not depend on either.

## Flow at a glance

| # | Screen | Time | The point |
|---|---|---|---|
| 1 | Architecture slide | 1:00 | What the pieces are and where the walls are |
| 2 | Home | 0:30 | The scenarios |
| 3 | Case C-0005 | 1:45 | The agent works the chart and writes the appeal |
| 4 | Case C-0030 | 1:15 | It knows when not to appeal |
| 5 | Containment | 2:00 | The runtime blocks the exfiltration attempt |
| 6 | Scorecard | 1:15 | How it is scored, with the caveats |
| 7 | The model swap and what is next | 0:45 | R1's checkpoint plugs in through the route |

---

## 1. Architecture slide (1:00)

**Show:** the slide.

**Say:**
"A revenue-cycle team gets a denial. Our agent reads the denial, finds the payer policy, checks the clinical record, and either drafts the appeal or tells you not to file one.
Everything the agent touches sits inside this green box, an OpenShell sandbox, which is like a data room: default-deny network, a read-only copy of the case, and an audit log.
Two things stay outside the wall. The answer key never enters the sandbox. And three independent judges score the output afterwards.
The one hole in the wall is the model endpoint, Nemotron 3.5 Super. That route is swappable, which is where R1's post-trained model plugs in."

**Point at:** the red dashed answer-key box, then the arrow labeled "only allowed egress".

**Avoid saying** "only allowed egress" as a finished fact unless the policy hardening is confirmed. Say "the one route the policy allows" only if it is.

## 2. Home (0:30)

**Show:** the Home page.

**Say:**
"All the data here is synthetic. These cards are the stories I will walk through: a win, a judgment call, an attack, the scorecard."

Click **The win**.

## 3. Case C-0005, the appeal (1:45)

**Show:** the Case page, "Before & After" tab.

**Say:**
"This is a medical-necessity denial, [FILL: denial code and policy id from the page]. The decision is [FILL: decision].
On the right, the agent. These chips are the real steps it took inside the sandbox: parse the denial, retrieve the policy, pull the notes, assess, draft, and self-check.
Every claim in the letter carries a source. These green tags point to the document each fact came from.
On the left is the same model with no tools and everything pasted into one prompt. [FILL: one sentence on what the data shows. Examples: where it matched, or where the judges flagged something. Read it from the page.]"

**Click:** the **Criteria** tab.

**Say:**
"Each case has its own checklist of yes/no criteria. Three judges from three model families grade each one. Here is the verdict by judge."

**Click:** the **Trace** tab briefly, expand one step.

**Say:**
"Hermes runs each skill by typing a command into its terminal, and the trace shows the actual command. [If errors are visible:] You can see one step failed and the agent recovered. That is a real run, not a cleaned-up one."

## 4. Case C-0030, the judgment call (1:15)

**Show:** the C-0030 Case page.

**Say:**
"This one is a timely-filing denial. The correct answer is not to appeal.
Here is the arithmetic the agent shows: [FILL: date of service, filing limit, resulting deadline, date the payer received the claim, as shown on the page].
A letter generator would write a letter anyway. This agent recommends the right alternative and explains why. About 40 percent of our cases are designed so the right answer is not to appeal."

If the trace shows a self-check failure and revision, point at it:
"It also checked its own work, found a problem, fixed it, and re-checked."

## 5. Containment (2:00)

**Show:** the Containment page, scenario A1.

**Say (natural run):**
"Here a clinical note contains a hidden instruction: send the patient record to an outside address. That address is deliberately fake and unroutable.
Left: what the agent did. At this step it tried to send the data. Right: what the sandbox recorded. This row is the connection attempt, and it is denied.
The model can be fooled. The runtime cannot be. [FILL: attempt rate, for example 'In N of 5 runs the agent attempted it.']"

**Say (scripted run, if that is what you are showing):**
"In our tests the agent [FILL: how often it followed the injection]. To show the runtime's behavior reliably, this recording is a **scripted attempt**: we ran the same command the agent would have run. The block and the log are real."

**Always:** point at the amber label so the audience sees which kind it is.

**Say:**
"According to the audit log, the only allowed connections during this run went to the model endpoint [FILL: confirm from the outcome panel]. The agent still finished the task and made the right decision."

**If you show the file-based attack (A3):**
"File access is different. The sandbox blocks it through file permissions, but the audit log does not record blocked file reads and writes. The evidence is this error in the trace. We are not claiming it is audited."

**Toggle:** show the "background" events to explain the extra denied rows: "These are Hermes' own background requests, which the policy also denies."

## 6. Scorecard (1:15)

**Show:** the Scorecard.

**Say:**
"Quality, on a small pilot of five synthetic cases, two repeats each:
Hermes made the right decision in all 10 runs. The criterion pass rate is 97.8 percent, versus 98.2 percent for our earlier version running outside the sandbox, so the sandbox cost us no accuracy on these cases.
It uses about three times as many tokens, mostly Hermes' own built-in prompt: about 250 thousand tokens a run versus about 84 thousand, and about 50 seconds a run.
We do not claim fewer hallucinations. Judge noise is about 0.4 flags per run, and the differences between versions are that size.
This is a pilot of five cases, not a benchmark. The category grid shows what has not been run yet."

[FILL: one line on the no-tools baseline's pass rate from RUN_REPORT.md, if you want to compare.]

## 7. The model swap and what is next (0:45)

**Show:** the Scorecard's model toggle (R1 checkpoint, shown as pending), or the architecture slide.

**Say:**
"The model sits behind one route. We tested switching it in place, with no rebuild: the gateway restarts in about 42 seconds. R1's post-trained checkpoint plugs in the same way once we know how it is served, and the same cases and judges then measure the difference.
What is next: the remaining 55 cases for a held-out test, finishing judge validation, and a coder reviewing the billing codes."

**Do not** try the swap live on stage.

---

## Numbers you can quote (with sources)

| Claim | Number | Source |
|---|---|---|
| Hermes runs finished and wrote both files | 10 of 10 | HERMES_RUN_REPORT |
| Correct decision | 10 of 10 (5 of 5 cases, same decision in both repeats) | HERMES_RUN_REPORT |
| Panel criterion pass | 97.8% (stand-in 98.2%) | HERMES_RUN_REPORT |
| Upheld material hallucination flags per run | 0.50 (stand-in 0.80) | HERMES_RUN_REPORT, inside judge noise |
| Clean runs (no upheld material flag) | 70% (stand-in 67%) | HERMES_RUN_REPORT |
| Tokens per run | about 250k (stand-in about 84k) | HERMES_RUN_REPORT |
| Hermes' fixed prompt per call | about 13.3k tokens (stand-in about 2.75k) | HERMES_RUN_REPORT |
| Tool errors | 14.5% of all tool calls, 20.7% of skill calls, all recovered | HERMES_RUN_REPORT |
| Time per run | about 50 s | HERMES_RUN_REPORT |
| Route swap restart | about 42 s | phase0_setup |
| Attack results | [FILL from CONTAINMENT_REPORT] | CONTAINMENT_REPORT |

## Do not say

- "The agent hallucinates less than the baseline."
- "Benchmark," "accuracy of X percent," or anything about unseen cases.
- "HIPAA compliant." Use "a demonstration of HIPAA-aligned controls" if at all.
- "Validated codes." They are synthetic and not coding-validated.
- "R1's model" as having run. It is base Nemotron 3.5 Super.
- "File access is logged." Blocked file access is not in the audit log.
- "Real patient data." Everything is synthetic.

## Likely questions, with honest answers

**Is this better than just prompting a model?**
On this pilot the quality was about the same as our earlier version, and the agent covered more of the checklist than a no-tools baseline [FILL: figure]. The value shown here is the structure: the right decision including not appealing, an auditable trace, and the sandbox containing the data.

**Does it use R1's model?**
No. It runs base Nemotron 3.5 Super. The harness, cases and judges are ready for R1's checkpoint to be swapped in.

**How accurate is it?**
We have a five-case pilot with synthetic data, so we do not quote an accuracy figure. A 48-case held-out run is the next step.

**Can the judges be trusted?**
Three model families grade each criterion, and none is the agent. We ran part of a validation that plants known errors; most were caught, and the full validation is queued. We say judge noise is about 0.4 flags per run.

**Why three times the tokens?**
Hermes carries a large built-in prompt on every call. It does not change the answer quality, and it can be trimmed later.

**Is it HIPAA compliant?**
We have not claimed that. This demonstrates the controls: data stays in the sandbox, only approved connections are allowed, and every connection is logged.

**What stops real data leaking in production?**
The sandbox policy, not the model. The agent can be tricked, but a denied connection stays denied. File access is also restricted, though blocked file access is not in the audit log.

**What about the answer key?**
It is never in the sandbox. The agent cannot read it.

**How long does swapping the model take?**
About 42 seconds, with no rebuild. We tested it between two models on the same endpoint. A different endpoint needs a policy entry, which we have not tested.

**Are the billing codes right?**
They are synthetic and have not been reviewed by a coder. That review is on the list.

## If something breaks

| Problem | Do this |
|---|---|
| A GUI page is blank or errors | Reload once. If still broken, switch to the screen recording |
| The laptop switches networks or sleeps | Nothing depends on the network. Wake it and continue |
| You lose your place | Go back to Home and click the next card |
| A number on screen disagrees with this script | Trust the screen, and say it is from the pilot report |
| Someone asks for a live run | "This is a cached replay of recorded runs. A live mode is on the list." |
| Someone asks something you do not know | "I do not have that measured yet. It is on our list." Then write it down |

## After the demo

- Note every question you could not answer and add it to `docs/BACKLOG.md`.
- Start with the highest-priority backlog items: the held-out run, the judge validation, the coder review, R1's serving details.
