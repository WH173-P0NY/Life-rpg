# Campaign Studio - Make/n8n-style canvas redesign spec

Date: 2026-06-29

## Goal

Current Campaign Studio exposes too much interface at once: campaign library,
node palette, toolbar, canvas, inspector, and readiness panel can all be visible
at the same time. The next version must feel closer to workflow builders such as
Make and n8n: the canvas is the primary surface, nodes are compact and direct,
and secondary configuration appears only when the user asks for it.

This is a UX/frontend redesign spec. It should reuse the existing campaign API,
React Flow stack, node/edge contracts, validation endpoint, and persisted node
positions.

## Source Research

Sources checked:

- Make Help Center, "Create your first scenario":
  `https://help.make.com/create-your-first-scenario`
- Make Help Center, "Canvas interaction model":
  `https://help.make.com/canvas-interaction-model`
- Make Help Center, "Step 2. Add a router":
  `https://help.make.com/step-2-add-a-router`
- Make Help Center, "Step 4. Add a filter":
  `https://help.make.com/step-4-add-a-filter`
- Make Help Center, "Step 6. Add an aggregator":
  `https://help.make.com/step-6-add-an-aggregator`
- n8n Docs, "Nodes":
  `https://docs.n8n.io/workflows/components/nodes/`
- n8n Docs, "Connections":
  `https://docs.n8n.io/workflows/components/connections/`
- n8n Docs, "Sticky Notes":
  `https://docs.n8n.io/workflows/components/sticky-notes/`
- n8n Docs, "Canvas Groups":
  `https://docs.n8n.io/workflows/components/canvas-groups/`

Distilled patterns:

- Make presents a scenario as a chain of modules on a large canvas. Modules are
  icon-first circular items connected by paths. Routers split the flow into
  multiple routes, and filters live on the route between modules rather than as
  large always-visible panels.
- Make uses plus affordances on modules/routes and context actions directly on
  the canvas. The canvas interaction model explicitly supports pan, zoom,
  select, context menu, marquee selection, and device-specific mouse/trackpad
  behavior.
- n8n treats nodes as the primary building blocks. A connector/add-node affordance
  opens the node panel when extending an existing workflow, rather than keeping a
  full palette permanently visible.
- n8n connections route data from one node output to the next node input. Hover
  controls expose node operations only when relevant.
- n8n uses sticky notes and canvas groups to help users understand and collapse
  large workflows. These are useful follow-up patterns for large campaigns.

Do not copy Make or n8n branding, colors, icons, or exact component styling. Use
their interaction model as product reference, then fit it into the Life RPG UI.

## Current State

Current files:

- `frontend/src/components/campaigns/CampaignStudio.tsx`
- `frontend/src/components/campaigns/CampaignCanvas.tsx`
- `frontend/src/components/campaigns/CampaignNode.tsx`
- `frontend/src/components/campaigns/CampaignPalette.tsx`
- `frontend/src/components/campaigns/CampaignInspector.tsx`
- `frontend/src/components/campaigns/CampaignReadinessPanel.tsx`
- `frontend/src/components/campaigns/CampaignToolbar.tsx`

Main issue:

- `CampaignStudio` uses a three-column desktop layout:
  campaign list plus palette, toolbar plus canvas, and inspector plus readiness.
- The palette and inspector are always visible on wide screens, so the graph
  feels like one panel inside an admin screen rather than the product surface.
- Nodes are rectangular cards with several text rows. This makes the graph dense,
  visually heavy, and less like a workflow builder.
- Validation/readiness content is always near the graph, competing with the
  canvas even when the user is only trying to build or scan the flow.

## Product Direction

The redesigned Campaign Studio must prioritize:

1. Canvas first.
2. Compact nodes.
3. Direct manipulation.
4. Progressive disclosure.
5. Fast scanning of path, status, and branch rules.

The default screen must look like a workflow graph editor, not a dashboard made
of panels.

## Information Architecture

### Default Desktop Layout

Use a single workbench shell:

```text
CampaignTopBar
CampaignCanvas
CanvasStatusBar / toast layer
InspectorDrawer only when selected
NodePickerPopover only when adding
CampaignSwitcherPopover only when switching
ValidationDrawer only when requested
```

Requirements:

- The canvas must occupy the primary viewport area.
- Remove the permanent left campaign library from the default builder view.
- Remove the permanent node palette from the default builder view.
- Remove the permanent right inspector/readiness column from the default builder
  view.
- Use overlay drawers/popovers for secondary surfaces.
- Keep the top bar dense and functional: campaign switcher, status badge,
  builder/play segmented control, save/validate/publish actions, and overflow
  menu.

### Campaign Selection

Replace the permanent `CampaignListPanel` with a `CampaignSwitcher`.

Behavior:

- Top-left button shows current campaign title, status badge, and a dropdown icon.
- Opening it shows searchable campaigns, create campaign action, refresh action,
  and status filters.
- If no campaign exists, show a centered create/import state. Once a campaign is
  selected, hide the library again.

### Node Creation

Replace the permanent `CampaignPalette` with a `NodePickerPopover`.

Entry points:

- Click plus on an output connector.
- Click plus on an empty branch placeholder. In the first pass this still uses
  add-after-source semantics, not edge splicing.
- Double-click empty canvas.
- Press `A` while focus is on the canvas.
- Use top-bar "Add" command.

Picker behavior:

- Search-first.
- Shows available node types from `studio.availableNodeTypes`.
- Supports quick categories: Quest, Milestone, Gate, Reward, Reflection.
- Selecting a node creates it after the selected node output. If the picker was
  opened from an edge/route affordance in the first pass, it uses that edge's
  source node as the insertion source and does not splice the edge. If there is
  no source context, it creates near the viewport center.

### Inspector

Replace the permanent inspector column with an overlay drawer.

Behavior:

- Selecting a node opens `NodeInspectorDrawer` on the right.
- Selecting an edge opens `EdgeInspectorDrawer`.
- Pressing `Esc`, clicking empty canvas, or saving closes the drawer only when
  the drawer has no unsaved changes. Dirty drawers require explicit Save or
  Discard.
- On mobile, drawer becomes a bottom sheet.

Node drawer sections:

- Details: title, description, stage.
- Reward: XP amount and reward skill.
- Unlock: unlock mode, required node selector.
- Danger: delete.

Reward skill is part of the studio node contract in this pass. The API must
return `reward_skill_id` and `reward_skill` on studio/map node payloads whenever
a quest reward exists. The drawer and add-node flow may submit `rewardSkillId`
only when the user can see and intentionally choose the current reward skill.

Edge drawer sections:

- Source and target.
- Derived route summary.
- Delete connection.

The current edge contract contains only source and target node IDs. The first
pass must derive route details from the connected nodes, unlock mode, and
dependency direction. It must not offer editable route labels or condition
summaries until the API adds fields such as `edge.label` and
`edge.condition_summary`.

### Validation

Replace always-visible readiness with a compact validation indicator.

Behavior:

- Top bar shows `Ready`, `Needs work`, or `Draft` as a badge.
- Clicking the badge opens `ValidationDrawer`.
- Publish action runs validation first and opens the drawer if blocked.
- Validation messages should link/select the affected node when possible.

## Canvas Design

### Canvas Surface

Use a clean builder canvas:

- Full-width workbench area.
- Subtle grid or dotted grid.
- Minimal outer border; avoid framing the graph in a heavy card.
- React Flow controls stay available but visually quiet.
- MiniMap is collapsed by default on simple campaigns and available through a
  canvas option when node count exceeds a threshold, for example 12 nodes.

### Node Shape

Use Make-inspired compact module nodes.

Default node:

- Circular or soft-square icon-first module, 72-88 px main body.
- Label below the module, max two lines.
- Status badge attached to top-right or bottom-right of the module.
- Reward XP shown only as a small badge, not a full row.
- Description is hidden by default and visible in drawer or hover preview.

Node states:

- Locked: muted border and lock badge.
- Available: active accent ring.
- Completed: success badge and toned-down filled accent.
- Invalid: warning badge and red/orange outline.
- Selected: strong focus ring.

Node kinds:

- Start: distinct trigger/start icon.
- Quest: task/shield icon.
- Milestone: milestone icon.
- Gate: router/split icon.
- Reward: gem/trophy icon.
- Reflection: note/pen icon.
- End: finish/trophy icon.

### Router / Gate Design

Gate nodes should visually read like Make routers:

- Circular split icon.
- Multiple outgoing routes fan out from the right side.
- Each outgoing route can show a small derived label pill, for example the target
  node title, required/optional state, or unlock mode.
- Empty branch ends display a plus module placeholder.

Campaign semantics:

- Gate node maps to existing `gate` node kind.
- Route label is derived from dependency/unlock semantics in the first pass.
- Later filter logic can be added without changing the base canvas interaction.

### Edges

Use workflow-style connectors:

- Builder mode: dotted or lightly segmented edge with plus affordance on hover.
- Play/read mode: solid edge with status color.
- Arrow direction must remain clear.
- Hovering an edge reveals compact controls. In the first pass, controls are
  limited to add-after-source and delete.
- Edge labels are derived and read-only in the first pass. They should be short
  and only visible for branches or non-default dependencies.
- Editing route labels or filter/condition summaries is a later contract change.

## Interaction Model

Canvas navigation:

- Pan with current React Flow behavior plus documented shortcuts:
  middle mouse / space + drag / trackpad pan.
- Zoom with wheel or pinch.
- Select node/edge with click.
- Multi-select with marquee drag.
- `Esc` clears selection and closes overlays.

Node controls:

- Hovering a node reveals a small action ring or floating toolbar:
  add next, connect, delete, more.
- Double-click opens inspector.
- Drag moves node and persists via existing position endpoint.
- Delete key deletes selected node/edge in builder mode only.
- Duplicate is out of scope for the first pass because the current API contract
  does not define what should happen to copied edges, reward skill identity, or
  node positions.

Add flow:

1. User clicks plus on a node output.
2. `NodePickerPopover` opens anchored near the plus.
3. User searches/selects a node kind.
4. New node appears connected after the source node.
5. Inspector opens only if the node needs required fields.

First-pass edge insertion rule:

- Adding from a node output uses a richer frontend callback than the current
  `onAddNode(kind)` shape:

```ts
type CampaignAddNodeRequest = {
  kind: CampaignNodeKind;
  sourceNodeId?: string;
  sourceEdgeId?: string;
  viewportPosition?: { x: number; y: number };
};
```

- If `sourceNodeId` is present, the mutation creates a node and then creates one
  edge from the source node to the new node.
- If `viewportPosition` is present and no source is present, the mutation creates
  an unconnected node at that viewport position.
- If neither is present, the mutation creates an unconnected node near the
  viewport center using the existing collision-aware open-position resolver.
- The first pass implementation must update the callback chain from picker to
  `CampaignsView` so node creation can carry `sourceNodeId`, `sourceEdgeId`, and
  `viewportPosition` context. Keeping only `onAddNode(kind)` is insufficient for
  connected add-from-node behavior.
- Mutation sequence for connected add-from-node:
  create node, create edge from source to new node, refresh studio state. If edge
  creation fails after node creation, refresh studio state and show a recoverable
  error instead of leaving optimistic local edges.
- Adding "on route" must behave as add-after-source in the first pass. It must
  not splice an existing edge into `source -> new -> target` unless the
  implementation uses the existing `PUT /api/campaigns/<id>/edges/` replacement
  endpoint with a documented rollback strategy.
- If route splicing is implemented later, the safe mutation sequence is:
  create node, create source-to-new dependency, replace the original
  source-to-target dependency with new-to-target through `PUT /edges/`, then
  refresh studio state. If any step fails, refresh from server and show the
  validation/error state instead of leaving optimistic local edges.

Drawer dirty-state rule:

- Inspector forms use a local dirty buffer.
- Clicking empty canvas or pressing `Esc` closes a clean drawer immediately.
- If the drawer is dirty, closing requires either explicit Save or explicit
  Discard.
- Saving calls the existing node update endpoint and refreshes the studio state.
- Autosave is out of scope for the first pass.

Selection flow:

1. User selects a node.
2. Node receives selected ring.
3. Drawer opens with node details.
4. Canvas remains visible and usable.

Validation flow:

1. User clicks Validate or Publish.
2. API validation result updates badge.
3. If blocked, drawer opens with grouped issues.
4. Clicking an issue centers/selects the node or edge.

## Responsive Behavior

Desktop:

- Top bar + full canvas.
- Right overlay drawer for inspector/validation.
- Popovers for campaign switcher and node picker.

Tablet:

- Same canvas-first layout.
- Inspector drawer may cover 40-55% width.
- Top bar actions collapse into icon buttons and overflow menu.

Mobile:

- Canvas remains first screen.
- Top bar uses compact campaign selector and overflow menu.
- Inspector and validation are bottom sheets.
- Node picker is a full-screen command sheet.
- Avoid three stacked panels above the canvas.

## Component Plan

New or heavily changed components:

- `CampaignWorkbench`
  - Owns top bar, canvas, drawers, popovers, and selection state.
- `CampaignTopBar`
  - Campaign switcher entry, mode segmented control, validate, publish, run/play,
    overflow actions.
- `CampaignSwitcher`
  - Searchable campaign list and create action.
- `NodePickerPopover`
  - Search-first add-node surface using `availableNodeTypes`.
- `NodeInspectorDrawer`
  - Replaces always-visible node inspector.
- `EdgeInspectorDrawer`
  - Replaces always-visible edge inspector.
- `ValidationDrawer`
  - Replaces always-visible readiness panel.
- `CanvasStatusBar`
  - Zoom, node count, validation status, pending/save indicators.
- `WorkflowModuleNode`
  - Replaces current rectangular `CampaignNode` styling.

Existing components to retire or make internal:

- `CampaignListPanel` becomes implementation detail of `CampaignSwitcher` or is
  removed.
- `CampaignPalette` is replaced by `NodePickerPopover`.
- `CampaignInspector` is split into node drawer and edge drawer.
- `CampaignReadinessPanel` becomes drawer content.
- `CampaignToolbar` becomes `CampaignTopBar`.

## API and Data Contract

No backend model changes are required for the first redesign pass.

Reuse:

- `GET /api/campaigns/`
- `POST /api/campaigns/`
- `GET /api/campaigns/<id>/studio/`
- `POST /api/campaigns/<id>/nodes/`
- `PATCH/DELETE /api/campaigns/<id>/nodes/<node_id>/`
- `POST /api/campaigns/<id>/edges/`
- `DELETE /api/campaigns/<id>/edges/<edge_id>/`
- `PUT /api/campaigns/<id>/edges/`
- `PATCH /api/campaigns/<id>/nodes/positions/`
- `POST /api/campaigns/<id>/validate/`
- `POST /api/campaigns/<id>/publish/`

First-pass data additions:

- `node.reward_skill_id`
- `node.reward_skill`

Optional later data additions:

- `edge.label`
- `edge.condition_summary`
- `canvas_group`
- `node.note`
- `node.collapsed`

Do not add these in the first pass unless the existing API already supports them
or the implementation truly needs them.

First-pass frontend callback contract:

```ts
type CampaignAddNodeRequest = {
  kind: CampaignNodeKind;
  sourceNodeId?: string;
  sourceEdgeId?: string;
  viewportPosition?: { x: number; y: number };
};
```

`CampaignWorkbench`, `NodePickerPopover`, and `CampaignsView` must pass this
request object through the add-node path. The implementation may still call the
existing `POST /nodes/` and `POST /edges/` endpoints internally, but the UI
callback must not remain `onAddNode(kind)` because it cannot represent connected
node creation.

## Implementation Order

1. Add this spec and align copy keys.
2. Create `CampaignWorkbench` shell and move current `CampaignStudio` state into
   it without changing API behavior.
3. Replace the three-column grid with canvas-first layout.
4. Build `CampaignTopBar` and `CampaignSwitcher`.
5. Replace fixed palette with `NodePickerPopover`.
6. Restyle nodes into compact module nodes.
7. Add node-output plus controls and derived edge labels where data exists.
8. Split inspector into node/edge drawers.
9. Move readiness into `ValidationDrawer`.
10. Add responsive bottom-sheet behavior for mobile.
11. Update QA checklist and run frontend verification.

## Acceptance Criteria

Layout:

- Campaign Studio opens to a canvas-first interface.
- On desktop, no permanent left library, permanent node palette, or permanent
  right inspector is visible by default.
- Canvas occupies most of the available workbench.
- Existing campaign selection, node creation, edge creation, node editing,
  deletion, validation, publish, archive, AI draft, and mode switching remain
  reachable.

Canvas:

- Nodes are compact, icon-first modules with labels.
- Gate/router nodes visually support branching.
- Edges show direction clearly.
- Add-node actions are available directly from node output controls.
- Edge plus controls in the first pass add after the source node unless route
  splicing is implemented with the documented `PUT /edges/` sequence.
- Hover controls do not resize nodes or shift the graph layout.
- Dragging nodes still persists positions.
- Nodes must not overlap after initial studio load, add-node, auto-layout, or
  drag-stop.
- Hover controls, badges, labels, and selected states must not change node
  footprint in a way that creates overlap.
- The redesign must update collision geometry in `campaignLayout.ts` or replace
  it with a measured geometry strategy that matches the new compact module node
  footprint.
- Manual QA must check overlap with 3, 10, and 30 nodes.

Inspector:

- Node and edge settings open only after selection or explicit edit.
- Dirty drawer state cannot be lost through `Esc` or canvas click without an
  explicit Save or Discard action.
- Reward skill editing is shown because the studio node API exposes current
  reward skill identity.
- Creating a quest node supports choosing reward skill and XP before submit.
- Saving a node must not submit an empty `rewardSkillId` that clears an existing
  reward skill unless the user intentionally selected no reward skill and set XP
  to `0`.
- Edge label/condition editing is not shown in the first pass unless the edge API
  exposes those fields.
- Mobile uses bottom sheets instead of stacked panels.

Validation:

- Validation state is visible as a top-bar/status badge.
- Detailed validation appears only on request or failed publish.
- Validation issue click centers/selects the affected graph item when possible.

Quality:

- `npm --prefix frontend run typecheck` passes.
- `npm --prefix frontend run build` passes.
- Existing backend API tests should remain unchanged unless a contract change is
  explicitly introduced.
- Manual QA confirms create, edit, connect, delete, validate, publish, and
  mobile layout flows.

## Out of Scope

- Backend campaign model redesign.
- AI campaign generation changes.
- ActivityWatch integration.
- Full Make/n8n feature parity.
- Copying Make or n8n visual identity.
- Advanced canvas groups, sticky notes, and route filters beyond existing
  campaign dependency semantics. These can be future enhancements.

## Open Questions

- Should campaign `gate` nodes be renamed in UI to `Router` for users, while
  keeping backend `gate` unchanged?
- Should play mode show completion simulation or only read-only status?
- Should edge labels be persisted now, or derived from existing unlock/dependency
  state until route conditions exist?
- Should the MiniMap appear only after a node threshold, or stay as a user
  preference in canvas options?
