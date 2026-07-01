━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PLAN: InvoiceFlow AI Paid-Ready Product Redesign
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Goal: Turn InvoiceFlow AI into a simple, elegant, paid-ready AI finance workflow product that proves product thinking, AI workflow depth, and creative frontend taste without becoming cluttered.

  Current State:
  The repo already has:

  - FastAPI backend
  - AP/AR workflow samples
  - RAG/policy evidence
  - structured extraction
  - review queue
  - evaluation dashboard
  - audit/debug metadata
  - static frontend in web/
  - README/docs/screenshots

  The issue is presentation:

  - README is still too repo-like.
  - UI still feels section-heavy.
  - The product story is not obvious enough.
  - Creative visual identity is still weak.
  - There are too many visible concepts at once.

  Core Strategy:
  We will not rewrite the architecture first. We will polish the product surface, demo flow, explainability, README, screenshots, and trust framing. The app should feel like:

  > Select/upload case → extract facts → check policy → detect risk → recommend action → human review → audit trail.

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  EXECUTION RULES
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Before each step, I will tell you:

  - Files I will change
  - What I will change
  - Why it matters
  - What I will not touch

  After each step, I will:

  - verify the change where possible
  - commit granularly
  - push to GitHub
  - update project step notes
  - ask:

  > Can a beginner human understand this page as it goes?

  I will not batch steps unless you explicitly tell me to.

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  STEP PLAN
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Phase 1: README Becomes A Client Case Study

  Step 1: Rewrite README Opening
  Files:

  - README.md

  What changes:

  - Replace the current repo-style opening with a product/client case-study intro.
  - Add the intentional origin story:
    “I originally built InvoiceFlow AI as a YC-style product prototype…”

  - Add the product promise in plain English.

  Why:

  - Recruiters and clients should understand the project in under 60 seconds.

  Not touching:

  - frontend
  - backend
  - samples
  - screenshots

  Step 2: Add Problem, Product Promise, Inputs/Outputs
  Files:

  - README.md

  What changes:

  - Add “The Problem”
  - Add “What InvoiceFlow Does”
  - Add input/output table:
    invoice PDF, invoice text, AR email, policy docs → extracted fields, evidence, decision, human review, audit trail

  Why:

  - Makes the README read like a real product, not a class assignment.

  Step 3: Add Best Demo Path
  Files:

  - README.md

  What changes:

  - Add a guided demo path:
    Open app → choose Missing PO → check fields → check evidence → decision → review → audit → AR follow-up.

  Why:

  - People do not explore random UIs. We need to guide them.

  Step 4: Add Client Adaptation, Safety, Deployment, Skills
  Files:

  - README.md

  What changes:

  - Add:
      - Safety and privacy
      - Demo mode vs live AI mode
      - Client adaptation section
      - Skills demonstrated
      - limitations
      - future improvements

  Why:

  - This makes the repo feel commercially useful.

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Phase 2: Focus The Product Around Five Demo Cases

  Step 5: Define The Five Visible Demo Cases
  Files:

  - web/index.html
  - web/app.js

  Visible cases:

  - Clean Invoice
  - Missing PO Invoice
  - Duplicate Invoice Risk
  - High-Value Approval Required
  - AR Overdue Follow-Up

  What changes:

  - Remove/hide extra demo clutter from the main UI.
  - Make the five cases the only primary visible demo choices.

  Why:

  - Five strong cases are better than many confusing ones.

  Not touching:

  - backend fixtures unless needed
  - eval dataset unless mismatch appears

  Step 6: Add Plain AP/AR Descriptions
  Files:

  - web/index.html

  What changes:

  - Add short one/two-line explanation:
      - AP = reviewing vendor invoices before payment.
      - AR = following up on overdue customer payments.

  Why:

  - A beginner should not need to know finance jargon.

  Step 7: Match UI Case Names To README
  Files:

  - README.md
  - web/index.html
  - web/app.js

  What changes:

  - Ensure README and UI use the same exact case names.

  Why:

  - Demo path should not confuse people with mismatched wording.

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Phase 3: Rebuild The Main Page Flow

  Step 8: Create A Centered Product Entry
  Files:

  - web/index.html
  - web/styles.css

  What changes:

  - Top area becomes centered and clean.
  - Brand, one-line product promise, AP/AR explanation, upload/select controls.
  - No giant dashboard maze at the top.

  Why:

  - The first screen should feel like a premium product entry, not a pile of panels.

  Step 9: Move Upload Controls To The Top
  Files:

  - web/index.html
  - web/styles.css
  - web/app.js

  What changes:

  - File picker stays at the top.
  - Upload button includes AP/AR workflow selector.
  - User does not click a button that jumps somewhere else.

  Why:

  - The first action must be obvious.

  Step 10: Add Staged Loading Cue
  Files:

  - web/index.html
  - web/styles.css
  - web/app.js

  What changes:

  - Add cute but restrained loading states:
      - Uploading
      - Extracting facts
      - Retrieving policy
      - Checking risk
      - Preparing recommendation

  Why:

  - Makes the workflow feel alive and understandable.

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Phase 4: Case Detail Becomes The Core Product Surface

  Step 11: Create Four Main Visible Areas
  Files:

  - web/index.html
  - web/styles.css

  Visible areas:

  1. Demo Case Selector
  2. Case Summary
  3. Evidence & Reasoning
  4. Human Review & Audit

  What changes:

  - Reduce visible clutter.
  - Put related content together.

  Why:

  - A finance manager should understand the screen in 5 seconds.

  Step 12: Decision Comes First
  Files:

  - web/index.html
  - web/app.js

  What changes:

  - Show:
      - Recommendation
      - reason
      - confidence/risk
      - human review required
        before raw details.

  Why:

  - Operators care first about “what should I do?”

  Step 13: Hide Debug/Raw JSON
  Files:

  - web/index.html
  - web/app.js
  - web/styles.css

  What changes:

  - Raw JSON moves into collapsed Advanced Debug.
  - Technical trace stays available, but not primary.

  Why:

  - Keeps the product simple while still proving engineering depth.

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Phase 5: Explainability Panel

  Step 14: Add “Why This Decision?”
  Files:

  - web/index.html
  - web/app.js
  - web/styles.css

  What changes:

  - Add a clear explanation panel showing:
      - PO required?
      - PO found?
      - amount
      - approval threshold
      - matching policy
      - risk level
      - recommended action
      - human review status

  Why:

  - This is what makes it trustworthy instead of “AI magic.”

  Step 15: Separate Missing Info From Rejection
  Files:

  - web/app.js

  What changes:

  - Make wording clear:
      - missing info = needs more data
      - reject = likely invalid/risky
      - review = human should inspect

  Why:

  - Finance users need safe decision language.

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Phase 6: Evidence And RAG Transparency

  Step 16: Clean Policy Evidence Panel
  Files:

  - web/index.html
  - web/app.js
  - web/styles.css

  What changes:

  - Evidence shows:
      - source name
      - citation/id
      - matched rule
      - why it mattered
      - which decision it influenced

  Why:

  - RAG should be visible without using the word RAG everywhere.

  Step 17: Add Weak Evidence Behavior
  Files:

  - web/app.js

  What changes:

  - If evidence is missing/weak, UI should say that clearly and route to review.

  Why:

  - Weak evidence must not produce confident decisions.

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Phase 7: Signature Creative Visual

  Step 18: Add Workflow Visual
  Files:

  - web/index.html
  - web/styles.css

  Visual:
  Invoice → Extract → Policy Check → Decision → Audit

  What changes:

  - Add one restrained animated visual near the top.
  - Use CSS/canvas-style feel, not heavy 3D yet.

  Why:

  - Shows creative taste while supporting the product story.

  Step 19: Add Subtle Motion
  Files:

  - web/styles.css
  - web/app.js

  What changes:

  - Soft animated status movement.
  - Subtle line/pulse through workflow stages.
  - No excessive 3D, no distracting animation.

  Why:

  - Makes the product feel polished without becoming flashy.

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Phase 8: Product Polish

  Step 20: Badge And Color Polish
  Files:

  - web/styles.css

  What changes:

  - Softer pastel:
      - green for approve/safe
      - amber for review/missing info
      - red for reject/high risk
      - blue/gray for evidence/audit

  Why:

  - Keeps the current color scheme but makes it more premium.

  Step 21: Add Empty/Error States
  Files:

  - web/index.html
  - web/app.js
  - web/styles.css

  What changes:

  - Clear messages for:
      - no case selected
      - upload failed
      - parsing failed
      - OCR unavailable
      - no evidence found

  Why:

  - A paid-ready product should never fail silently.

  Step 22: Improve Mobile Layout
  Files:

  - web/styles.css

  What changes:

  - Ensure the main flow stacks cleanly on smaller screens.
  - Prevent text overlap.
  - Keep buttons readable.

  Why:

  - Recruiters may open it on laptop, tablet, or phone.

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Phase 9: Evaluation Proof

  Step 23: Compact Evaluation Table In README
  Files:

  - README.md

  What changes:

  - Add concise eval proof table:
      - Clean Invoice
      - Missing PO
      - Duplicate Risk
      - High-Value Approval
      - AR Follow-Up

  Why:

  - Shows this is tested, not just prompted.

  Step 24: Keep Eval UI Secondary
  Files:

  - web/index.html
  - web/styles.css

  What changes:

  - Evaluation remains visible but not dominant.
  - It supports credibility without making the page academic.

  Why:

  - Product first, proof second.

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Phase 10: Screenshots And Demo Assets

  Step 25: Refresh Screenshots
  Files:

  - docs/screenshots/*

  What changes:

  - New screenshots after UI polish:
      - main console
      - case detail
      - evidence panel
      - human review/audit
      - eval proof

  Why:

  - README should show the polished product.

  Step 26: Update Demo Walkthrough
  Files:

  - docs/showcase.md

  What changes:

  - Add final demo script:
      - what to click
      - what to point out
      - what story to tell

  Why:

  - Makes the project easy to present.

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Phase 11: Verification, Docs, Commits, Push

  Step 27: Run Checks
  Commands likely:

  - node --check web/app.js
  - backend compile/check
  - eval runner if available

  Why:

  - Avoid pushing broken frontend/backend.

  Step 28: DeepLearn Documentation
  Files:

  - learnings/* or project learning doc

  What changes:

  - Document what changed and why.
  - Capture design/product decisions.

  Why:

  - Required after significant feature/phase work.

  Step 29: Granular Commits
  Commit style:

  - README intro separately
  - README demo path separately
  - HTML structure separately
  - JS rendering separately
  - CSS visual polish separately
  - docs/screenshots separately

  Why:

  - You specifically want very granular commit history.

  Step 30: Push To GitHub
  Target:

  - GargiGupta-io/invoiceflow-ai

  Why:

  - GitHub should reflect the latest product-ready version.
