/* web/assets/js/transcript.js — the transcript: the log's own steps, in the order the log holds them; the
   per-message toolbar; the change an edit made; the command a line withholds; the chip's two hands; the
   acts on the record.

   The steps stand as the log holds them — the words, the calls and their results, the change an edit
   made and the command a line withholds, each stood as it is and refused where the record refuses it —
   and the acts on the record stand beside the steps they act on: the delete that asks before it runs,
   the stop that stands the run down, the fork that rides the run's own word. The chip's two hands stand
   on the document, answered by whoever built the chip (wireChipHands, at the boot).
   */

import { nodes, store, state, number } from './state.js';
import { api } from './wire.js';
import {
  COPY_GLYPH, DOWNLOAD_GLYPH, SELECT_GLYPH, EDIT_GLYPH, INFO_GLYPH, VIEW_GLYPH,
  CHANGE_GLYPH, COMMAND_GLYPH, el, badge, basename, stepDigits, claimedKind, pictureKind,
  MARKDOWN_KINDS, claimedLanguage, imagePath, receiptPaths, goneMark, FORK_GLYPH
} from './components.js';
import { UNDONE, askConfirmation, OFF_DISK } from './modal.js';
import { scrollers } from './scroller.js';
import {
  action, clearPartials, reasoningFace, renderChat, renderHeader, renderTree
} from './trace.js';
import { bubble, directoryOf, renderWord, toolRow } from './reading.js';
import { clockSpan, closeFile, openFile } from './tree.js';
import {
  browse, closeStream, compact, copyMark, editMark, findRun, forkMark, frame, openRun,
  paintDials, refreshTree, rememberedRun, renderComposer, resetDials
} from './composer.js';

/** One picture: the frame the route paints, until the route refuses it. The slot is what stands in the
 * row, and on a failed frame the slot is refilled with the gone-mark — the broken frame goes, the mark
 * takes its place, and the words the row was built around are untouched either way. */
export function picture(path) {
  const slot = el('span', 'sahw-picture');
  const frame = el('img', 'sahw-picture__img');
  frame.setAttribute('src', imagePath(path));
  frame.setAttribute('alt', basename(path));
  frame.addEventListener('error', () => slot.replaceChildren(goneMark(path)));
  slot.appendChild(frame);
  return slot;
}

/** The files one row carries, in the order the record named them — or nothing at all, so a row with no
 * file in it is drawn exactly as it was before the face had eyes. A path whose extension claims a picture
 * is painted; every other path wears the chip the touched files wear, because words are what the preview
 * shows and the reader's refusal is what it shows instead of words it cannot show. */
export function filesRow(paths) {
  const row = el('div', 'sahw-files');
  for (const path of paths) row.appendChild(pictureKind(path) ? picture(path) : chip(path, ''));
  return row.children.length ? row : null;
}

/* --- the reader's place, kept ------------------------------------------------------------------------

   The pane the reader scrolls is the transcript's own, and where they left it is the face's own to keep:
   one key, holding the run the place was stood on, the row, and how far below the top of the pane that
   row stood — and the empty word when the reader stands at the pane's end, because the end is the
   standing the pane wears by default and a default the face has to stand back is no place at all. The
   writing is the reading: every reading the pane publishes (the event the engine speaks when its reading
   is not the one it spoke last) writes the place it carries for the run the pane stands on, so the boot
   that lands at the end costs one write of the empty word and a wheel up costs one write of the place.
   The taking is `standKeptPlace`, asked by the render that stands the rows: the place is stood the first
   moment the row it names stands in the pane, once, and the engine's own accounting keeps it from there —
   the face never sets the pane's scroll by hand. Two lettings go: a kept place naming a run the page does
   not open is no place for this one, and a row the replay never stands is a row the record no longer
   holds. Both end with the empty word written and the pane wearing its default standing, the end with the
   follow on. A value that is not the shape it was written as is no value, as everywhere in the memory.
*/

// The one key the reader's place stands under. The run it was stood on travels inside the value, because a
// place for one run is no place for another and it is the record, not this key, that says which runs stand.
const PLACE = 'read.place';

/* The place this page has read and not yet stood: {run, row, offset}, or nothing. Read once when the run
   it names opens, because the pane's first reading of a run it has just opened says *the end* — and a face
   that wrote that down before the taking had its turn would have forgotten the place it was about to stand.
   It goes when the row stands, and when the record is whole and the row is simply not in it. */
let placeOwes = null;

/** Keep the place the pane's reading carries, for the run the pane is standing on. The reading is a
 * change in where the pane stands, and a write of the face's memory is that change's own cost. */
function keepPlace(event) {
  if (!state.run) return;   // the pane over no run holds no reader's place, and keeps no other run's
  const place = event && event.detail ? event.detail.place : null;
  if (!place || !place.row) { store.write(PLACE, ''); return; }
  store.write(PLACE, { run: state.run.id, row: String(place.row), offset: number(place.offset, 0) });
}

/** Stand the pane where the reader left it, when this page has that place kept for the run it opened.
 *
 * The render that stands the rows asks, because the place is stood the first moment the row it names
 * stands in the pane, and the act answers with the fact of whether that row stands there — so the asking
 * is made again by every render until it lands. A record that has finished speaking — the replay has
 * stood its rows, the run's own `ended` stands on it, the stream closed over it, no asking after it —
 * will not bring the row after all: the place is
 * let go with the empty word, and the pane wears the end and the follow the face would have worn had it
 * never remembered. From the moment the act lands the engine keeps the place; this asks it once.
 */
export function standKeptPlace() {
  if (!state.run) return;
  if (!placeOwes || placeOwes.run !== state.run.id) {
    const kept = store.read(PLACE, '');
    const shape = kept && typeof kept === 'object' ? kept : null;
    if (!shape || !shape.row) { placeOwes = null; return; }   // nothing kept, or nothing to read
    if (shape.run !== state.run.id) {
      // A place stood on another run is no place for the run this page opened — and the keeping goes.
      placeOwes = null;
      store.write(PLACE, '');
      return;
    }
    placeOwes = { run: shape.run, row: String(shape.row), offset: number(shape.offset, 0) };
  }
  const pane = scrollers.get(nodes.scroller);
  if (!pane) return;
  if (pane.scrollToPlace(placeOwes)) { placeOwes = null; return; }
  // The record is whole only when the replay has spoken it: a run this page has just opened already ends
  // with its ending written, and the asking has not stood a single row when the page stands over it — a
  // letting go on that first render would forget the place the taking is about to stand.
  if (state.run.status === 'ended' && state.steps.length > 0 && !state.stream && !state.reattach) {
    placeOwes = null;
    store.write(PLACE, '');
  }
}

/** Stand the place's one hand on the page: the pane's own reading, kept as the reader's place. */
export function wirePlace() {
  nodes.scroller.addEventListener('sahw:message-scroll', keepPlace);
}

/* --- the acts on the record --------------------------------------------------------------------------

   An act's answer is read the same way whoever asked for it: the tree moves when it landed, and a refusal
   — whether it came as `ok: false` in the act's own shape or as an error the route threw — leaves the tree
   standing and its words at the head of the pane the act was asked from. The server's own sentence is what
   is said; the page has no better account of why the machine declined.
*/

/** Carry one act through its answer: `landed` runs only when the act happened. */
export async function runAct(pending, landed) {
  let answer;
  try {
    answer = await pending;
  } catch (error) {
    state.treeNotice = error.message;
    renderTree();
    return;
  }
  if (answer && answer.ok === false) {
    state.treeNotice = answer.reason || 'the server refused the act; nothing was deleted';
    renderTree();
    return;
  }
  state.treeNotice = '';
  landed(answer);
}

/** Take the runs the record no longer holds out of the face's reading of it — including the verdict that
 * had hidden them, which is a fact about a row that is now nothing to look at. */
export function pruneRuns(ids) {
  const gone = new Set(ids);
  for (const workspace of state.workspaces) {
    workspace.runs = workspace.runs.filter((row) => !gone.has(row.id));
  }
  // A workspace is a line of the tree because it holds runs; with none left it is not a line.
  state.workspaces = state.workspaces.filter((workspace) => workspace.runs.length);
  for (const id of gone) state.archived.delete(id);
  store.write('archived', Array.from(state.archived));
}

/** Where the page stands when the run it was showing has left the record: plan 06's default, the pair it
 * opens on — the remembered run while it still lists, the newest run otherwise, and the workspace level
 * with the browser pointed at the directory the act was done in when there is no run at all.
 */
export function afterDelete(workspacePath) {
  if (state.run && findRun(state.run.id)) {
    renderTree();
    refreshTree().catch(() => {});
    return;
  }
  if (!state.run) {
    // Nothing was open, so nothing has to be fallen back on: the tree is the whole of the change.
    renderTree();
    refreshTree().catch(() => {});
    return;
  }
  // The opened run is gone: its stream, its steps and its composer go with it, and what follows is
  // exactly what a page that had never opened it would have opened.
  closeStream();
  state.run = null;
  state.steps = [];
  state.seen = new Set();
  state.follow = '';
  state.steer = '';
  state.notice = '';
  resetDials();                          // the dials go back to what the machine says a new run stands on
  paintDials();
  const next = rememberedRun();
  if (next) {
    openRun(next.row, next.workspace);
    refreshTree().catch(() => {});
    return;
  }
  renderHeader();
  renderTree();
  renderChat();
  renderComposer();
  if (workspacePath) browse(workspacePath);
  refreshTree().catch(() => {});
}

/** Delete one run: the consent first, then the route, then the tree without it. */
export function deleteRunAct(runId) {
  const found = findRun(runId);
  const workspacePath = found ? found.workspace : '';
  askConfirmation({
    title: 'Delete one run',
    lines: [`Run ${runId}${workspacePath ? `, in ${workspacePath}` : ''}`, OFF_DISK, UNDONE],
    confirm: 'Delete the run',
  }, () => runAct(api.deleteRun(runId), (answer) => {
    pruneRuns([answer.deleted || runId]);
    afterDelete(workspacePath);
  }));
}

/** The stop act: end the run's process and let the face settle on the state the kill leaves.
 * The log is untouched — a stopped working run is the orphan's own shape (no ending was written) — so the
 * record is resumable, and the re-list is what says which state the run is in now. No confirmation: the act
 * is reversible (a word after relaunches the run), so it is not the consent the delete owes, and the menu
 * shows it only on a run that is working. When the stopped run is the one open on the face, the kill is
 * this page's own act and the pane owes it the settle the `ended` frame will never bring: a stopped run
 * writes no ending, and the frame that takes the running mark away and settles the in-flight face is the
 * ending's, so the stop settles the pane the way the ending does — the partials clear (the words the dead
 * process will never settle), the chat re-renders off the dead reading, where the run's heartbeat stands no
 * longer, and the composer takes the face a stopped run wears. */
export function stopRunAct(runId) {
  runAct(api.stop(runId), () => {
    if (state.run && state.run.id === runId) {
      state.run.live = 'dead';
      clearPartials();
      renderHeader();
      renderChat();
      renderComposer();
    }
    renderTree();
    refreshTree().catch(() => {});
  });
}

/** The stop act from the composer: the row's own act, aimed at the run the composer stands over, with
 * the face's own settle after it. The kill is the fact the server just answered with okay, and the face
 * believes it on the row's live reading the way it believes a follow's relaunch — so the composer
 * re-renders on the dead reading: the marks that stood with the working run go, and a word riding the
 * queue delivers to the run it stood over, the way the ending delivers it. The re-list is the record
 * agreeing with the face's belief, the way the follow's re-open is. */
export function stopRunComposer() {
  if (!state.run) return;
  const runId = state.run.id;
  runAct(api.stop(runId), () => {
    if (state.run && state.run.id === runId) {
      state.run.live = 'dead';
      clearPartials();
      renderHeader();
      renderChat();
      renderComposer();
    }
    renderTree();
    refreshTree().catch(() => {});
  });
}

/** Delete a workspace's runs: the count is the act named, since a batch has no one id to name. */
export function deleteWorkspaceAct(workspace) {
  const count = workspace.runs.length;
  const said = count === 1 ? '1 run' : `${count} runs`;
  askConfirmation({
    title: 'Delete every run in this workspace',
    lines: [`The ${said} of ${workspace.path}`, OFF_DISK, UNDONE],
    confirm: `Delete ${said}`,
  }, () => runAct(api.deleteAll(workspace.path), (answer) => {
    const ids = Array.isArray(answer.deleted) && answer.deleted.length
      ? answer.deleted : workspace.runs.map((row) => row.id);
    pruneRuns(ids);
    afterDelete(workspace.path);
  }));
}

/* --- the transcript: the log's own steps, in the order the log holds them ------------------------

   The stream frames every line of the log; the pane shows all of them but one. `started` is the
   header's facts — the model's name and the status the badges already carry — and `ended` never
   arrives as a step at all, because the stream closes with a frame of its own. What is left is the
   record, and the record is the pane: what the user asked, what the model said, what it asked the
   harness for, whether it was allowed, what came back, and the harness's own word in between.

   The row is the **segment**: a maximal stretch of steps by one actor, kept under one header. A call
   names the turn that made it in its `refs`, the same reference the chips follow, so the calls a turn
   made stand with that turn rather than each under its own name — tool activity between two messages
   of one speaker does not break the segment, it is what the speaker did between them. A step the pane
   draws nothing for is not a step that changes the speaker either.

   A **cut** is the record's word for the operator returning the conversation to a step, and it is the one
   line that is neither speaker's turn: it earns a marker row where it stands. The pane shows the
   conversation in force, not the whole file — the steps the cut detached are kept in the log, the branch
   the run gave up on, and they owe the pane no lines — and which ones those are is the pane's own
   `lineage` projection, the same walk the server makes before it answers a cut, so what the pane withholds
   and what the route refuses to return to are one answer (see `detachedSteps`).

   Live and replay are this one rendering: the steps arrive from a stream and from that stream replaying
   a finished log, and nothing below looks at which.
*/

/** The row a step earns, or '' for a step the pane draws nothing for.
 *
 * An allowed operation draws nothing: a row that says "allowed" is a row that says nothing, and the
 * call it stands for is already on the screen. A refusal is the opposite case — the reason the run was
 * stopped is the one thing the call's own row cannot tell. A cut is the third case and the operator's
 * own: the log says a step was returned to and a tail was detached, and neither is legible from the
 * steps around it, so it earns the marker row it needs to be read in. */
export function rowType(step) {
  if (step.kind === 'message') {
    // A user message the core itself sent is a nudge between turns, a word of the machinery rather
    // than the operator's own: it stands in the pane's quietest line, never under the operator's name.
    if (step.role === 'user' && step.issuer === 'core') return 'plumbing';
    return 'text';
  }
  if (step.kind === 'call') return 'call';
  if (step.kind === 'notice') return 'notice';
  if (step.kind === 'result') return 'result';
  if (step.kind === 'cut') return 'cut';
  if (step.kind === 'fork') return 'fork';
  if (step.kind === 'operation') return step.outcome === 'allowed' ? '' : 'refusal';
  return ''; // `started`, and `ended` were they ever to arrive as a step
}

/** Whose stretch a step stands in: the user's own message is the user's row, and everything else the
 * log holds — what the model said, what it asked the harness for, what the harness answered — stands
 * under the model's name, because it is the model's turn being carried out. */
export function rowActor(step) {
  return step.kind === 'message' && step.role === 'user' ? 'user' : 'model';
}

/** Which of the log's steps the conversation in force no longer holds: the pane's own `lineage` walk,
 * the very one the server walks before it answers a cut — file order, truncating at each `cut` to the
 * prefix ending at the step it names, so the target stays, what came after it detaches, and a later cut
 * composes over an earlier one because it may aim at a step an earlier cut made and a detached step never
 * re-enters.
 *
 * This is the one projection the log cannot say line by line, and the pane needs it for the one thing the
 * record's own order cannot tell the reader: which of the steps the conversation in force no longer holds.
 * It is a set of ids rather than a shorter list because the set is what the pane withholds: the log keeps
 * the whole file — the branch the run gave up on — and the pane shows the conversation in force.
 *
 * A `cut` line is not a turn of the conversation, so it is never in force; but it stands in the stretch a
 * later cut can detach, so it joins the walk just after the truncation it belongs to and is read back with
 * the rest. That is what mutes a superseded marker and keeps the newest one at full weight. A cut naming a
 * step this walk does not hold is the corruption `lineage` refuses to project from, and the pane answers
 * it the way the report does — nothing is muted, the log is shown as it is, and the marker still says what
 * it tried to do.
 */
export function detachedSteps(steps) {
  const gone = new Set();
  const held = [];      // the steps the conversation holds so far, in the order the file gave them
  for (const step of steps) {
    if (step.kind === 'cut') {
      const target = typeof step.to === 'string' ? step.to : '';
      for (let index = held.length - 1; index >= 0; index -= 1) {
        if (held[index].id !== target) continue;
        for (const lost of held.splice(index + 1)) {
          if (lost.id) gone.add(lost.id);
        }
        break;
      }
      held.push(step);
      continue;
    }
    held.push(step);
  }
  return gone;
}

/** The pane's rows: the steps grouped into the segments they belong to, each result moved onto the
 * row of the call it answers.
 *
 * One pass, because the log's order is the pairing: a `call` is written before the `result` that
 * answers it, and the answer's `refs` names the call by id. A result whose call is not on the screen
 * keeps a row of its own — the pane loses no line of the record over a step it did not expect.
 *
 * Two things cut across the grouping, and both are the cut's doing. A `cut` line stands on a row of its
 * own — it is the operator's act between two stretches of the record, not a turn of anybody's — so it
 * opens a segment of one and leaves none open, and the step after it starts afresh whichever speaker it
 * belongs to. And every segment carries whether the conversation still holds it, from the projection
 * above; a segment closes where that answer changes, so the mute falls exactly where the cut fell and
 * never across the line.
 *
 * A third thing is the cut's re-presentation: the stretch the cut opens re-includes the word it
 * returned to — the record is append-only and the stretch is self-contained — so when the operator sent
 * the word back unchanged the file holds it twice, once as the target the cut keeps and once as the word
 * re-spoken. The conversation in force holds the word at the cut, and the pane shows it there: the first
 * operator word after the cut that matches the word the cut names stands in the mute with the tail the
 * cut detached. A first word that differs is the edit itself — the before and the after stand on either
 * side of the marker, and the marker says which is which.
 */
export function transcriptSegments(steps) {
  const gone = detachedSteps(steps);
  const byId = new Map();
  for (const step of steps) if (step.id) byId.set(step.id, step);
  let rePresentation = null;
  const segments = [];
  const calls = new Map(); // the tool rows already drawn, by call id, so an answer can find its row
  let current = null;
  for (const step of steps) {
    const type = rowType(step);
    if (!type) continue;
    const answered = type === 'result' ? calls.get(references(step)[0]) : null;
    if (answered) {
      answered.results.push(step);
      continue;
    }
    const item = { type, step, results: [] };
    if (type === 'call' && step.id) calls.set(step.id, item);
    const actor = rowActor(step);
    const spoken = type === 'text' && actor === 'user' && step.issuer !== 'core';
    const spokenBack = spoken && rePresentation !== null && step.text === rePresentation;
    if (spoken) rePresentation = null; // the first word after the cut is spoken; the stretch has begun
    const detached = gone.has(step.id) || spokenBack;
    // A `cut` and a `fork` are both the operator's act between two stretches of the record rather than a
    // turn of anybody's, and a `plumbing` line is the harness's own word between the model's turns —
    // the nudge that asks for the missing call — the same kind of seam: each opens a marker segment of
    // one and leaves none open, so the step after it starts afresh whichever speaker it belongs to. The
    // boundary a fork marks is the seam between the prefix it carried and the steps that are its own,
    // and the carried side is *not* detached — nothing was given up on — so it keeps its full weight
    // while the marker says where the seam is.
    if (type === 'cut' || type === 'fork' || type === 'plumbing') {
      if (type === 'cut') {
        // The cut names its target by id; when the target is an operator word, the stretch that follows
        // re-spoke it, and the pane owes to mute the re-speaking if it came back unchanged.
        const target = byId.get(step.to);
        rePresentation = target && target.kind === 'message' && target.role === 'user'
          && typeof target.text === 'string' ? target.text : null;
      }
      segments.push({ role: 'marker', marker: type, items: [item], detached });
      current = null;
      continue;
    }
    if (!current || current.role !== actor || current.detached !== detached) {
      current = { role: actor, items: [], detached };
      segments.push(current);
    }
    current.items.push(item);
  }
  for (const segment of segments) {
    // The row is named for the turn it opens with: the scroller names the conversation's rows, and the
    // conversation's row is the message a segment begins with, its calls and answers notwithstanding.
    // That step is also the row's moment: its `ts` is the time the row carries.
    const opener = segment.items.find((item) => item.type === 'text') || segment.items[0];
    segment.id = opener.step.id || '';
    segment.opener = opener.step;
  }
  return segments;
}

/** One segment: the speaker's header over everything they did, in the order the log held it. The marker
 * segment is the exception that has no speaker — the act of an operator between two stretches of the
 * record — and it wears its row alone: the cut's sentence for a `cut`, the fork's for a `fork`. */
export function segmentRow(segment) {
  if (segment.role === 'marker') {
    return segment.marker === 'fork'
      ? forkRow(segment.opener, segment.detached)
      : segment.marker === 'plumbing'
        ? plumbingRow(segment.opener, segment.detached)
        : cutRow(segment.opener, segment.detached);
  }
  const fromModel = segment.role === 'model';
  const row = el('div', fromModel ? 'sahw-message' : 'sahw-message sahw-message--end');
  // The mute: what reaches here detached is the marker a later cut superseded — the record still holds
  // the stretch it named, the conversation does not, and the row says which of the two it is standing in:
  // the return the run gave up on in the quiet ink, the return it stands on at full weight.
  if (segment.detached) row.classList.add('sahw-muted');
  if (segment.id) row.dataset.sahwMessageId = segment.id; // the pane's engine reads its rows by this id
  const content = el('div', 'sahw-message__content');
  // The row owes no line: the name, the moment, and the numbers the turn was measured in stand under
  // the mark that holds them, at the bottom of the turn, where the reader stands when the words end —
  // a line over the words owed the reader the scroll back up to read it, and a line under the words
  // owes the words nothing at all. The operator's row owes no name — the page itself is the name —
  // and a stretch with no name and no moment owes no line, and so no mark.
  for (const item of segment.items) {
    if (item.type === 'text') {
      // The thought the turn thought, settled the way the word settles: the record's words stand whole
      // on the asking, above the word they stood above — the quiet line its kind is owed, the face the
      // turn was thinking in standing no longer. A step that carries no reasoning field is a step the
      // pane reads the way it always read a step: no face, no line, the pane the turn always stood in.
      if (fromModel && typeof item.step.reasoning === 'string' && item.step.reasoning) {
        content.appendChild(reasoningFace(item.step.reasoning));
      }
      // A turn that only asked for tools has no text, and an empty bubble is a box around nothing. A
      // turn the endpoint would not answer has no text either, and the record's words for why — the
      // transport's own sentence — stand where the bubble would have, rather than the row owing none.
      if (item.step.text) content.appendChild(bubble(item.step, fromModel));
      else if (fromModel && typeof item.step.error === 'string' && item.step.error) {
        content.appendChild(failedTurnRow(item.step));
      }
    } else if (item.type === 'call') {
      content.appendChild(toolRow(item.step, item.results));
    } else if (item.type === 'refusal') {
      content.appendChild(refusalRow(item.step));
    } else if (item.type === 'notice') {
      content.appendChild(noticeRow(item.step));
    } else {
      content.appendChild(resultBlock(item.step)); // an answer with no call beside it stands alone
    }
  }
  // What the turn did to the disk, standing where its words end. The row is the segment's own reading of
  // its calls, so it wears the segment's mute when the cut detached the stretch it belongs to, and it
  // says nothing the tool rows beside it do not already say.
  const touched = turnFilesRow(segment);
  if (touched) content.appendChild(touched);
  row.appendChild(content);
  // The row's own acts, standing below the words, where the reader stands when the words end: a mark
  // beside the words in the row's flow stole the words' width as the line stands, and the reader's
  // hand is at the bottom of a long word when it wants to act on it. The line the row once wore over
  // its words stands here too — the mark that holds it — because the bottom of the turn is where the
  // reader stands when the turn is done. See `rowTools` for who is offered what.
  const tools = rowTools(segment, fromModel);
  if (tools) content.appendChild(tools);
  // The line the mark holds is not in the row's flow: the words below the mark would move for the line
  // to open, and the scroller cuts what stands inside it — so the line floats where the mark stands,
  // hung off the document the way the menu is. The render that follows the click is the one that stands
  // it, and the render that owes it nothing owes no panel: the standing and the placing are the
  // render's tail's work, where the rows have stood and the mark has its standing.
  return row;
}

/* --- the per-message toolbar: the acts a word of the record invites -------------------------------------

   Three acts are aimed at a step rather than at the run, and they stand on the row they act on: `✎`
   returns the conversation to it (the cut), `⑂` branches a new run from it (the fork), and `⧉` hands its
   words to the clipboard. They are one row rather than three loose marks because they are one kind of
   thing — what an operator does with a word that is already in the record — and a new act of the same
   kind is a new icon in the same row, not a new place on the page.

   Who is offered what follows from whose word it is and whether the conversation still holds it. Only
   the words the operator sent are theirs to send again or to branch, so only their rows carry the cut and
   the fork; a step the conversation gave up on is refused by the route that would be asked, so its row
   offers neither; and the copy reaches nothing but the browser, so it stands wherever there are words to
   hand over. The row is hidden until the hand is on it, which is the one thing the single mark it replaces
   did not do — and the mark itself is unchanged inside it, first icon in the row.
*/
/** The turn's own numbers: the last of the stretch's message steps to carry any — the request the
 * context was largest at, and the line the composer's own line reads for the whole record. A stretch
 * the record never measured owes none, and the panel owes no number the record does not stand. */
export function segmentStats(segment) {
  for (let index = segment.items.length - 1; index >= 0; index -= 1) {
    const step = segment.items[index].step;
    if (step.kind === 'message' && (typeof step.tokens_in === 'number' || typeof step.tps === 'number')) {
      return step;
    }
  }
  return null;
}

/** The hand that holds a line open: the hover opens it, and a hand that leaves is given the gap to
 * cross — the close is scheduled, not immediate, because a hand that leaves the mark to read the line
 * it opened is still the hand that opened it, and the line it opened stands until the hand is clearly
 * gone. The state stands the line, not the mark's own hand: a re-render stands it from the state, and
 * the mark and the line both aim at it, and both give the hand its moment. */
export let infoCloseTimer = null;
export let infoClickSegment = null;

export function aimInfo(segmentId) {
  if (infoCloseTimer) { clearTimeout(infoCloseTimer); infoCloseTimer = null; }
  if (state.infoOpen === segmentId) return;
  // The close a mark's click owes re-stands the mark under the hand that clicked it, and a standing
  // cursor re-aims the mark it stands on: the line the click just put away opens again, undone by the
  // hand's own standing. The one re-aim the standing cursor owes is the one for the segment the click
  // closed, and only that one — a hand arriving at the mark again, or at another mark at all, has
  // moved, and its aim stands.
  if (infoClickSegment === segmentId) { infoClickSegment = null; return; }
  infoClickSegment = null;
  state.infoOpen = segmentId;
  renderChat();
}

export function unaimInfo() {
  if (infoCloseTimer) { clearTimeout(infoCloseTimer); infoCloseTimer = null; }
  if (!state.infoOpen) return;
  state.infoOpen = '';
  renderChat();
}

export function nudgeInfoClose() {
  if (infoCloseTimer) return;
  infoCloseTimer = setTimeout(() => { infoCloseTimer = null; unaimInfo(); }, 250);
}

/** The line's standing beside its mark: fixed, the way the menu stands — under the mark the line
 * holds, at the side the mark stands, kept on screen the way the menu is kept. */
export function placeInfoPanel(node, anchor) {
  const from = anchor.getBoundingClientRect();
  const box = node.getBoundingClientRect();
  node.style.left = `${Math.max(0, Math.min(from.left, window.innerWidth - box.width))}px`;
  node.style.top = `${Math.max(0, Math.min(from.bottom + 4, window.innerHeight - box.height))}px`;
}

/** The line a turn owes, standing open under the mark that holds it: one line per thing the line
 * owes — the name, the moment, the numbers the turn was measured in — the whole of the record's
 * reading of the turn, and nothing the record does not stand. The name and the numbers stand on the
 * model's row alone: the operator's row owes no name, the page itself is the name, and the turn the
 * words were measured in is the model's. */
export function infoPanel(segment, fromModel) {
  const panel = el('div', 'sahw-info__panel');
  if (fromModel) panel.appendChild(el('div', 'sahw-info__item', state.run.model || 'model'));
  const clock = clockSpan(segment.opener, false);
  if (clock) {
    const item = el('div', 'sahw-info__item');
    item.appendChild(clock);
    panel.appendChild(item);
  }
  const stats = segmentStats(segment);
  if (stats) {
    if (typeof stats.tokens_in === 'number') {
      const ceiling = typeof stats.context_max === 'number' ? `/${compact(stats.context_max)}` : '';
      panel.appendChild(el('div', 'sahw-info__item sahw-info__stat', `ctx ${compact(stats.tokens_in)}${ceiling}`));
    }
    if (typeof stats.tokens_out === 'number') {
      panel.appendChild(el('div', 'sahw-info__item sahw-info__stat', `out ${stats.tokens_out}`));
    }
    if (typeof stats.prefill_tps === 'number') {
      panel.appendChild(el('div', 'sahw-info__item sahw-info__stat', `${Math.round(stats.prefill_tps)} tps prefill`));
    }
    // The decode rate closes the line: prefill first, so the number the turn delivered — its words a
    // second — stands last, where the reader's eye ends on the line.
    if (typeof stats.tps === 'number') {
      panel.appendChild(el('div', 'sahw-info__item sahw-info__stat', `${Math.round(stats.tps)} tps`));
    }
  }
  // The hand that opened the line may be reading it: the line gives the hand its moment the way the
  // mark does, and it aims the line at its own stretch so a hand that arrives at it from the mark
  // finds it standing.
  panel.addEventListener('mouseenter', () => aimInfo(segment.id));
  panel.addEventListener('mouseleave', nudgeInfoClose);
  return panel.children.length ? panel : null;
}

/** The mark that holds the line the row once wore over its words: the name, the moment, and the
 * numbers the turn was measured in, one hover under the acts, standing where the reader stands when
 * the words end. The hover is enough — the mark opens the line it holds — so the claim the mark makes
 * by standing is no tooltip the mark has to say. It is the one act here that reaches nothing but the
 * turn's own line — no route, no state but the one that stands it, no word sent — so it stands on the
 * model's rows as well as the operator's, and on a detached stretch as well as a live one. */
export function infoMark(segment, fromModel) {
  const mark = action(INFO_GLYPH,
    'The turn\'s own line: the name, the moment, the numbers the turn was measured in', () => {
      if (state.infoOpen === segment.id) {
        infoClickSegment = segment.id;
        unaimInfo();
      }
      else aimInfo(segment.id);
    });
  mark.classList.add('sahw-info');
  mark.title = '';   // the hover is the mark's own claim; a tooltip would stand over the line it opens
  mark.addEventListener('mouseenter', () => aimInfo(segment.id));
  mark.addEventListener('mouseleave', nudgeInfoClose);
  return mark;
}

export function rowTools(segment, fromModel) {
  // The row's words, in the order the row shows them: what `⧉` gives the clipboard. A stretch of one
  // speaker's turns is one thing to copy, and the tool calls and their answers are not words to copy.
  const words = segment.items
    .filter((item) => item.type === 'text' && item.step.text)
    .map((item) => item.step.text)
    .join('\n\n');
  const number = stepDigits(segment.opener.id);
  const sendable = !fromModel && !segment.detached && number;
  const tools = el('div', 'sahw-tools');
  if (sendable) tools.appendChild(editMark(segment.opener));
  if (sendable) tools.appendChild(forkMark(segment.opener, number));
  // The mark that holds the line the row once wore: it stands before the clipboard, on every row the
  // line owed — a stretch that says nothing but calls owed the line its moment, too — and on no row
  // the line owed nothing.
  if (fromModel || clockSpan(segment.opener, false)) tools.appendChild(infoMark(segment, fromModel));
  if (words) tools.appendChild(copyMark(words));
  return tools.children.length ? tools : null;
}

/** A word's own code fences: a line of triple backticks opens a block and names the language it
 * stands in, and a block is code, not a word — the pane shows it as a pre, and the highlighter, when
 * the page carries one, is asked for its colours. A fence that never closes holds to the end of the
 * word: the model stopped mid-block, and the block it started is the block it meant. A block the
 * page carries no language for is shown plain — the words, not a fetch, are what the pane owes. */
/* The grammar a fence owes, when the fence's claim and the content's fact part ways: a fence that
   names python and opens on a prompt line holds a session, not code — the prompt's words are the
   python it invites, and the lines the session answers with are the machine's own. The head keeps
   the fence's claim; the grammar follows the content. */
export function fenceLang(lang, value) {
  if (lang !== 'python' && lang !== 'py') return lang;
  const first = value.split('\n').find((line) => line.trim() !== '') || '';
  return /^ {0,3}>>>/.test(first) ? 'pycon' : lang;
}

/* The grammar the page owes the session a fence names: Prism ships no grammar for a transcript of
   a prompt, so the face writes its own, the way it writes the sheet the tokens owe. The marker a
   line wears stands in the punctuation the marks between the words wear; the words the marker
   invites stand in the python that stands in them; and every other line is the machine's answer,
   and the answer stands in the theme's muted. */
if (window.Prism) {
  Prism.languages = Prism.languages || {};
  if (!Prism.languages.pycon) {
    Prism.languages.pycon = {
      prompt: {
        pattern: /^ {0,3}(?:>>>|\.\.\.)[ \t]+[^\n]*$/gm,
        inside: {
          marker: { pattern: /^ {0,3}(?:>>>|\.\.\.)[ \t]+/, alias: 'punctuation' },
          code: { pattern: /[\s\S]*$/, inside: Prism.languages.python },
        },
      },
      output: { pattern: /^[^\r\n>].*$/m, alias: 'output' },
    };
  }
}

/* --- the change an edit made, stood as the change it is ---------------------------------------------

   The record already holds the whole of an `edit`: the words that stood there, the words that stand there
   instead, and an answer naming the line the change stood on. So the change needs no new route and no new
   field — the pane reads the two words the call carries against each other, line for line, and stands the
   reading under the line the call stands in, on the asking of the act the change earns.

   The reading is the agreement of those two words and nothing else. The record does not hold the
   neighbourhood the span stood in, so no line the record does not hold stands in the reading, and every
   line of both words stands exactly once: the lines the two agree on are the context the change stood in,
   the lines only the first word holds were given up, and the lines only the second holds are what the file
   now holds. The agreement is the longest one the two words have *in order*, because a shorter agreement
   would stand a line the words agree stood as a line the change moved.

   The numbers come from the answer: the change stood where the answer says it stood, so the first line of
   the reading stands on that line and every line after it counts up, over the context and the change
   alike. A change the tool made in every place stands this reading once — the words are the change, and
   how many places it landed in is the answer's own sentence, standing beside it. The cap the pane owes a
   long word is owed here too: each word is read from its head and the mark says so, because a change of
   five thousand lines is a pager, not a transcript. */

// The change's own sentence, as the tool writes it: `edited <file>: changed 2 place(s) at line 41,
// 1234 -> 1250 characters`. Only a change that landed says what it changed — a refusal may name lines,
// and even name how many places a span matched, but it never says it changed a place at a line.
export const CHANGE_RECEIPT = /changed (\d+) place\(s\) at line (\d+)/;

/** The line the tool says the change stood on, and how many places it landed in. `null` is an answer that
 * did not land a change: the refusal's own sentence stands, and the change it refused stands nowhere. */
export function changeAnchor(result) {
  const sentence = typeof result.content === 'string' ? result.content : '';
  const landed = CHANGE_RECEIPT.exec(sentence);
  return landed ? { places: Number(landed[1]), line: Number(landed[2]) } : null;
}

/** The change a call stands for, or `null` for a call that stands none: not an `edit`, an `edit` whose
 * words the record does not hold whole, a call whose answer refused the change, and a call with no id for
 * the asking of its reading to stand on. */
export function editChange(call, results) {
  if (call.name !== 'edit' || typeof call.id !== 'string' || !call.id) return null;
  const args = call.args && typeof call.args === 'object' ? call.args : {};
  if (typeof args.old_text !== 'string' || typeof args.new_text !== 'string') return null;
  for (const answer of results) {
    const landed = changeAnchor(answer);
    if (landed) return { from: args.old_text, to: args.new_text, line: landed.line };
  }
  return null;
}

/** The head of each word of a change longer than the pane reads, and the marks naming what was cut. The
 * answer's own cap, owed twice because a change is two words: each word the cap cut earns the sentence
 * that says so — the sentence names the word it cut, which is what the cap's `noun` is for — and a change
 * whose words both stand whole owes no mark at all. */
export function capChange(from, to) {
  const gaveUp = capResult(from, 'text the call was asked to take away');
  const nowHeld = capResult(to, 'text the call was asked to put there');
  return {
    from: gaveUp.text,
    to: nowHeld.text,
    marks: [gaveUp.notice, nowHeld.notice].filter(Boolean),
  };
}

/** The reading two words owe each other, line for line: `kept` where they agree, `gone` for a line only
 * the first holds, `set` for a line only the second holds. The agreement is the longest the two words have
 * keeping their order — the table below *is* that agreement, and walking it from the head is the reading.
 */
export function changeReading(from, to) {
  const gaveUp = from.split('\n');
  const nowHeld = to.split('\n');
  const agree = [];
  for (let i = 0; i <= gaveUp.length; i += 1) agree.push(new Array(nowHeld.length + 1).fill(0));
  for (let i = gaveUp.length - 1; i >= 0; i -= 1) {
    for (let j = nowHeld.length - 1; j >= 0; j -= 1) {
      agree[i][j] = gaveUp[i] === nowHeld[j]
        ? agree[i + 1][j + 1] + 1
        : Math.max(agree[i + 1][j], agree[i][j + 1]);
    }
  }
  const rows = [];
  let i = 0;
  let j = 0;
  while (i < gaveUp.length && j < nowHeld.length) {
    if (gaveUp[i] === nowHeld[j]) {
      rows.push({ kind: 'kept', text: gaveUp[i] });
      i += 1;
      j += 1;
    } else if (agree[i + 1][j] >= agree[i][j + 1]) {
      rows.push({ kind: 'gone', text: gaveUp[i] });
      i += 1;
    } else {
      rows.push({ kind: 'set', text: nowHeld[j] });
      j += 1;
    }
  }
  while (i < gaveUp.length) { rows.push({ kind: 'gone', text: gaveUp[i] }); i += 1; }
  while (j < nowHeld.length) { rows.push({ kind: 'set', text: nowHeld[j] }); j += 1; }
  return rows;
}

// The token the highlight's sheet already owes each kind of line: the word the document gave up, and the
// word it set. A kept line wears no token — the theme's own words, unmarked, are what a line the file kept
// is read in.
export const CHANGE_TOKENS = { gone: ' token deleted', set: ' token insertion' };

/** One line of the reading: its own number in the gutter the face owes a line that says where it stood,
 * and the words the record holds, in the token the theme owes them. */
export function changeLine(row, number) {
  const line = el('div', `sahw-change__line sahw-change__line--${row.kind}`);
  line.appendChild(el('span', 'sahw-change__num', String(number)));
  line.appendChild(el('span', `sahw-change__text${CHANGE_TOKENS[row.kind] || ''}`, row.text));
  return line;
}

/** The change, stood under the line that made it: the marks naming any word the cap cut, then the reading,
 * its first line standing where the answer says the change stood. The face's own lines and no ground of
 * its own — only the ground the theme owes a word given up or set says which way a line went. */
export function changeBox(change) {
  const words = capChange(change.from, change.to);
  const box = el('div', 'sahw-change');
  for (const notice of words.marks) box.appendChild(el('div', 'sahw-marker sahw-change__ask', notice));
  const rows = changeReading(words.from, words.to);
  for (let at = 0; at < rows.length; at += 1) box.appendChild(changeLine(rows[at], change.line + at));
  return box;
}

/** The act a change earns, standing in the line the call stands in: the asking for the reading the record
 * holds. Asked again, the line stands the way it stood before — the reading is built from the asking on
 * every render, and nothing else about the line moves either way. */
export function changeMark(call) {
  const asked = state.changes.has(call.id);
  const mark = action(CHANGE_GLYPH,
    asked ? 'Take the change this call made away again'
      : 'Stand the change this call made, line for line', () => {
        if (state.changes.has(call.id)) state.changes.delete(call.id);
        else state.changes.add(call.id);
        renderChat();
      });
  mark.classList.add('sahw-tool__change');
  mark.setAttribute('aria-pressed', asked ? 'true' : 'false');
  return mark;
}

/* --- the command a line withholds, stood as the word the record holds ---------------------------------

   The line a `bash` call earns says what the call is pointed at: the command put on one line and cut at
   the line's own cut, the mark the cut wears. What the line withholds is a fact the record already carries
   — the exact word the run was asked to run, newlines and script and all — so the command needs no new
   route and no new field: the pane reads the word off the call it is already reading, and stands it under
   the line on the asking of the act the withholding invites.

   The word stands as the record holds it, and the record's word is the whole of the reading: the newlines
   it carried stand as newlines, so a script stands as the script the run gave it and not as the one line
   the face put it on. It stands plain, in the theme's ink and the face's own mono, because the command a
   call was asked to run is not the prose a sheet owes its fences to — no language stands in it. The block
   it stands in is the face's own block, the shape a word that stands under a line and over the answer
   already wears, and it has no ground of its own: the ground beside the words is the ground the theme
   stands, the same one the answer's own words stand beside. A command longer than the pane reads a word
   stands the head of it and the mark that says so, in the sentence the cap already speaks, naming the
   command it cut rather than the result — because the word the pane withheld is the command, not the
   answer. Nothing here is a second copy of anything: the line keeps the summary the line already owed,
   and the record keeps every byte, and the asking only stands the reading. */

/** The command, stood under the line that withholds it: the word the record's own call holds, whole —
 * the newlines the record holds standing as the newlines the record holds — with the mark and the
 * sentence the pane owes a word longer than it reads, naming the command it cut. The words are the
 * record's and nothing else: no language the sheet owes, and no ground of the block's own. */
export function commandBox(command) {
  const box = el('div', 'sahw-command');
  const shown = capResult(command, 'command the call was asked to run');
  if (shown.notice) box.appendChild(el('div', 'sahw-marker sahw-command__ask', shown.notice));
  box.appendChild(el('pre', 'sahw-pre sahw-command__pre', shown.text));
  return box;
}

/** The act a withheld command earns, standing in the line the call stands in, at the line's right edge,
 * in front of the timestamp: the asking for the word the record holds. Asked again, the line stands the way it
 * stood before the act stood it — the block is built from the asking on every render, and the asking is
 * the face's own state, so a frame the record speaks re-stands the block standing rather than closing
 * it. */
export function commandMark(call) {
  const asked = state.commands.has(call.id);
  const mark = action(COMMAND_GLYPH,
    asked ? 'Take the command this call was asked to run away again'
      : 'Stand the command this call was asked to run, whole', () => {
        if (state.commands.has(call.id)) state.commands.delete(call.id);
        else state.commands.add(call.id);
        renderChat();
      });
  mark.classList.add('sahw-tool__command');
  mark.setAttribute('aria-pressed', asked ? 'true' : 'false');
  return mark;
}

/** A permission decision that was not an allowing one: the reason, verbatim, as the run was told it. */
export function refusalRow(step) {
  const row = el('div', 'sahw-refusal');
  row.appendChild(badge(step.outcome || 'refused', 'error'));
  row.appendChild(el('span', 'sahw-refusal__reason', step.reason || 'the log gives no reason'));
  const clock = clockSpan(step, false);
  if (clock) row.appendChild(clock);
  if (step.address) row.title = String(step.address);
  return row;
}

/** The model's turn the endpoint would not answer, standing the record's own words: the outcome's
 * badge and the transport's sentence verbatim, where the turn's words would have stood — so a run that
 * died on the wire says why, instead of standing as an empty bubble under the model's name. The
 * record keeps the failure beside the turn that failed, in the `error` the record's own writer puts
 * there, and this row is that sentence, in the shape the face already owes a word of failure. */
export function failedTurnRow(step) {
  const row = el('div', 'sahw-refusal');
  row.appendChild(badge(step.outcome || 'failed', 'error'));
  row.appendChild(el('span', 'sahw-refusal__reason',
    step.error || 'the log gives no words for the failure'));
  const clock = clockSpan(step, false);
  if (clock) row.appendChild(clock);
  return row;
}

/** The harness's own word — a nudge, the verify declaration — as the marker row it reads like. The
 * subject says which kind of word it was and rides in the title, where it does not crowd the text. */
/** The harness's own word standing in the record: the nudge that asks for the missing call. Neither
 * the operator's turn nor the model's — the machinery between two stretches of the record — so the
 * pane wears it in its quietest line, the marker's shape at the record's own weight. The record keeps
 * the words where the reader who wants the seam can have them; the pane only refuses them the
 * operator's name and a turn's weight. */
export function plumbingRow(step, muted) {
  const line = el('div', 'sahw-marker sahw-plumbing');
  line.appendChild(el('span', 'sahw-marker__content', typeof step.text === 'string' ? step.text : ''));
  if (muted) line.classList.add('sahw-muted');
  return line;
}

export function noticeRow(step) {
  const marker = el('div', 'sahw-marker');
  if (step.subject) marker.title = String(step.subject);
  // The nudge's own notice is the machinery's word: it stands in the quiet line its nudge stands in.
  if (step.subject === 'nudge') marker.classList.add('sahw-plumbing');
  marker.appendChild(el('span', 'sahw-marker__content', typeof step.text === 'string' ? step.text : ''));
  const clock = clockSpan(step, false);
  if (clock) marker.appendChild(clock);
  return marker;
}

/** The marker a cut earns where it stands: the sentence the record owes a reader about the one act its
 * own steps cannot tell — the conversation went back to step N, and everything the file held after that
 * step is detached, kept in the log and out of every conversation from here on. It is one more of the
 * pane's marker rows, the shape the notices and the running mark wear, because it is the same kind of row:
 * a word about the record rather than a turn inside it. The whole target id rides in the title, where the
 * reader who wants the exact line can have it without the sentence having to carry it. */
export function cutRow(step, muted) {
  const marker = el('div', 'sahw-marker sahw-cut');
  const where = stepDigits(step.to);
  marker.appendChild(el('span', 'sahw-marker__content',
    `the conversation returned to step ${where || '?'} — the later steps are detached: `
    + 'kept in the log, never in a conversation again'));
  if (step.to) marker.title = String(step.to);
  const clock = clockSpan(step, false);
  if (clock) marker.appendChild(clock);
  // A cut a later cut cut away is history twice over, and it reads that way: the marker wears the same
  // mute as the stretch it belonged to, while the cut the run is standing on keeps its full weight.
  if (muted) marker.classList.add('sahw-muted');
  return marker;
}

/** The marker a fork earns where its record says the seam is: the sentence that says where this run's own
 * steps begin, because everything above the line is the conversation it was carried in on and everything
 * below is the one it is having. It is the cut's sibling in shape — a word about the record in one of the
 * pane's marker rows, not a turn inside it — and its opposite in what it does to the steps around it: a
 * cut mutes what it detached, and a fork detaches nothing, so the prefix it carries stands at full weight.
 *
 * The whole target id rides in the title, where the reader who wants the exact line can have it without
 * the sentence carrying it, and a row a later cut cut away is muted like any other step the conversation
 * gave up on. */
export function forkRow(step, muted) {
  const marker = el('div', 'sahw-marker sahw-forked');
  const source = typeof step.source_run === 'string' ? step.source_run : '';
  const where = stepDigits(step.source_step);
  marker.appendChild(el('span', 'sahw-marker__content',
    `${FORK_GLYPH} forked from ${source || '?'} @ ${where || '?'}`));
  if (step.source_step) marker.title = String(step.source_step);
  const clock = clockSpan(step, false);
  if (clock) marker.appendChild(clock);
  if (muted) marker.classList.add('sahw-muted');
  return marker;
}

// The most of one tool result the pane shows. A result is the tool's whole answer and can be a whole
// file — a read of a 224 KB file arrives in one step — and the transcript is a pane, not a pager. So
// the copy stops at whichever cap it reaches first, and the notice says where it stopped and where the
// whole of it is. The record is never cut: the run's log holds every byte and `/report` renders them.
export const RESULT_LINES = 200;
export const RESULT_BYTES = 16 * 1024;
export const byteCounter = new TextEncoder();

/** The head of a word the pane withholds — a call's answer, the text an edit was asked to take away
 * or put there, the command a call was asked to run — and the sentence naming where the pane stopped
 * showing it. The cap is the tool result's discipline: it does not reach the model's own words, which
 * stand whole whatever their length (the reasoning in `reasoningFace`, the speech in `bubble`).
 * The `noun` is the word the sentence names: the cut is the copy's own act, and the sentence says
 * what it cut. */
export function capResult(content, noun = 'result') {
  const lines = content.split('\n');
  const lineCapped = lines.length > RESULT_LINES;
  let text = lineCapped ? lines.slice(0, RESULT_LINES).join('\n') : content;
  let bytes = byteCounter.encode(text).length;
  if (!lineCapped && bytes <= RESULT_BYTES) return { text, notice: '' };
  if (bytes > RESULT_BYTES) {
    // Over the byte cap as well, so cut inside the head of it at the last character the cap still fits
    // whole — this is for the answer that is one enormous line, where the line cap alone would show the
    // whole of it. A character costs a byte at least, so the cut point is inside the first RESULT_BYTES
    // of them, and the search that finds it stays small.
    let low = 0; // the longest prefix known to fit
    let high = Math.min(text.length, RESULT_BYTES) + 1; // one past the window, and never a fitting cut
    while (high - low > 1) {
      const middle = Math.floor((low + high) / 2);
      if (byteCounter.encode(text.slice(0, middle)).length <= RESULT_BYTES) low = middle;
      else high = middle;
    }
    text = text.slice(0, low);
    bytes = low ? byteCounter.encode(text).length : 0;
  }
  return {
    text,
    notice: `truncated: the pane shows the first ${text.split('\n').length} of ${lines.length} lines `
      + `and ${bytes} bytes of this ${noun}; the whole of it is in the run's log and at `
      + `/api/runs/${state.run.id}/report`,
  };
}

/** What a call came back with, in a pre of its own and capped. The pre is a scroll surface, so it
 * wears the sheet's own scrollbar and holds the wheel only until its own edge: the rest of the wheel
 * belongs to
 * the transcript it stands in. */
export function resultBlock(result, touchPath) {
  const box = el('div', 'sahw-result' + (touchPath ? ' sahw-result--file' : ''));
  const raw = result.content === undefined || result.content === null ? '' : String(result.content);
  const shown = capResult(raw);
  if (shown.notice) box.appendChild(el('div', 'sahw-marker', shown.notice));
  box.appendChild(el('pre', 'sahw-pre sahw-result__pre sahw-scroll-area', shown.text));
  // The receipt, when this answer carries one: the model saw this, and the picture is why the sentence
  // says so. With no field the sentence is the whole of the answer — a picture that never travelled
  // stays a sentence about a picture that never travelled, however much it talks about one.
  const seen = filesRow(receiptPaths(result));
  if (seen) box.appendChild(seen);
  // This answer is the one that touched the file: the whole box is the act that opens it in the
  // viewer, and the mark at its right edge is where the act stands — the full path in the hover, the
  // way the row's words already ride.
  if (touchPath) {
    box.addEventListener('click', () => openFile(touchPath));
    const view = el('span', 'sahw-result__view', VIEW_GLYPH);
    view.title = String(touchPath);
    box.appendChild(view);
  }
  return box;
}

/* The one line a call earns beside its name: what it is pointed at, and how far it reaches.
   The value is chosen, never dumped. An argument's value can be a whole file — a `write`'s content IS
   the file, and a row is not a file — so the row names the path the content goes to, the command it
   runs, the pattern it looks for, and the page it reads, and the record keeps the bytes. A value the
   row does carry is put on one line and cut, because the row sits in a transcript. */
export const SUMMARY_TARGET = { // the argument that says what each tool is aimed at
  bash: 'command', calc: 'expr', read: 'path', write: 'path', edit: 'path', ls: 'path',
  grep: 'path', find: 'path', run_log: 'run_id', child_status: 'child_id', child_wait: 'child_id',
  spawn: 'objective',
};
export const SUMMARY_REACH = { // the paging a call carries, named after the target: `read x (offset 40)`
  read: ['offset', 'count'], ls: ['offset'], grep: ['pattern', 'glob'], find: ['pattern'],
  run_log: ['offset'], runs: ['since', 'grep'],
};
export const SUMMARY_CUT = 80; // a command earns eighty characters of a line; the log holds the rest
export const QUALIFIER_CUT = 40;

/** The value on one line, cut with the mark that says so: a bash command can be a whole script. */
export function oneLine(value, cut) {
  const text = String(value).replace(/\s+/g, ' ').trim();
  return text.length > cut ? `${text.slice(0, cut)}…` : text;
}

export function argumentSummary(call) {
  const args = call.args && typeof call.args === 'object' ? call.args : {};
  const key = SUMMARY_TARGET[call.name] || (typeof args.path === 'string' ? 'path' : '');
  const target = key && typeof args[key] === 'string' ? oneLine(args[key], SUMMARY_CUT) : '';
  const reach = [];
  for (const qualifier of SUMMARY_REACH[call.name] || []) {
    const value = args[qualifier];
    if (value === undefined || value === null || value === '') continue;
    reach.push(`${qualifier} ${oneLine(value, QUALIFIER_CUT)}`);
  }
  if (!target) return reach.join(', ');
  return reach.length ? `${target} (${reach.join(', ')})` : target;
}

/** The command this line withholds, or null when the line withholds none. A `bash` call's line shows the
 * record's own word put on one line and cut at the line's own cut, so the line withholds a word the
 * record holds exactly when that face word is not the record word — the command the call was asked to run,
 * as the record holds it, stands in one and not the other. A call that is no `bash` is asked for nothing
 * of this reading, because the words its line owes the face already shows whole; and a `bash` whose word
 * the line shows whole earns no act either, because a line that shows its word whole withholds no word
 * and the act owes the face one to get back. */
export function heldCommand(call) {
  if (call.name !== 'bash' || typeof call.id !== 'string' || !call.id) return null;
  const args = call.args && typeof call.args === 'object' ? call.args : {};
  if (typeof args.command !== 'string') return null;
  return oneLine(args.command, SUMMARY_CUT) === args.command ? null : args.command;
}

export const TOUCHES = { write: 'W', edit: 'E' }; // the two calls whose argument is a file this page can show

export function argumentPath(step) {
  const args = step.args;
  return args && typeof args === 'object' && typeof args.path === 'string' ? args.path : '';
}

/** The ids a step speaks about. A call's `refs` is one id and a summary's is a list; the page reads
 * both as the list of turns this step belongs to, so one shape renders them both. */
export function references(step) {
  if (typeof step.refs === 'string') return [step.refs];
  if (Array.isArray(step.refs)) return step.refs.filter((id) => typeof id === 'string');
  return [];
}

/* The file's own icon, drawn inline: this page carries no icon kit, so the face stands the glyph the way
   it stands its own marks — as elements built one at a time, never as markup written into anything. The
   strokes are `currentColor`, so the icon stands in whatever colour the words beside it stand in, and it
   turns with the theme the page stands in. */
export const SVG_NS = 'http://www.w3.org/2000/svg';
export const FILE_GLYPH = [ // the sheet, the folded corner, and the three lines of words on it, at 24 by 24
  'M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z',
  'M14 2v4a2 2 0 0 0 2 2h4',
  'M10 9H8', 'M16 13H8', 'M16 17H8',
];

export function fileIcon() {
  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('fill', 'none');
  svg.setAttribute('stroke', 'currentColor');
  svg.setAttribute('stroke-width', '2');
  svg.setAttribute('stroke-linecap', 'round');
  svg.setAttribute('stroke-linejoin', 'round');
  svg.setAttribute('aria-hidden', 'true'); // the pull's own name is the word for it
  svg.classList.add('sahw-pull__icon');
  for (const d of FILE_GLYPH) {
    const line = document.createElementNS(SVG_NS, 'path');
    line.setAttribute('d', d);
    svg.appendChild(line);
  }
  return svg;
}

/** One file as the pull that opens it: the file's own icon beside the file's own name, the whole path
 * riding in the hover, and the click asking the preview pane for the file — `openFile`, the one act the
 * mark beside an answer already stands on. A name that two paths share is told apart by that hover,
 * because a pull is a path and not a name. */
export function pull(path) {
  const button = el('button', 'sahw-pull');
  button.type = 'button';
  button.title = String(path);
  button.appendChild(fileIcon());
  button.appendChild(el('span', 'sahw-pull__name', basename(path)));
  button.addEventListener('click', () => openFile(path));
  return button;
}

/** The paths the turn's mutating calls named, in the order the record first stands them, a path named
 * twice standing once: the two calls the face already counts (`TOUCHES`) and the path each one's argument
 * carries (`argumentPath`), the same two readings that earn the mark beside an answer. A call whose
 * argument names no path carries none, and a turn whose calls name no path earns no row at all. */
export function touchedPaths(segment) {
  const paths = [];
  for (const item of segment.items) {
    if (item.type !== 'call' || !TOUCHES[item.step.name]) continue;
    const path = argumentPath(item.step);
    if (path && !paths.includes(path)) paths.push(path);
  }
  return paths;
}

/** The row of pulls a turn earns where its words end: what the turn did to the disk, in one line, one
 * pull per path its calls named. It is the inventory, not a second way in — the mark beside each answer
 * stays where it lives with the answer it opens. A segment with no path to name is no row: the turn's
 * words already take the space it would have stood in, and an operator's stretch holds no calls and a
 * marker no turn, so neither earns one. The row stands for a call whose answer is still away, because the
 * record holds the call before it holds the answer and the row is the record's own reading. */
export function turnFilesRow(segment) {
  const paths = touchedPaths(segment);
  if (!paths.length) return null;
  const row = el('div', 'sahw-pulls');
  for (const path of paths) row.appendChild(pull(path));
  return row;
}

/** One file of words as the chip that opens it: the name, the full path in the hover, and the click that
 * asks the preview pane for the file. The chip stands beside the word that names the file — the
 * operator's line sent with it, or the receipt the answer carries. The files a turn touched are not
 * chipped: they stand as the smaller pull under the turn's words (`turnFilesRow`), and the mark at an
 * answer's right edge stays where it lives, opening the file it belongs to. */
export function chip(path, mark) {
  const button = el('button', 'sahw-chip');
  button.type = 'button';
  button.title = String(path);
  button.appendChild(el('span', 'sahw-chip__name', basename(path)));
  if (mark) button.appendChild(badge(mark, mark === 'W' ? 'new' : 'gray'));
  button.addEventListener('click', () => openFile(path));
  return button;
}

/* --- the chip's two hands: the close, and the toggle ----------------------------------------------------

   A chip is the face's own markup — a `button` wearing `sahw-chip`, built just above and thrown away with
   every redraw of the region it stands in — and two acts are owed to it beyond its own click. The **close**
   is the mark inside it: the chip fades and goes. The **toggle** is a container naming itself
   `data-sahw-chip-toggle`, whose chips say a standing they hold: pressed, or not, and one at a time where
   the container also says `data-sahw-chip-mode="single"`. A pick is refused by anything that prevents the
   `sahw:chip-change` the hand speaks before it moves the pressed word.

   Both hands stand on the document rather than on a chip: a hand hung on each chip would have to be hung
   again on every redraw, and a hand that can be forgotten is a hand a page would lose in silence. What the
   per-subtree walk this came from did at the same moment — a role and a place in the tab order for a chip
   that is not a control — stands down with the walk, named: the chip this page wears is a `button`, which
   owes neither, and the word a pressed chip carries is kept in step by the hand below.
*/
export function wireChipHands() {
  document.addEventListener('click', (event) => {
    const mark = event.target.closest ? event.target.closest('.sahw-chip__close') : null;
    if (!mark || event.defaultPrevented) return;
    const chipNode = mark.closest('.sahw-chip');
    if (!chipNode) return;
    // The fade the chip's own sheet paints, and the taking-out on the far side of it: one 150ms span.
    chipNode.style.transition = 'opacity 150ms ease, transform 150ms ease';
    chipNode.style.opacity = '0';
    chipNode.style.transform = 'scale(0.8)';
    setTimeout(() => chipNode.remove(), 150);
  });
  // A chip that is not a control is reached by the keyboard the container gives it, and `Enter` or `Space`
  // is the click it would have been.
  document.addEventListener('keydown', (event) => {
    const node = event.target;
    if (!node || !node.matches) return;
    if (event.key !== 'Enter' && event.key !== ' ') return;
    if (!node.matches('.sahw-chip') || node.matches('button')) return;
    if (!node.closest('[data-sahw-chip-toggle]')) return;
    event.preventDefault();
    node.click();
  });
  document.addEventListener('click', (event) => {
    if (event.defaultPrevented || !event.target.closest) return;
    const chipNode = event.target.closest('.sahw-chip');
    if (!chipNode) return;
    if (event.target.closest('.sahw-chip__close')) return;   // that mark is the other hand's
    const holder = chipNode.closest('[data-sahw-chip-toggle]');
    if (!holder) return;
    const pressed = !chipNode.classList.contains('sahw-chip--active');
    const choice = new CustomEvent('sahw:chip-change', {
      bubbles: true,
      cancelable: true,
      detail: { chip: chipNode, value: chipNode.textContent.trim(), pressed },
    });
    if (!chipNode.dispatchEvent(choice)) return;   // a hand that refused the pick leaves it as it stood
    if (holder.getAttribute('data-sahw-chip-mode') === 'single') {
      for (const one of holder.querySelectorAll('.sahw-chip--active')) {
        if (one === chipNode) continue;
        one.classList.remove('sahw-chip--active');
        one.setAttribute('aria-pressed', 'false');
      }
    }
    chipNode.classList.toggle('sahw-chip--active');
    chipNode.setAttribute('aria-pressed', String(pressed));
  });
}

/** The copy that stands in front of the file's path: the contents the pane shows, handed to the
 * browser — the one act here that reaches nothing else, no route and no state. A file the pane shows
 * as a picture or a refusal holds no words to copy, so the copy stands down with them. A truncated
 * file's own title says the clipboard takes the head, not the file. */
export function copyButton(file) {
  const claim = file.truncated
    ? 'Copy the head of the file — this answer carries the head, not all of it'
    : 'Copy the file\'s contents';
  const mark = action(COPY_GLYPH, claim, () => {
    navigator.clipboard.writeText(file.content).then(
      () => flashMark(mark, '✓'),
      () => flashMark(mark, '✗'),
    );
  }, 'sahw-act sahw-preview__copy');
  return mark;
}

/** The download that stands behind the copy: the file's own bytes, handed to the browser as the
 * download the file's own name stands in — the whole of the file as it is on the disk, not the head
 * the pane shows. The copy and the download stand and stand down together: a file the pane shows as a
 * picture or as a refusal is not a file the pane reads as words, and the line of the words is where
 * both of them stand. The mark's one flash is the hand's own answer: a check for a hand that stood,
 * a cross for a server that refused it, and back to its own glyph when the moment is out. */
export function downloadButton(file) {
  const mark = action(DOWNLOAD_GLYPH, 'Download the file — the bytes as written, not the pane\'s reading of them', async () => {
    try {
      const reply = await fetch('/api/file?path=' + encodeURIComponent(file.path) + '&download=1');
      if (!reply.ok) throw new Error('the server refused the download');
      handDownload(basename(file.path), await reply.blob());
      flashMark(mark, '✓', DOWNLOAD_GLYPH);
    } catch {
      flashMark(mark, '✗', DOWNLOAD_GLYPH);
    }
  }, 'sahw-act sahw-preview__download');
  return mark;
}

/** The browser's own hand for the bytes the act stands: an object URL the anchor takes down as the
 * download its own name claims. The name the attribute claims is the file's own, and the server's own
 * `Content-Disposition` says the same, so a browser that keeps the one or the other keeps the file's
 * name either way; the URL goes back to the browser where it came from, and the anchor stands nowhere
 * after it has stood. */
export function handDownload(name, blob) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = name;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

/** The mark's own word for a moment: a check for an act that stood, a cross for a browser or a server
 * that withheld it — and back to the mark's own glyph when the moment is out. */
export function flashMark(mark, glyph, restore = COPY_GLYPH) {
  mark.textContent = glyph;
  setTimeout(() => { mark.textContent = restore; }, 1000);
}

/** The line the file's own tools stand in, above its path and over its words: what the pane can do with
 * the file it is reading, and which of the two ways it is reading it. The two hands that take the words
 * go first, then the two acts that reach further than the pane — the machine's own file browser asked to
 * stand on the file itself, and the machine's own opener asked for the file itself — and the reading's
 * toggle at the line's end. A picture and a file the server refused earn no line of them, because none of
 * these is a thing that can be done with words the pane is not holding. */
export function toolsLine(file) {
  const line = el('div', 'sahw-preview__toolsline');
  line.appendChild(copyButton(file));
  line.appendChild(downloadButton(file));
  line.appendChild(selectButton(file));
  line.appendChild(editorButton(file));
  line.appendChild(readingToggle());
  return line;
}

/** The act that asks the machine's own file browser to stand on this file, selected: the file's own path
 * posted to the open route under the select kind, and the answer read from the shape every act answers
 * with. The window is the machine's — the file browser this box owes a directory with, standing in the
 * file's own folder with the file itself marked — and this page neither chooses nor keeps it. `ok` is the
 * window having been asked for; anything else is the machine's own sentence, which stands in the head's
 * note until the file leaves the pane. The pane the face points walks nowhere: the walk is the machine's,
 * not the pane's. */
export function selectButton(file) {
  const claim = 'Select this file in the machine\'s own file browser';
  return action(SELECT_GLYPH, claim, async () => {
    try {
      const answer = await api.open('select', file.path);
      state.fileNotice = answer && answer.ok ? '' : ((answer && answer.reason) || 'the file was not selected');
    } catch (error) {
      state.fileNotice = error.message;
    }
    renderPreview();
  }, 'sahw-act sahw-preview__select');
}

/** The act that asks the machine for the file in an editor: the file's own path posted to the open route
 * under the file kind, and the answer read from the shape every act answers with. Which program opens it
 * is the box's — the default handler the name's kind earns — and this page neither chooses nor remembers
 * it. `ok` is the window having been asked for; anything else is the machine's own sentence, which stands
 * in the head's note until the file leaves the pane. */
export function editorButton(file) {
  return action(EDIT_GLYPH, 'Open the file in the editor this machine owes it', async () => {
    try {
      const answer = await api.open('file', file.path);
      state.fileNotice = answer && answer.ok ? '' : ((answer && answer.reason) || 'the file was not opened');
    } catch (error) {
      state.fileNotice = error.message;
    }
    renderPreview();
  }, 'sahw-act sahw-preview__edit');
}

/** The reading's two ways, in the one control at the tools line's end. It stands the way the reading
 * stands, the way the archive's word follows its state: "preview" while a name's claim is rendered — the
 * document a markdown name is, the highlighting a carried code name earns — and "raw" while the file's own
 * words stand. A press flips the standing and re-renders from the words the pane already holds, so the
 * flip asks nothing of the server in either direction, and the standing is the operator's own: kept in the
 * face's memory, it is still standing on the next load and for the next file. */
export function readingToggle() {
  const claim = state.raw
    ? 'The file\'s own words are standing — press to read it as its name claims it'
    : 'The file is read as its name claims it — press for its own words, plain';
  return action(state.raw ? 'raw' : 'preview', claim, () => {
    state.raw = !state.raw;
    store.write('preview.raw', state.raw);
    renderPreview();
  }, 'sahw-act sahw-preview__mode');
}

/* The file sits in the pane: its name and the close that takes it — with it the column the file
   stood in — the tools the file earns, its full path, and its text; or, for a file whose extension
   claims a picture, the picture itself. No card, no border, no radius, and no padding kept over from
   the box that used to hold it — the box was a frame around a thing that is read, and the pane is
   already the frame around the pane. */
export function renderPreview() {
  nodes.preview.replaceChildren();
  if (!state.file) {
    nodes.preview.appendChild(emptyState(
      'No file selected',
      'A turn that touched a file wears its pull; a sent word or a receipt wears a chip.',
    ));
    return;
  }
  const body = el('div', 'sahw-preview__body');
  // The pane's own head stands in one container, so the room the reading settles on is the
  // reading's own to settle: the head's lines hold their ground together, beside the reading, and the
  // reading's ground is set apart from theirs.
  const header = el('div', 'sahw-preview__header');
  const head = el('div', 'sahw-preview__head');
  head.appendChild(el('div', 'sahw-preview__name', basename(state.file.path)));
  const close = el('button', 'sahw-preview__close', '×');
  close.type = 'button';
  close.title = 'Close the file';
  close.setAttribute('aria-label', 'Close the file');
  close.addEventListener('click', closeFile);
  head.appendChild(close);
  header.appendChild(head);
  // The tools are the reading's own, so a file the pane does not read as words earns no line of them: a
  // picture is painted and a refusal holds no words, and neither can be copied, downloaded, walked to,
  // opened elsewhere, or read another way.
  if (!state.file.error && !state.file.picture) header.appendChild(toolsLine(state.file));
  const pathLine = el('div', 'sahw-preview__pathline');
  pathLine.appendChild(el('span', 'sahw-preview__path', state.file.path));
  header.appendChild(pathLine);
  // The head's quiet note, in the same hand the tree's and the directory pane's stand: it takes no room
  // until there is a sentence to say, and what it says is the machine's own words.
  const note = el('div', 'sahw-preview__note', state.fileNotice);
  note.setAttribute('role', 'status');
  note.setAttribute('aria-live', 'polite');
  header.appendChild(note);
  body.appendChild(header);
  if (state.file.error) {
    body.appendChild(el('div', 'sahw-marker', state.file.error));
  } else if (state.file.picture) {
    // A picture is painted, not read: the same frame, the same route and the same gone-mark a receipt
    // wears, because a file the browser opened and a file the model read are one file.
    body.appendChild(picture(state.file.path));
  } else {
    if (state.file.truncated) {
      body.appendChild(el('div', 'sahw-marker', 'truncated: this answer carries the head of the file, not all of it'));
    }
    if (state.raw) {
      // The file's own words, however its name claims them: no document, no highlighting, the text the
      // server answered standing in the plain pre the pane already stands words in.
      body.appendChild(el('pre', 'sahw-pre sahw-scroll-area', state.file.content));
    } else if (claimedKind(MARKDOWN_KINDS, state.file.path) && window.smd) {
      // The file read as its kind is read: first the document a name claims as markdown, on the ground
      // the pane already stands on; then the language a name claims as code, in the pre the pane
      // already stands words in; and when the name claims none the page can stand — or the page
      // carries none — the words the pane reads today.
      const doc = el('div', 'sahw-doc sahw-prose sahw-scroll-area');
      renderWord(doc, state.file.content, { mode: 'pane', fileDir: directoryOf(state.file.path) });
      body.appendChild(doc);
      if (window.Prism) window.Prism.highlightAllUnder(body);
    } else {
      const language = claimedLanguage(state.file.path);
      if (language && window.Prism && window.Prism.languages && window.Prism.languages[language]) {
        const pre = el('pre', 'sahw-pre sahw-scroll-area');
        pre.appendChild(el('code', 'language-' + language, state.file.content));
        body.appendChild(pre);
        window.Prism.highlightAllUnder(body);
      } else {
        body.appendChild(el('pre', 'sahw-pre sahw-scroll-area', state.file.content));
      }
    }
  }
  nodes.preview.appendChild(body);
}

export function emptyState(title, message, titleClass) {
  const box = el('div', 'sahw-empty');
  box.appendChild(el('p', 'sahw-empty__title' + (titleClass ? ' ' + titleClass : ''), title));
  box.appendChild(el('p', 'sahw-empty__message', message));
  return box;
}
