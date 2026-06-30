# Steps Log - InvoiceFlow AI

---

## Step 41 - Simplify Hero Sample Controls
*Completed: 2026-07-01*

**What was built**
- `web/index.html` - hides the hero status row, removes the two large AP/AR sample buttons, and adds a “Run sample” label inside the compact sample card.
- `web/styles.css` - stacks the five compact sample buttons vertically and keeps hover, focus, selected, and running states.

**In plain English**
The extra buttons under the upload area are gone. The five curated sample buttons inside the compact card now line up one below another, with a clear “Run sample” label so users understand that clicking a case launches the demo.

**Files changed**
~ modified: web/index.html
~ modified: web/styles.css
~ modified: steps.md

---

## Step 40 - Move Workflow Rail Into Product Path
*Completed: 2026-07-01*

**What was built**
- `web/index.html` - moves the six-step workflow rail from the hero into the Product Path section and removes the extra path chips and paragraph.
- `web/styles.css` - adjusts Product Path spacing so the section is just the heading and workflow rail.

**In plain English**
The Product Path section now has the big “One readable route from case intake to audit” heading with the six-step workflow rail directly below it. The duplicate explanatory chips and paragraph were removed so the section is cleaner.

**Files changed**
~ modified: web/index.html
~ modified: web/styles.css
~ modified: steps.md

---

## Step 39 - Move Sample Launch Into Compact Card
*Completed: 2026-07-01*

**What was built**
- `web/index.html` - removes the separate sample-card grid and uses the compact sample card as the Cases anchor.
- `web/styles.css` - makes the compact sample chips read as clickable launch controls with hover, focus, running, and selected states.

**In plain English**
The extra “Run a focused demo case” section is gone. The five sample names inside the compact card are now the demo launcher, so clicking a case immediately runs that sample without needing a second big card grid below it.

**Files changed**
~ modified: web/index.html
~ modified: web/styles.css
~ modified: steps.md

---

## Step 38 - Redesign Operator Snapshot Cards
*Completed: 2026-07-01*

**What was built**
- `web/index.html` - restructures the three operator snapshot cards into feature cards with preview areas and copy areas.
- `web/styles.css` - styles the snapshot cards with ReactBits-inspired visual panels, staggered layout, preview graphics, and responsive stacking.

**In plain English**
The three cards under the upload controls now look more like polished product feature cards. Each card has a visual preview on top and the useful text below, so the section feels closer to the ReactBits reference instead of looking like plain dashboard boxes.

**Files changed**
~ modified: web/index.html
~ modified: web/styles.css
~ modified: steps.md

---

## Step 37 - Run Final Verification Pass
*Completed: 2026-07-01*

**What was built**
- `steps.md` - records the final verification pass for the creative UI phase.

**In plain English**
The app passed the final command checks after the creative UI work. JavaScript syntax is valid, the health endpoint is responding, sample cases load, and the evaluation summary reports all bundled cases passing. Browser automation was unavailable in this session, so that visual check was not claimed.

**Files changed**
~ modified: steps.md

---

## Step 36 - Polish Surfaces And Motion
*Completed: 2026-07-01*

**What was built**
- `web/styles.css` - adds a cohesive glass surface layer, softer pastel status colors, smoother hover motion, and gentler section separation.

**In plain English**
The page now feels more unified. Cards, badges, tables, buttons, and workflow elements share the same soft glass style, so the interface reads more like one polished product instead of separate pieces.

**Files changed**
~ modified: web/styles.css
~ modified: steps.md

---

## Step 35 - Add Unified Workflow Visual
*Completed: 2026-07-01*

**What was built**
- `web/index.html` - expands the hero workflow visual into six numbered stages from invoice intake through audit.
- `web/app.js` - updates the workflow visual as the loading stages progress.
- `web/styles.css` - styles the connected workflow rail with active and completed states.

**In plain English**
The top visual now behaves more like a product workflow instead of a row of static labels. When a case runs, the visual can move from invoice to extraction, policy, risk, decision, and audit so a viewer understands what the system is doing.

**Files changed**
~ modified: web/index.html
~ modified: web/app.js
~ modified: web/styles.css
~ modified: steps.md

---

## Step 34 - Organize Page Copy
*Completed: 2026-06-30*

**What was built**
- `web/index.html` - turns loose AP/AR explanation text into compact paired cards and adds a clearer product path sentence.
- `web/styles.css` - styles the new AP/AR cards, intake copy group, and path chips so the page reads in cleaner sections.

**In plain English**
The page now explains itself in a more ordered way. Instead of scattered sentences, the viewer sees what AP and AR mean, how to start, and the product path from upload to audit in grouped pieces that are easier to scan.

**Files changed**
~ modified: web/index.html
~ modified: web/styles.css
~ modified: steps.md

---

## Step 33 - Add Floating Glass Header
*Completed: 2026-06-30*

**What was built**
- `web/index.html` - turns the top nav into a structured product header with brand, centered section tabs, and system status.
- `web/app.js` - tracks scroll position so the header can switch into its compact scrolled state.
- `web/styles.css` - adds the fixed centered header, translucent glass styling, smooth shrink transition, responsive behavior, and ReactBits-style tab hover states.

**In plain English**
The page now has a real product-style top bar instead of a static header. At the top it feels clean and open, and when someone scrolls it tightens into a translucent floating pill with quick links for the main parts of the product.

**Files changed**
~ modified: web/index.html
~ modified: web/app.js
~ modified: web/styles.css
~ modified: steps.md

---

## Step 1 - Rewrite README Opening
*Completed: 2026-06-30*

**What was built**
- `README.md` - turns the opening into a product/client case-study intro with the intentional project origin story and the plain-English workflow promise.

**In plain English**
The project now explains itself immediately. A reader sees that InvoiceFlow AI is a finance workflow product for invoice review, AR follow-ups, policy evidence, human review, and audit trails. The opening now sounds intentional and product-focused instead of like a repo status note.

**Files changed**
~ modified: README.md

---

## Step 2 - Add Problem And Workflow Outputs
*Completed: 2026-06-30*

**What was built**
- `README.md` - adds the business problem, a plain workflow promise, and an input/output table for invoices, AR cases, customer emails, policy documents, and final workflow results.

**In plain English**
The README now explains why InvoiceFlow AI matters before it explains how the code works. A reader can see the manual finance work this product reduces, what kinds of documents go in, and what useful outputs come out. That makes the project easier for a beginner, recruiter, or client to follow.

**Files changed**
~ modified: README.md

---

## Step 3 - Add Best Demo Path
*Completed: 2026-06-30*

**What was built**
- `README.md` - adds a guided demo path from opening the operator console through the Missing PO sample, evidence review, human review, audit trail, and AR follow-up sample.

**In plain English**
The README now tells a viewer exactly how to try the product instead of making them explore randomly. A recruiter or client can follow the path and see the strongest AP and AR moments in the right order.

**Files changed**
~ modified: README.md

---

## Step 4 - Add Trust And Client Framing
*Completed: 2026-06-30*

**What was built**
- `README.md` - adds safety and privacy language, demo mode versus live AI mode, client adaptation ideas, and a clear skills-demonstrated section.

**In plain English**
The README now explains why the project feels safer and more commercially useful. A viewer can see that the demo works without paid API keys, risky cases go to human review, and the same product shape could be customized for real client finance workflows.

**Files changed**
~ modified: README.md

---

## Step 4.5 - Reduce README Technical Density
*Completed: 2026-06-30*

**What was built**
- `README.md` - moves safety, demo-mode, client adaptation, and skills sections before the technical reference, removes the duplicate demo path, and collapses dense API/eval metadata behind optional details.

**In plain English**
The README now stays easier for a beginner for longer. The product story, demo path, trust language, and client value come before the dense engineering details, while technical reviewers can still open the deeper API and CI information when they need it.

**Files changed**
~ modified: README.md

---

## Step 5 - Define Five Visible Demo Cases
*Completed: 2026-06-30*

**What was built**
- `web/index.html` - shows exactly five primary demo cases: Clean Invoice, Missing PO Invoice, Duplicate Invoice Risk, High-Value Approval Required, and AR Overdue Follow-Up.
- `web/app.js` - makes the operator snapshot count only the curated visible cases and uses friendly sample names while runs are processing.

**In plain English**
The app now gives users five clear demo choices instead of making the sample area feel open-ended or scattered. Each case teaches one finance control, so someone can understand what the product is good at before running anything.

**Files changed**
~ modified: web/index.html
~ modified: web/app.js

---

## Step 6 - Explain AP And AR In The UI
*Completed: 2026-06-30*

**What was built**
- `web/index.html` - explains AP as Accounts Payable/vendor invoice review and AR as Accounts Receivable/overdue payment follow-up in the hero, upload workflow selector, and product statement.

**In plain English**
The page no longer assumes the user already knows finance abbreviations. Someone can now understand that AP is about checking vendor invoices before payment, while AR is about following up when customers owe money.

**Files changed**
~ modified: web/index.html

---

## Step 7 - Match UI Case Names To README
*Completed: 2026-06-30*

**What was built**
- `README.md` - replaces the older raw sample list with the same five case names shown in the UI, including sample IDs and expected results.

**In plain English**
The README and app now use the same names for the main demo cases. A viewer will not see one label in the instructions and a different label inside the product.

**Files changed**
~ modified: README.md

---

## Step 8 - Create Centered Product Entry
*Completed: 2026-06-30*

**What was built**
- `web/index.html` - moves the operator snapshot into the hero so upload, sample status, sample chips, and latest audit feel like one entry surface.
- `web/styles.css` - centers the hero as a taller product entry and constrains the snapshot width so the first screen feels more focused.

**In plain English**
The top of the page now feels more like one clean starting point instead of a hero followed by a separate dashboard strip. The user sees the product promise, upload controls, sample actions, and current workflow state together.

**Files changed**
~ modified: web/index.html
~ modified: web/styles.css

---

## Step 9 - Clarify Upload Intake Row
*Completed: 2026-06-30*

**What was built**
- `web/index.html` - adds a short intake cue above the upload controls so users know they can start with a document or a sample case.
- `web/styles.css` - makes the upload row feel like a primary top action with a wider centered layout and subtle top/bottom rules.

**In plain English**
The upload area now reads like the main intake point instead of a plain form sitting under the hero text. A user can see immediately that they can either upload a document or run a sample case.

**Files changed**
~ modified: web/index.html
~ modified: web/styles.css

---

## Step 10 - Add Staged Loading Cue
*Completed: 2026-06-30*

**What was built**
- `web/app.js` - cycles the loading cue through reading/uploading, extracting facts, retrieving policy evidence, checking risk signals, and preparing the recommendation while a sample or upload is running.

**In plain English**
The app now tells the user what kind of work is happening instead of showing one static loading message. This makes the workflow feel more understandable while the result is being prepared.

**Files changed**
~ modified: web/app.js

---

## Step 11 - Create Four Main Visible Areas
*Completed: 2026-06-30*

**What was built**
- `web/index.html` - renames the workspace navigation and panel headings around Case Summary, Evidence & Reasoning, Human Review & Audit, and Evaluation.

**In plain English**
The result workspace now has clearer labels. Instead of sounding like a mix of workflow, inspect, queue, and debug panels, the page points users toward the main areas they need after running a case.

**Files changed**
~ modified: web/index.html

---

## Step 12 - Put Decision First
*Completed: 2026-06-30*

**What was built**
- `web/index.html` - rewrites the top result card labels around the operator decision, confidence/risk, human review, evidence, and why.
- `web/app.js` - prefixes AP output with a clear reason and AR output with the draft subject so the top summary reads like a decision, not metadata.
- `web/styles.css` - gives the decision card stronger visual hierarchy with subtle rules and larger recommendation type.

**In plain English**
The result now starts by answering what the operator should do, why, how risky it is, whether a person needs to review it, and what evidence supports it. A finance user no longer has to scan technical details first.

**Files changed**
~ modified: web/index.html
~ modified: web/app.js
~ modified: web/styles.css

---

## Step 13 - Hide Debug And Raw JSON
*Completed: 2026-06-30*

**What was built**
- `web/index.html` - turns the raw backend response into a compact Advanced Debug disclosure instead of a visible debug panel.
- `web/styles.css` - gives the debug disclosure quieter spacing and secondary styling so it stays available without dominating the Evidence & Reasoning tab.

**In plain English**
The page now keeps technical JSON available for engineers, but normal users do not have to look at it first. The result flow stays focused on the recommendation, evidence, and review path.

**Files changed**
~ modified: web/index.html
~ modified: web/styles.css

---

## Step 14 - Add Why This Decision
*Completed: 2026-06-30*

**What was built**
- `web/index.html` - adds a dedicated reasoning checklist under the main decision summary.
- `web/app.js` - fills the checklist from extracted fields, policy assessment, evidence, risk, recommendation, and human review metadata.
- `web/styles.css` - styles the checklist as a lightweight fact grid that stays readable on desktop and mobile.

**In plain English**
The result page now explains the recommendation with concrete facts instead of only a short summary. A user can see whether a PO was required, whether one was found, what amount and policy were used, what risk level applied, and whether human review is needed.

**Files changed**
~ modified: web/index.html
~ modified: web/app.js
~ modified: web/styles.css

---

## Step 15 - Clarify Missing Info Versus Reject
*Completed: 2026-06-30*

**What was built**
- `web/app.js` - changes recommendation labels and explanations so missing info, human review, and rejection read as separate operator actions.
- `web/index.html` - replaces raw expected-result codes in the demo cards with beginner-readable outcome labels.

**In plain English**
The app now avoids making “missing info” sound like a rejection. A user can tell that missing info means “ask for more details,” human review means “send to a person,” and reject means “do not proceed.”

**Files changed**
~ modified: web/app.js
~ modified: web/index.html

---

## Step 16 - Clean Policy Evidence Panel
*Completed: 2026-06-30*

**What was built**
- `web/index.html` - renames the evidence column to Policy evidence.
- `web/app.js` - renders each evidence item with source, citation, matched rule, excerpt, decision impact, and why it was relevant.
- `web/styles.css` - improves the evidence panel spacing, citation chips, and excerpt treatment while keeping the unboxed layout.

**In plain English**
The evidence area now reads like a policy match instead of a technical data card. A user can see which policy source was used, the citation ID, the matched rule, why it mattered, and what part of the decision it influenced.

**Files changed**
~ modified: web/index.html
~ modified: web/app.js
~ modified: web/styles.css

---

## Step 17 - Add Weak Evidence Behavior
*Completed: 2026-06-30*

**What was built**
- `web/app.js` - detects missing, uncited, or fallback evidence and routes the visible recommendation toward human review instead of sounding automatic.

**In plain English**
The app now says when evidence is too weak to trust as an automatic decision. If policy support is missing or weak, the decision summary and reasoning checklist tell the operator to send the case to human review before acting.

**Files changed**
~ modified: web/app.js

---

## Step 18 - Add Workflow Visual
*Completed: 2026-06-30*

**What was built**
- `web/index.html` - adds a top workflow visual showing Invoice, Extract, Policy Check, Decision, and Audit.
- `web/styles.css` - styles the visual with a restrained animated sweep and responsive mobile stacking.

**In plain English**
The top of the page now shows the product flow visually before the user reaches the upload controls. It explains the path from invoice intake to audit trail in one glance without adding a heavy animation or distracting 3D effect.

**Files changed**
~ modified: web/index.html
~ modified: web/styles.css

---

## Step 19 - Add Subtle Motion
*Completed: 2026-06-30*

**What was built**
- `web/app.js` - toggles a workflow-running page state while a sample or upload is processing.
- `web/styles.css` - adds subtle workflow-node motion, running status pulses, active sample highlighting, and reduced-motion safeguards.

**In plain English**
The page now feels more alive while a workflow is running. The motion is tied to real processing states, so it helps the user understand that extraction, policy retrieval, risk checking, and recommendation work are in progress.

**Files changed**
~ modified: web/app.js
~ modified: web/styles.css

---

## Step 20 - Badge And Color Polish
*Completed: 2026-06-30*

**What was built**
- `web/styles.css` - adds softer shared green, amber, red, and blue-gray tokens and applies them to status pills, risk badges, queue statuses, sample chips, and anomaly tags.

**In plain English**
The badges now feel calmer and more consistent. Green still means safe, amber still means review or missing info, red still means high risk, and blue-gray now handles neutral/information states without making the page feel loud.

**Files changed**
~ modified: web/styles.css

---

## Step 21 - Add Empty And Error States
*Completed: 2026-06-30*

**What was built**
- `web/index.html` - adds upload guidance that explains supported files and OCR limitations.
- `web/app.js` - adds client-side file type checks and clearer upload failure messages for empty files, unsupported files, OCR limitations, and parsing failures.
- `web/styles.css` - styles upload guidance and improves empty-state readability.

**In plain English**
The upload flow now tells the user what went wrong and what to try next. If a file is missing, unsupported, scanned, empty, or hard to parse, the page gives a direct fallback instead of only showing a generic failure.

**Files changed**
~ modified: web/index.html
~ modified: web/app.js
~ modified: web/styles.css

---

## Step 22 - Improve Mobile Layout
*Completed: 2026-06-30*

**What was built**
- `web/styles.css` - strengthens the final mobile breakpoints for page padding, hero sizing, workflow visual stacking, upload controls, buttons, tabs, cards, result grids, tables, and long text wrapping.

**In plain English**
The page now behaves better on smaller screens. Controls stack cleanly, buttons become full-width when space is tight, the workflow visual becomes vertical, and long labels are less likely to overflow.

**Files changed**
~ modified: web/styles.css

---

## Step 23 - Add Compact Evaluation Table
*Completed: 2026-06-30*

**What was built**
- `README.md` - adds a compact five-case evaluation proof table under Evaluation Proof.

**In plain English**
The README now shows the expected result, actual result, and pass status for the five main demo cases before the technical eval commands. A reviewer can see that the core workflows are checked without reading the full eval implementation first.

**Files changed**
~ modified: README.md

---

## Step 24 - Keep Eval UI Secondary
*Completed: 2026-06-30*

**What was built**
- `web/index.html` - reframes the eval tab as Evaluation Proof and explains that it supports the operator workflow.
- `web/styles.css` - quiets the eval metric grid with smaller metric type, lighter separators, and fewer dominant columns.

**In plain English**
The evaluation area now feels like supporting proof instead of the main product. It still shows quality gates, but the page continues to prioritize the operator workflow, recommendation, evidence, and human review path.

**Files changed**
~ modified: web/index.html
~ modified: web/styles.css

---

## Step 25 - Refresh Screenshots
*Completed: 2026-06-30*

**What was built**
- `docs/screenshots/operator-console.png` - captures the polished centered operator entry screen.
- `docs/screenshots/ap-result.png` - captures the AP Missing PO decision-first result.
- `docs/screenshots/evidence-panel.png` - captures the policy evidence and reasoning view.
- `docs/screenshots/human-review-queue.png` - captures the human review and audit queue.
- `docs/screenshots/eval-dashboard.png` - captures the secondary evaluation proof view.
- `docs/screenshots/ar-follow-up.png` - captures the AR overdue follow-up result.

**In plain English**
The repo now has fresh screenshots that match the current product UI. A reviewer can see the operator entry, AP decision, evidence trail, review queue, evaluation proof, and AR follow-up without needing to run the app first.

**Files changed**
+ created: docs/screenshots/operator-console.png
+ created: docs/screenshots/ap-result.png
+ created: docs/screenshots/evidence-panel.png
+ created: docs/screenshots/human-review-queue.png
+ created: docs/screenshots/eval-dashboard.png
+ created: docs/screenshots/ar-follow-up.png
~ modified: steps.md

---

## Step 26 - Update Demo Walkthrough
*Completed: 2026-06-30*

**What was built**
- `docs/showcase.md` - adds a best demo path and rewrites the 75-second script around the current operator entry, AP Missing PO, Evidence & Reasoning, Human Review & Audit, AR Overdue Follow-Up, and Evaluation views.

**In plain English**
The demo now has a clear script for what to click and what to say. Someone showing the project can walk through the product in order instead of jumping between random technical pieces.

**Files changed**
~ modified: docs/showcase.md
~ modified: steps.md

---

## Step 27 - Add Prompt Schema Guardrail Panel
*Completed: 2026-06-30*

**What was built**
- `web/index.html` - adds a compact Prompt, Schema, and Guardrail readout inside the collapsed Advanced Debug panel.
- `web/app.js` - renders prompt version, extractor mode, schema status, repair status, PII redaction, LLM gateway calls, stage latency, and token metadata from the workflow audit payload.
- `web/styles.css` - styles the guardrail readout as a quiet technical grid that collapses cleanly on small screens.

**In plain English**
The app now gives technical reviewers a clear place to inspect how the AI workflow was controlled. Normal operators still see the simple decision-first flow, while advanced users can expand Debug to check prompts, schema validation, repair behavior, gateway metadata, and latency.

**Files changed**
~ modified: web/index.html
~ modified: web/app.js
~ modified: web/styles.css
~ modified: steps.md

---

## Step 28 - Strengthen Backend Reliability
*Completed: 2026-06-30*

**What was built**
- `api/main.py` - adds extractor-mode validation, upload size/type checks, structured error responses, OCR/text fallback hints, and safer generic workflow errors.
- `tests/test_api_reliability.py` - adds API tests for health, missing samples, invalid extractor modes, empty uploads, unsupported file types, and text upload fallback behavior.

**In plain English**
The backend now handles bad inputs more cleanly. Instead of leaking raw internal errors or accepting unsupported files, the API returns clear error codes and practical next steps while keeping the happy-path upload and sample workflows working.

**Files changed**
~ modified: api/main.py
+ created: tests/test_api_reliability.py
~ modified: steps.md

---

## Step 29 - Add CI Test And Eval Gate
*Completed: 2026-06-30*

**What was built**
- `.github/workflows/eval.yml` - renames the workflow to InvoiceFlow CI and runs backend compile checks, unit tests, eval threshold checks, and eval artifact upload.

**In plain English**
GitHub will now prove more of the project automatically. Instead of only running the evaluation gate, CI also checks that backend modules compile and the API reliability tests pass before publishing the eval report.

**Files changed**
~ modified: .github/workflows/eval.yml
~ modified: steps.md

---

## Step 30 - Verify GitHub CI Run
*Completed: 2026-06-30*

**What was built**
- `steps.md` - records that the latest `InvoiceFlow CI` GitHub Actions run completed successfully.

**In plain English**
GitHub has now proved the CI workflow works after the push. The backend compile check, backend tests, eval threshold gate, and eval artifact upload all passed in the `Backend tests and eval thresholds` job.

**Files changed**
~ modified: steps.md

---

## Step 31 - Polish Frontend States
*Completed: 2026-06-30*

**What was built**
- `web/app.js` - formats structured backend error details into readable UI messages and tracks the currently selected demo sample.
- `web/styles.css` - adds selected sample styling, clearer focus states, and a softer active loading cue.

**In plain English**
The page now gives cleaner feedback while someone runs demos or hits an upload error. Selected cases stay visually marked, keyboard focus is easier to see, and structured backend errors become useful messages instead of technical object text.

**Files changed**
~ modified: web/app.js
~ modified: web/styles.css
~ modified: steps.md

---

## Step 32 - Browser Check Upload Row
*Completed: 2026-06-30*

**What was built**
- `web/styles.css` - widens the top workflow selector and document upload columns so the workflow type label is readable in the browser.

**In plain English**
The top upload controls now read more clearly. The workflow dropdown no longer cuts off “AP - vendor invoice review,” so a first-time viewer can understand the upload choice without guessing.

**Files changed**
~ modified: web/styles.css
~ modified: steps.md

---

## Step 33 - Merge Product Path And Workspace Tabs
*Completed: 2026-07-01*

**What was built**
- `web/index.html` - replaces the separate product path rail and lower tab row with one clickable four-stage workflow rail.
- `web/styles.css` - styles the merged rail like the product path cards and shrinks the upload support line into a mini note.
- `web/app.js` - keeps the header highlight matched to Overview, Cases, Summary, Evidence, Review, or Eval based on page position and selected workspace view.

**In plain English**
The Product Path and the lower tabs no longer feel like two different things. The path itself now works as the section switcher, so a viewer can click Case Summary, Evidence, Review, or Evaluation and immediately understand what part of the workflow they are opening. The top header also behaves more naturally: it highlights Overview near the hero, Cases near the sample area, and the correct workspace view once the user reaches the workflow area.

**Files changed**
~ modified: web/index.html
~ modified: web/styles.css
~ modified: web/app.js
~ modified: steps.md

---

## Step 34 - Add Hero Aurora And Guide Cards
*Completed: 2026-07-01*

**What was built**
- `web/index.html` - turns the side snapshot cards into first-time user guides for the current case and latest decision.
- `web/styles.css` - adds a subtle soft aurora hero layer, one-line desktop helper note, and styles for guide facts, decision facts, and the mini audit timeline.
- `web/app.js` - updates the guide cards with real case facts, recommendation, evidence count, review gate, and timeline state after a run.

**In plain English**
The top area now has more personality and more guidance. Before a sample runs, the side cards explain how to read the product: choose a case, extract facts, check policy, decide, then review the evidence-backed output. After a run, those same cards turn into live summaries showing the desk, party, amount, recommendation, evidence count, review gate, and audit progress.

**Files changed**
~ modified: web/index.html
~ modified: web/styles.css
~ modified: web/app.js
~ modified: steps.md

---

## Step 35 - Strengthen Hero Aurora Ribbon
*Completed: 2026-07-01*

**What was built**
- `web/styles.css` - replaces the faint hero haze with a visible Soft Aurora-style horizontal ribbon using green, cream, and amber gradients.

**In plain English**
The hero background now reads more like an actual aurora instead of a barely visible wash. The glow stays in the existing InvoiceFlow palette, but it has a clearer wave shape like the React Bits reference.

**Files changed**
~ modified: web/styles.css
~ modified: steps.md

---

## Step 36 - Clarify Hero Section Spacing And Samples
*Completed: 2026-07-01*

**What was built**
- `web/index.html` - adds a “What's inside?” heading above the three operator cards and turns “Start the review” into a real heading.
- `web/styles.css` - improves vertical spacing, removes the pill styling from the “Run sample” label, prevents the sample overlay from blocking clicks, and gives all five sample buttons enough room.

**In plain English**
The top of the page now separates the upload flow from the three explanatory cards more clearly. The sample card label is plain text instead of a small bubble, and the AR Overdue button has enough space to be clickable like the other sample buttons.

**Files changed**
~ modified: web/index.html
~ modified: web/styles.css
~ modified: steps.md

---

## Step 37 - Make Hero Full Width
*Completed: 2026-07-01*

**What was built**
- `web/styles.css` - removes the boxed hero margins, lets the hero background span the full page width, left-aligns the “Start the review” block with the upload form, adds more spacing between heading groups, and widens the Product Path heading so it breaks into two lines.

**In plain English**
The top hero should now feel more like a full product page instead of a centered card sitting on the background. The upload section is easier to scan because its heading aligns with the form, and the Product Path headline should read in two clean lines instead of three cramped lines.

**Files changed**
~ modified: web/styles.css
~ modified: steps.md

---

## Step 38 - Clean Up Replaced Learning Docs
*Completed: 2026-07-01*

**What was built**
- `learnings/phase-15h-product-path-rail.md` - rewrites the visual UI learning note as the current source of truth for the full-width hero, guide cards, sample launcher, and Product Path.
- `learnings/phase-7-signature-visual.md` - removed because it described the old workflow-orbit visual.
- `learnings/phase-15c-unified-workflow-visual.md` - removed because it described a replaced workflow rail.
- `learnings/phase-15f-operator-snapshot-cards.md` - removed because the older card experiment was replaced by the current guide cards.

**In plain English**
The learning folder no longer keeps old UI experiments as if they are still part of the product. The current visual documentation now describes the page that actually exists: full-width hero, Soft Aurora-style ribbon, Start the review, What's inside cards, sample launcher, Latest Decision, and the four-stage Product Path.

**Files changed**
- deleted: learnings/phase-7-signature-visual.md
- deleted: learnings/phase-15c-unified-workflow-visual.md
- deleted: learnings/phase-15f-operator-snapshot-cards.md
~ modified: learnings/phase-15h-product-path-rail.md
~ modified: steps.md

---
