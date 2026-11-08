/* web/assets/js/trace.js — the trace: the words as they arrive, and the faces they grow until the record
   lands.

   The transcript is the one region that cannot afford to be rebuilt per arriving frame — a live run's
   trace arrives at sixty frames a second, and a surface rebuilt for each of them is a main thread that
   never stands down — so the arriving frames are buffered into one animation frame, and that frame pays
   for what it carried: a step the record settled is the whole surface rebuilt, and a trace fragment is
   the in-flight row grown where it stands. The frame's work is proportional to what arrived, not to the
   length of the transcript it arrived beside.

   The module stands the faces the trace grows until the record lands — the in-flight row, the
   reasoning's face beside it, the header the page's word stands in, and the rows the tree wears while
   the record stands — and the settle that takes them away when the record lands.

   The render the pane the live surface owes stands here too — `renderChat`, the whole surface rebuilt
   when a step settles — and with it the standing the render resets: `standingRow` and its boxes,
   `standingInfoPanel` the transcript stands, and `ticking` the row the tick keeps. And `treeRendered`,
   the mark that a tree has been drawn at all, stands here because `renderTree`, the one place a tree
   is drawn, stands here. A write of a name stands in the room where the write stands, and a write
   crosses no module, so a standing two rooms write stands in the room of the render that pays for it.
   */

import { nodes, state } from './state.js';
import {
  REASONING_GLYPH, UNFOLD_GLYPH, FOLD_GLYPH, el, badge, workingMark, rowWorking,
  workspaceLabel, shortRunId
} from './components.js';
import { closeMenu } from './menus.js';
import {
  emptyState, infoPanel, placeInfoPanel, references, resultBlock, rowActor, rowType,
  segmentRow, standKeptPlace, transcriptSegments
} from './transcript.js';
import { bubble } from './reading.js';
import { clockSpan, forkWords, keepClocks, runRow, workspaceRow } from './tree.js';
import { runWorks } from './composer.js';

export let ticking = [];
// Whether the tree has been drawn at all: the first listing must render whatever it answers — even
// nothing, which is the face the page owes for an empty tree — while a later listing that answers the
// rows already drawn is not redrawn. `renderTree` is the one place a tree is drawn, so it sets this.
export let treeRendered = false;
export let standingInfoPanel = null;
/** Take the line away from the document it is hung on. The render that owes it nothing is the render
 * that takes it — the render's head clears the standing, and nothing stands of the line but the state.
 */
export function closeInfoPanel() {
  if (!standingInfoPanel) return;
  standingInfoPanel.remove();
  standingInfoPanel = null;
}
export function renderChat() {
  closeInfoPanel();
  nodes.messages.replaceChildren();
  ticking = [];   // the rows below are the ones standing now, and the tick follows them
  // …and so are the faces the trace grows: what stands is what this pass stood, and a frame that grows a
  // word looks for it here and finds either this surface's row or no row at all.
  standingRow = null;
  standingBoxes.clear();
  const segments = transcriptSegments(state.steps);
  if (!segments.length) {
    nodes.messages.appendChild(emptyState(
      state.run ? 'Nothing said yet' : 'S ╱─╲ H',
      state.run ? 'The transcript fills as the run answers.' : 'Pick a run on the left, or start one below.',
      state.run ? '' : 'sahw-empty__mark'));
  }
  // The pane shows the conversation in force, not the whole file: the stretch a cut detached is the
  // record's — kept in the log, never in a conversation again, the cut's own marker says so — and it
  // owes the pane no lines. The markers are what stand: a cut the run stands on at full weight, a cut
  // a later cut superseded in the quiet ink, still saying what it tried to do.
  for (const segment of segments) {
    if (segment.detached && !(segment.role === 'marker' && segment.marker === 'cut')) continue;
    nodes.messages.appendChild(segmentRow(segment));
  }
  // The turn being written, after everything the record has settled and before the run's own heartbeat:
  // the word and the thought are the run's newest, and the faces are the model's row. Null for every
  // stream that carries no trace, which is every run started without SAH's `--live`.
  const inflight = proseInFlight();
  const thinking = reasoningInFlight();
  if (inflight || thinking) nodes.messages.appendChild(inflightRow(inflight, thinking));
  if (state.notice) nodes.messages.appendChild(el('div', 'sahw-marker', state.notice));
  // The marker is the run's own heartbeat: it exists while a writer holds the log — the stream
  // following it, or a follow this page started that has not reached the record yet — and the `ended`
  // frame is what takes it away. A settled run is not writing, so it owes no marker of its own: the last
  // line of the record is where it stopped, and the face has nothing to add beneath it.
  if (runWorks()) {
    const beat = el('div');
    beat.setAttribute('aria-busy', 'true');
    beat.appendChild(el('span', 'sahw-spinner sahw-spinner--sm'));
    nodes.messages.appendChild(beat);
  }
  // Nothing is asked of the pane's engine for the rows that arrived above: it watches the surface it
  // stands on, and they are the layout change it wakes on. The one thing this render does ask of it is
  // the reader's own place, when the page has just opened a run whose place the reader left elsewhere —
  // asked through the act the engine keeps the pane by, once, and never by hand.
  keepClocks();
  standKeptPlace();
  // The line the mark holds, floating where the mark stands: the rows have stood by now, so the mark
  // the line stands for has its standing, and the line takes its place beside it without moving the
  // words it stands above.
  const openSegment = state.infoOpen ? segments.find((one) => one.id === state.infoOpen) : null;
  if (openSegment) {
    const openRow = [...nodes.messages.children].find((one) => one.dataset && one.dataset.sahwMessageId === state.infoOpen);
    const openMark = openRow ? openRow.querySelector('.sahw-info') : null;
    if (openMark) {
      const panel = infoPanel(openSegment, openSegment.role === 'model');
      if (panel) {
        document.body.appendChild(panel);
        standingInfoPanel = panel;
        placeInfoPanel(panel, openMark);
      }
    }
  }
}

/* --- the trace: the words as they arrive, and the faces they grow until the record lands ----------------

   The stream carries two kinds of frame. The record's steps, as it always did; and the run's trace —
   SAH's `live.jsonl`, the model's prose and a streaming tool's output fragment by fragment, each one a
   fact the finished step will also hold. A fragment is a word still being written, so the pane grows a
   face from it and hands that face over to the step which settles it: `state.partials` holds what is on
   the screen and nothing else, and every entry in it is owed to a step that is coming.

   The three faces are the faces the pane already owes, plus the face the reasoning owes. The
   in-flight thought is the turn's own word still being thought: the face it stands in grows above the
   face the word the turn speaks stands in, because the reasoning the turn thinks stands before the
   word the turn speaks — a turn that thinks and speaks stands the two faces, and the one does not
   swallow the other, and a turn that speaks nothing but thinking stands the thinking. The in-flight
   turn is the model row that turn will be, wearing the working clock an in-flight call already wears
   and rendering through the bubble it settles into — an opened fence stands as a growing block, because it is the same bubble. The in-flight
   answer is the result box its call owes, under the same cap and wearing the same file mark, because the
   file a `write` is writing is a file this page can show mid-write. What changes at settlement is whose
   words the face holds, not what the face is.

   Settlement is by identity where identity stands in the record, and by position where none does. A tool
   fragment names the tool-call id its `call` step recorded under `call_id`; the answer that settles it
   names that same step in its `refs`, so the box is found again from either side. A prose fragment names
   nothing — the agent is sequential, one prose turn is in flight at a time, and the place a word grows is
   the end of the transcript — so the next assistant `message` step settles it. A reasoning fragment
   names nothing either: the thought owes the turn in flight, the way the word does, and the next
   assistant `message` step settles it — the step that carries the turn's reasoning field is the step
   that settles the face the thought grew into, and the settled thought stands the quiet line its kind
   is owed in the record's row, above the word it stood above. A fragment can still reach
   the pane after its own step: the route drains the trace after the record's frames of each poll, so the
   tail of a turn may arrive on the far side of the line that finished it. Such a fragment grows nothing
   you would call a turn in flight — see `proseInFlight` and `reasoningInFlight` — and the record's text is what stands. */

/** Empty the in-flight faces: their steps landed, the stream on which they arrived is over, or the run
 * they belonged to is no longer the run open on the screen. */
export function clearPartials() {
  state.partials = { prose: null, tools: new Map(), reasoning: null };
}

/* What the pane holds of the faces the trace grows, so that the frame a fragment brings can find the
   words it grew: `standingRow` the row the turn being written stands in — its content, the two faces
   stood under its clock, and the words each of them stands — and `standingBoxes` one entry per call the
   last rebuild drew with no answer yet, holding the box its arriving answer stands in when a box stands
   and the words that box stands.

   Both are the rebuild's own work: it stands them, it records them here as it stands them, and it clears
   them with the surface it replaced, which is why a frame that grows a face never has to ask whether what
   it holds is on the page — either it is, or the rebuild that took it away refilled the holding with what
   stands now. They are held for one reason: a `delta` is a word, and the frame it schedules owes the pane
   that word's own face and none of the record the word did not change. */
export let standingRow = null;
export const standingBoxes = new Set();

/** The call step a tool fragment belongs to: the fragment carries the tool-call id the model minted, and
 * the record wrote that id into the `call` step before the tool ran, so the step stands in the log before
 * any fragment that needs it. A fragment whose call the pane has not read is held under the id it came
 * with rather than dropped — a row not drawn yet is a row that will want the words. */
export function callStep(toolCallId) {
  for (let at = state.steps.length - 1; at >= 0; at -= 1) {
    const step = state.steps[at];
    if (step.kind === 'call' && step.call_id === toolCallId) return step;
  }
  return null;
}

/** One fragment, grown into the face it belongs to. A line the pane cannot read, an empty fragment, and a
 * kind the writer does not send are all passed over: the trace is a courtesy, and a pane that failed on a
 * word it did not understand would lose the record with it. */
export function applyDelta(delta) {
  if (!delta || typeof delta.text !== 'string' || !delta.text) return;
  const stamp = typeof delta.ts === 'string' ? delta.ts : '';
  if (delta.kind === 'reasoning') {
    // The turn's own thought: it grows the face the turn is thinking in, and it owes no call, because
    // the reasoning a turn thinks is not the output of a call, and a line that carries a call is a line
    // the output of the call it names stands in. The step that settles it is coming, the way the one
    // for the prose is coming.
    if (state.partials.reasoning) state.partials.reasoning.text += delta.text;
    else state.partials.reasoning = { text: delta.text, ts: stamp };
    return;
  }
  if (delta.kind !== 'delta') return;
  if (typeof delta.call !== 'string' || !delta.call) {
    if (state.partials.prose) state.partials.prose.text += delta.text;
    else state.partials.prose = { text: delta.text, ts: stamp };
    return;
  }
  const call = callStep(delta.call);
  const key = call && call.id ? call.id : delta.call;
  const held = state.partials.tools.get(key);
  if (held) held.text += delta.text;
  else state.partials.tools.set(key, { text: delta.text, ts: stamp });
}

/** The step that settles: an assistant turn's `message` clears the prose and the thought that grew
 * into it, and a `result` clears the answer that grew into the call it answers. The step is already
 * the pane's truth; the partial is display state that owes the reader nothing once the step it grew
 * towards stands — and the line the thought settles into stands in the record's row, from the step's
 * own reasoning field, which a step that owes no reasoning does not carry. */
export function settleStep(step) {
  if (step.kind === 'message') {
    if (step.role !== 'user') {
      state.partials.prose = null;
      state.partials.reasoning = null;
    }
    return;
  }
  if (step.kind !== 'result') return;
  for (const id of references(step)) {
    state.partials.tools.delete(id);
    // …and the key of a fragment that arrived before the row it belongs to, which is the tool-call id the
    // call step carries beside its own.
    for (let at = state.steps.length - 1; at >= 0; at -= 1) {
      const call = state.steps[at];
      if (call.kind === 'call' && call.id === id) {
        if (typeof call.call_id === 'string') state.partials.tools.delete(call.call_id);
        break;
      }
    }
  }
}

/** The prose still arriving, or null when there is no turn in flight: nothing has grown, or the record's
 * last word is the assistant turn this prose belongs to. A transcript that ends on an assistant message
 * has no turn in flight at the end of it, whatever the trace still holds under it — those are the words
 * of the turn the record has just closed, and the settled bubble above is where they belong now. */
export function proseInFlight() {
  const partial = state.partials.prose;
  if (!partial || !partial.text) return null;
  for (let at = state.steps.length - 1; at >= 0; at -= 1) {
    const type = rowType(state.steps[at]);
    if (!type) continue;
    return type === 'text' && rowActor(state.steps[at]) === 'model' ? null : partial;
  }
  return partial;
}

/** The thought still arriving, or null when there is no thought in flight: the same positional debt
 * the prose owes — nothing has grown, or the record's last word is the assistant turn this thought
 * belongs to. A transcript that ends on an assistant message has no turn in flight at the end of it,
 * whatever the trace still holds under it — those are the words of the turn the record has just
 * closed, and the quiet line its reasoning settled into is where they belong now. */
export function reasoningInFlight() {
  const partial = state.partials.reasoning;
  if (!partial || !partial.text) return null;
  for (let at = state.steps.length - 1; at >= 0; at -= 1) {
    const type = rowType(state.steps[at]);
    if (!type) continue;
    return type === 'text' && rowActor(state.steps[at]) === 'model' ? null : partial;
  }
  return partial;
}

/** The row a turn in flight earns: the model's row, the working clock stamped from the turn's first
 * fragment, and the faces it will settle into. No line over it: the line the turn will wear — the
 * name, the moment, the numbers — stands with the turn that settles, under the mark that holds it,
 * and the container it stood in is gone. What the in-flight row keeps is what no mark holds: the
 * working clock, a bare span at the head of the words' own flow — the count the words standing are.
 * `sahw-inflight` styles nothing — it is the name the row is asked by, for a reader of the document
 * who wants to know which words the record has not settled yet.
 *
 * The row is stood once, here, and grown after that: it is recorded as what stands (see `standingRow`)
 * at the one moment it is made, with no words recorded on it yet — which is what makes the first
 * growing the whole of them and every growing after it one face at a time. */
export function inflightRow(prose, thinking) {
  const row = el('div', 'sahw-message sahw-inflight');
  const content = el('div', 'sahw-message__content');
  const first = [prose, thinking]
    .filter((one) => one && typeof one.ts === 'string' && one.ts)
    .map((one) => one.ts).sort()[0] || '';
  // The clock is stood with the row and not grown with the faces: the moment it counts from is the turn's
  // first fragment's, and the second it says is the tick's to write. Growing it would be the row's own
  // work over again and the tick's list doubled, and neither is what a arriving word owes.
  const clock = clockSpan({ ts: first }, runWorks());
  if (clock) content.appendChild(clock);
  row.appendChild(content);
  standingRow = { row, content, thought: null, word: null, thinking: '', prose: '' };
  growFaces(prose, thinking);
  return row;
}

/** The two faces the turn being written stands, grown where they stand: the thought the turn is thinking,
 * above the word the turn is speaking, both under the clock the row was opened with. Only the face whose
 * words moved is built again, and it is built by the builder the rebuild would have used over the words
 * now held, and set down in the place the face it replaces stood — the row growing its own text, and every
 * settled row about it standing where it stands. The words each face is recorded with are how the next
 * frame knows whether it carried this face's. */
export function growFaces(prose, thinking) {
  const stood = standingRow;
  const thought = thinking ? thinking.text : '';
  const word = prose ? prose.text : '';
  if (thought !== stood.thinking) standFace('thought', thinking ? reasoningFace(thought) : null);
  if (word !== stood.prose) standFace('word', prose ? bubble({ text: word }, true) : null);
  stood.thinking = thought;
  stood.prose = word;
}

/** One face of the turn being written, stood under its clock in the order the turn owes it: the thought
 * before the word it stands above, the word at the end of the row's own flow. A face already standing
 * gives its place to the face built from the words now held; a face that has begun to stand is put before
 * the word it stands under, or at the end when no word stands yet. */
export function standFace(name, built) {
  const stood = standingRow;
  const held = stood[name];
  if (held) {
    if (built) held.replaceWith(built);
    else held.remove();
    stood[name] = built;
    return;
  }
  if (!built) return;
  stood[name] = built;
  stood.content.insertBefore(built, name === 'thought' ? stood.word : null);
}

/** The answer a call is still getting, in the box its answer will occupy, or null when the call has no
 * words on the way. Keyed by the call step's id, and beside it by the tool-call id — the two names are
 * the same fact seen from either side of the record, and a fragment arrives before the pane has read the
 * step that would give it the first of them only when the row and the fragment reach the screen together. */
export function inflightResult(call) {
  const held = state.partials.tools.get(call.id)
    || (typeof call.call_id === 'string' ? state.partials.tools.get(call.call_id) : null);
  return held && held.text ? held : null;
}

/** The face the reasoning owes, in flight and settled alike: the face's own quiet shape — the face's
 * own class, the theme's own muted word, the face's own glyph a word that stands thinking wears — and
 * the record's words standing whole. The shape is the quiet line the notices and the seams wear, and
 * no other: no ground the theme does not stand, and no language the words stand in, because the word
 * the model thinks is not the prose a sheet owes its fences to — it stands plain in the theme's own
 * ink, the newlines the record holds standing as the newlines the record holds.
 *
 * The word the model thinks is never withheld. The cap the pane owes a long tool result — the first
 * two hundred lines and the asking that names what it cut — is the result's discipline, and it does
 * not reach the model's own words: a thought stands whole, whatever length the turn thinks it, and
 * the pane's own scroll is the room a long thought stands in. A frame that arrives while the face
 * stands grows the face with it, the way the in-flight prose grows; a turn that owes no reasoning
 * owes no face and no line at all: the face is built only when the words stand. */
export function reasoningFace(text) {
  // The thought stands in the word's own shape: the bubble's frame and padding, the face's own
  // text, on the theme's own surface — the ground the word stands on. The ground is the theme's
  // own token, and the face's sheet loads after the catalog's, so at the equal specificity the
  // cascade does the work; the line needs no override of its own.
  const face = el('div', 'sahw-reasoning sahw-bubble sahw-bubble__content sahw-text');
  const line = el('div', 'sahw-reasoning__line');
  line.appendChild(el('span', 'sahw-reasoning__glyph', REASONING_GLYPH));
  line.appendChild(el('span', 'sahw-reasoning__text', text));
  face.appendChild(line);
  return face;
}

/** The frame a trace fragment scheduled, served out of the faces it grew and nothing else: the turn being
 * written, grown in its own row, and the answers still arriving, grown in the boxes their calls owe them.
 * The settled rows, the marker, the clocks and the open segment's place stand as the last rebuild stood
 * them, because a fragment of the turn being written is none of their facts — and the pane's own engine
 * wakes on the layout this growth makes the way it wakes on a rebuild's, since it watches the surface it
 * stands on and not the pass that changed it.
 *
 * It answers `true` when the growth moved a shape the rebuild reads — the turn's row needing to stand where
 * none stands, a call's arriving answer needing the box its row does not hold — because a row's shape is
 * the rebuild's to stand, and that one occasion the frame gives back. It answers `false` when the pane
 * stands right as it stands, which includes the frame that carried nothing the pane shows: a turn the
 * record has just closed, a fragment whose call the pane has not drawn, a run this pane stopped watching.
 * `false` is the frame that rebuilds nothing at all. */
export function growTrace() {
  const prose = proseInFlight();
  const thinking = reasoningInFlight();
  // The row's own presence is a shape fact: it stands between the record's last row and the marks under
  // it, and standing up or standing down is the rebuild's to order. Growing the words inside a row that
  // stands is not.
  if (Boolean(standingRow) !== Boolean(prose || thinking)) return true;
  if (standingRow) growFaces(prose, thinking);
  return growBoxes();
}

/** The answers still arriving, grown into the boxes their calls owe them, where the boxes stand. A box
 * with nothing left held for it is left to the step that settled it — the `result` that cleared the
 * partial is the frame that owes the row rebuilt, and it is a step, so that frame is on its way. A call
 * the rebuild drew with no answer and no words on the way has its entry from the moment it was drawn, so
 * an answer beginning to arrive for a row already standing is the box standing up — the row's shape, and
 * the rebuild's occasion. A fragment for a call no row of this pane's was drawn for grows nothing here at
 * all: its words wait in `state.partials` for the row the record has not settled yet. */
export function growBoxes() {
  let owed = false;
  for (const stood of standingBoxes) {
    const held = inflightResult(stood.call);
    if (!held) continue;
    if (!stood.box) {
      owed = true;
      continue;
    }
    if (held.text === stood.text) continue;
    const box = resultBlock({ content: held.text }, stood.touch);
    stood.box.replaceWith(box);
    stood.box = box;
    stood.text = held.text;
  }
  return owed;
}

// --- the renderers ------------------------------------------------------------------------------

export function renderHeader() {
  nodes.badges.replaceChildren();
  if (!state.run) return;
  // The header wears no word for the model: the model is the composer's own, and the header owes the
  // run no mark of its state either — the working mark is the tree's, standing with the rows it
  // corrects and the head that says so. What it owes the run is the carried conversation, spelled out
  // here where the header has the room the sidebar has to spend as a glyph: the run it was forked from
  // and the step the prefix ended at, the same sentence the row's hover holds. A run that began as its
  // own run wears nothing of it.
  const carried = forkWords(state.run);
  if (carried) {
    const mark = badge(carried.badge, 'gray');
    mark.classList.add('sahw-fork-badge');
    mark.title = carried.hover;
    nodes.badges.appendChild(mark);
  }
}

/* The rows the tree holds: the workspaces with their runs, or — while the operator is looking at the
   shelf — the workspaces that hold archived runs and only those runs. A run's archived state is a fact
   about this view and never about the run: hiding one opens nothing, moves nothing and writes nothing
   to the runs root, which is the record and stays as it is.

   The head's filter is a hand over these rows and nothing else: a workspace stands while its own name —
   the folder's last word, the one the row wears — holds the text, and a run stands while its own name does.
   A workspace that stands only because one of its runs matched stands **unfolded for the length of the
   text**, so the run the operator looked for is where it was found; that expansion is borrowed for the view
   and never written to the folding the operator left, which is what gives it back when the text clears.
   Runs that did not match stay folded away under a workspace that matched by its own name — the text asked
   for rows, and the rows it did not name are not what is being looked at.
*/
export function treeRows() {
  const text = state.treeFilter.trim().toLowerCase();
  const shown = [];
  for (const workspace of state.workspaces) {
    const held = workspace.runs.filter((row) => state.archived.has(row.id) === state.showArchived);
    if (state.showArchived && !held.length) continue;
    const runs = text ? held.filter((row) => runName(row).toLowerCase().includes(text)) : held;
    const named = !text || workspaceLabel(workspace.path).toLowerCase().includes(text);
    if (!named && !runs.length) continue;
    shown.push({
      workspace,
      runs,
      open: state.showArchived || state.expanded.has(workspace.path) || Boolean(text && runs.length),
    });
  }
  return shown;
}

/** A run's own name, in the one place both the row and the filter ask for it: the word the row wears — the
 * face's own word for the run when it has named one, the boot's word when only the boot named it, and the
 * operator's first word when neither did, the three settled server-side in the one rule (see `runs.worn_name`)
 * — and its minted stamp's tail when nothing says anything at all. The filter narrows by this word, so a run
 * that has been renamed is found by its new word and nothing further is asked of the operator. */
export const runName = (rowData) => rowData.name || shortRunId(rowData.id);

export function renderTree() {
  // The rows about to be replaced are the ones the standing menu was opened from, and after this point
  // they are not in the document: the menu closes rather than hang on a row nothing holds. A tree is
  // being drawn, and the first-drawn fact the re-list gate keeps is set here and nowhere else.
  treeRendered = true;
  closeMenu();
  nodes.treeNote.textContent = state.treeNotice;
  // The head wears the tree's mark: while any run works, the pane's top says so — the work stands
  // with the tree's rows out of the eye, and the mark is drawn with the tree, so it stands or
  // leaves with the same gate the rows are drawn under. It stands in front of the marks the head
  // wears as its own — the folding pair and the menu — because the work is the fact the head says,
  // and the marks are the acts it offers; a fact is read before an act is chosen.
  for (const mark of nodes.treeHead.querySelectorAll('.sahw-working')) mark.remove();
  if (state.workspaces.some((ws) => ws.runs.some(rowWorking)))
    nodes.treeHead.insertBefore(workingMark(), nodes.treeUnfold);
  // The head's two batch marks wear the dimming the rows' marks used to: a mark stands dimmed while the
  // tree already stands in the state it names, so the head never offers an act it is already doing. A
  // workspace with no runs is nothing to unfold and nothing to fold, and stands in neither mark's aim.
  const withRuns = state.workspaces.filter((ws) => ws.runs.length);
  nodes.treeUnfold.disabled = !withRuns.some((ws) => !state.expanded.has(ws.path));
  nodes.treeFold.disabled = !withRuns.some((ws) => state.expanded.has(ws.path));
  nodes.tree.replaceChildren();
  if (!state.archived.size) state.showArchived = false;
  if (!state.workspaces.length) {
    nodes.tree.appendChild(emptyState('No runs yet', 'Pick a directory below and describe what to do.'));
    return;
  }
  // The entry is absent at zero and carries the truth at any other number: it is the only way back, so
  // the count on it is the count of what is hidden, not of what the tree could show.
  if (state.archived.size) nodes.tree.appendChild(archivedEntry(state.archived.size));
  const lines = treeRows();
  for (const line of lines) {
    nodes.tree.appendChild(workspaceRow(line.workspace, line.runs, line.open));
    if (line.open) {
      for (const row of line.runs) nodes.tree.appendChild(runRow(row, line.workspace.path));
    }
  }
  // A word nothing answers is said, once: rows narrowed away are the filter's doing, and a tree that went
  // quiet without a word reads as a record that lost its runs.
  if (state.treeFilter.trim() && !lines.length) {
    nodes.tree.appendChild(el('div', 'sahw-marker', `no row of the tree is named ${state.treeFilter}`));
  }
}

/** The shelf's own row at the head of the tree: how many runs are put away, and the toggle that shows
 * them. It is the run rows' own shape — a line, its main control, and nothing else. */
export function archivedEntry(count) {
  const line = el('div', 'sahw-line');
  const row = el('button', 'sahw-row');
  row.type = 'button';
  row.setAttribute('aria-expanded', String(state.showArchived));
  row.appendChild(el('span', 'sahw-row__label',
    `${state.showArchived ? UNFOLD_GLYPH : FOLD_GLYPH} Archived (${count})`));
  row.addEventListener('click', () => {
    state.showArchived = !state.showArchived;
    renderTree();
  });
  line.appendChild(row);
  return line;
}

/** The claim a control carries in the two places it is read: the hover's title and the accessible name.
 * Markup says it once (see the pane heads), and a control this file builds says it here. */
export function nameButton(button, claim) {
  button.title = claim;
  button.setAttribute('aria-label', claim);
  return button;
}

/** The small action at the end of a row, named by its title and its accessible name and drawn as one
 * glyph: the row is the thing a reader is trying to hit, so the affordance stays quieter than it. */
export function action(glyph, claim, onClick, cls = 'sahw-act') {
  const button = nameButton(el('button', cls, glyph), claim);
  button.type = 'button';
  button.addEventListener('click', onClick);
  return button;
}
