# Phase 15H: Product Path Rail

> The six-step workflow rail now lives inside the Product Path section, directly under the “One readable route” heading.

---

## In Plain English

The page had two product-path explanations: the visual workflow rail near the top and the Product Path section lower down with chips and a paragraph. That repeated the same idea in two different styles.

This update moves the visual rail into the Product Path section and removes the extra chips and paragraph. Now the section is simpler: heading first, workflow rail second.

## What Changed

### Moved Workflow Rail

Plain English: the visual path now appears where the Product Path heading is.

The `workflow-orbit` block moved from the hero area into the `manifesto-band` section.

### Removed Extra Copy

Plain English: the section no longer explains the path twice.

The old path chips and paragraph were removed:

- Select or upload
- Extract facts
- Check policy
- Detect risk
- Recommend action
- Save audit trail

The rail now carries that job visually.

## Verification

- `node --check web/app.js` passed.
- Local `/ui` served successfully.
- There is one `workflow-orbit` in `web/index.html`.
- Backend and workflow behavior were not changed.

## Updates

### 2026-07-01 - Product Path Became The Workspace Navigation

Plain English: the page used to have a visual product path and then a separate tab row below it. That made the viewer ask, "Are these two different things?" The answer was no: both were trying to control the same mental model. The Product Path is the route through the workflow, and the workspace tabs are the places where the user inspects that route.

The fix was to merge them. The Product Path section now has four clickable stages:

- `Case Summary` - covers invoice intake and extracted facts.
- `Evidence` - covers policy retrieval and risk/anomaly reasoning.
- `Review` - covers the recommendation, human gate, and audit trail.
- `Evaluation` - covers quality checks and reliability proof.

This keeps the original six-step story, but groups it into four readable screens. A user does not need to decide whether to use the path or the tabs. The path is the navigation.

### Why Four Stages Instead Of Six

Plain English: six small labels looked like a timeline, but four larger choices work better as clickable destinations.

The six-step route still exists conceptually:

1. Invoice
2. Extract
3. Policy
4. Risk
5. Decision
6. Audit

The UI now groups those into the actual views:

1. `Invoice + Extract` becomes `Case Summary`.
2. `Policy + Risk` becomes `Evidence`.
3. `Decision + Audit` becomes `Review`.
4. Quality checks become `Evaluation`.

This is easier because the user sees both the product path and the screen purpose in one place.

### Header Highlight Behavior

Plain English: the top header should not glow on a workspace tab while the user is still looking at the hero. That made the page feel like it was already inside the decision section before the user had chosen anything.

The header now tracks page position:

- Near the hero, `Overview` is active.
- Near the sample launcher, `Cases` is active.
- Near the workflow area, the selected workspace view is active.

This makes the header behave like a site map, while the Product Path rail behaves like the workflow switcher.

### Upload Helper Text

Plain English: the upload support sentence was visually too loud for something that is only a small note.

The line now uses a smaller font and lighter treatment. It still tells users what files work and why scanned PDFs may need a text fallback, but it no longer competes with the upload controls.

### Files Updated

- `web/index.html` - removed the separate lower tab row and added the merged Product Path navigation cards.
- `web/styles.css` - added the Product Path card styling, active state, responsive layout, and smaller helper note style.
- `web/app.js` - added header state synchronization and workspace scrolling when a workflow view is selected.

### Beginner Test

Plain English: a beginner should now understand that the page has one route through the workflow:

1. Choose or upload a case.
2. Open Case Summary to see what was extracted.
3. Open Evidence to see why the decision is grounded.
4. Open Review to see the human action and audit trail.
5. Open Evaluation to see quality proof.

The main improvement is that the UI no longer asks the viewer to interpret two competing navigation rows.
