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
