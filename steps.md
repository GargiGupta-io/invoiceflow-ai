# Steps Log - InvoiceFlow AI

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
