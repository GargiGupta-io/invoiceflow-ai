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

