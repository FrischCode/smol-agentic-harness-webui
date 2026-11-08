/* web/assets/js/composer.js — the composer's own hands; the edit and the composer that returns to it; the
   session's two dials; the trio a working run owes; the compact's mark; the run's numbers; the run's own
   console.

   The composer is markup, and every draw of it reads the state its hands write: the word the operator
   types, the files it travels with, and the edit that returns a word to the composer it left. The dials
   stand on the machine's registry and refuse where the machine refuses; the trio a working run owes
   stands in the row's corner — stop it, steer it, or queue a word for after; the compact's mark says the
   run's conversation in its own word; the run's numbers stand at the composer's left; and the run's own
   console is the operator's channel on the session, standing beside the attach's mark.
   */

import { nodes, store, DEFAULT_LEVEL, LEVEL_NONE, state, number } from './state.js';
import { api } from './wire.js';
import {
  CUT_GLYPH, COPY_GLYPH, QUEUE_GLYPH, STOP_GLYPH, el, rowWorking, stepDigits, parseStep,
  extensionOf, pictureKind, textKind, FORK_GLYPH
} from './components.js';
import { confirmation } from './modal.js';
import {
  action, applyDelta, clearPartials, growTrace, renderChat, renderHeader, renderTree,
  settleStep, treeRendered
} from './trace.js';
import { filterMark, standingMenu, standingName, toggleMenu } from './menus.js';
import { stopRunComposer } from './transcript.js';
import { renderBrowser } from './tree.js';
import { scrollers } from './scroller.js';

// --- the dials' words, and the clocks a spoken switch waits on ----------------------------------------

// The picker's stand when the machine names no model at all: not a model the page invented but the fact
// that a run launched with no `--model` speaks as whatever this box is set to. It is the only entry when
// there is nothing else to offer — before the registry has answered, when the route refused, and when the
// machine declares no reference of its own — because a dial with no entry to stand on wears no word at
// all, and a list the page fills in itself is a list of models this machine does not carry.
export const MACHINE_MODEL = 'machine';
export const MACHINE_LABEL = 'the machine\'s own';

// What the two dials say while the run is generating, and the sentence a switch asked for in that window
// is refused with. It is the server's own sentence for the same moment (`channel.DIALS_DOWN`), because a
// control that said one thing and the route behind it another would leave the operator choosing which one
// to disbelieve.
export const DIALS_DOWN = 'the run is mid-turn — the model and the thinking level switch when it rests';

// The other reason a dial stands down: the machine was read and it named nothing to run on — no registry
// the route could answer, or a registry and no reference either. The picker cannot stand on nothing, and
// the word beside it is what says the nothing is the machine's and not the face's.
export const DIALS_NONE = 'this machine names no model to run on — a run takes whatever it is set to';

// The third reason a dial stands down: the registry was read and it names only what the dial already
// stands on — one model, one level — so the dial owes no choice, and a field that owes no choice owes
// no arrow either. The words are plain fact, the fewest of them: the operator reads them where the
// dial wears them.
export const DIALS_ONE_MODEL = 'one model in the registry';
export const DIALS_ONE_LEVEL = 'one level to stand on';

// The reason the level dial stands nowhere at all: the machine's own declaration withholds it. The
// registry's `think` field is the field a launch rides as `--think`, and a profile that declares no
// level is a model the machine will not think — so the dial that would offer a level the machine
// withholds is not offered at all. Plain fact, the fewest of them, the way the dial's other words are.
export const DIALS_NO_THINKING = 'the machine names no thinking level for the model the dials stand on';

// The word for a switch the run was told and the record has never confirmed: the notice the console leaves
// is the only receipt there is, and a dial that stood on an unconfirmed switch would be the click standing
// in for the record. The dials keep where the record says, which is what this sentence sends for.
export const DIALS_LATE = 'the switch was spoken and the record has not said it landed; the dials stand where '
  + 'the record says';

// How long a spoken switch is waited for, and how often the record is asked whether it landed: the console
// line this face speaks is a child that has to boot, resolve the endpoint, record its notice and go, and
// the dials settle on that notice rather than on the answer the POST brought back.
export const DIAL_SETTLE_MS = 1500;
export const DIAL_SETTLE_TRIES = 40;
export const CONSOLE_SETTLE_TRIES = 30;

// --- the run's state, read the way the server reads it ----------------------------------------------

/* The composer is one control with a handful of faces, and which one it wears is decided from the two
   facts a row of the tree carries: whether the objective wrote its ending, and what the machine says about
   the process behind a log that never wrote one. They are the same two facts the server places a word
   by, so the control is framed by the rule that will answer it — but framed only: the page never
   chooses how a word arrives, it sends the word and the server answers which way it went. The editing
   face is the one exception to that reading, and it is on top of it rather than beside it: the operator
   has already said what this word is for (see `composerFace`).
*/
export const FACES = {
  // A word the operator sends is one objective: the lines inside it are that objective's text, not
  // objectives of their own. The next word is the next objective. The face's own placeholder reads the
  // hint plain — the word that stands where the objective lands — and the steer, which is a word to the
  // run rather than a new objective, keeps its own.
  new: { placeholder: 'Describe a task for a new run' },
  follow: { placeholder: 'Prompt...' },
  steer: {
    placeholder: 'Say a word to the run while it works',
  },
  // The orphan is the follow face with its reason named: the composer says why the run stopped short
  // of its ending and what it offers anyway — the same conversation, from where the record left off.
  orphan: {
    placeholder: 'This run stopped short of its ending — say what to do next; it keeps its log and its grants',
  },
  // The editing face, the one whose line names a step of the record instead of the moment a word
  // lands in: the composer is holding a word the operator already sent, and the send does not open the
  // next objective at the tail, it returns the conversation to that step. Which step is a fact about the
  // edit standing in the composer and not about the run, so the line is built from it — the table holds
  // the shape of the sentence and `faceWords` fills in the number.
  editing: {
    placeholder: (edit) => `Returning to step ${edit.step} — change the word and send it back`,
  },
  // The forking face, the editing face's shape with the opposite outcome: the word typed here is not sent
  // to this run at all, it is the objective a *new* run works on the carried conversation. The line names
  // where the branch carries from, which is the fact an operator cannot get back after the send: the step
  // named by the `⑂` clicked on a row, or the end of the conversation when the act was the row menu's and
  // no step was named.
  forking: {
    placeholder: (fork) => `Forking from ${fork.step ? `step ${fork.step}` : 'the end'} `
      + '— describe what the branch does differently',
  },
};

/** The two lines the composer wears, read out of the table — except for the two faces that name a step of
 * the record, whose lines are built from the aim standing in the composer. `composerFace` answers
 * `editing` or `forking` only while that aim stands, so it is there whenever these lines are asked for.
 * The send's word is not of the table: the button is a send whatever the face it stands in, and the
 * face's own words — the placeholder and the note — say what this send does there. */
export function faceWords(name) {
  if (name === 'editing') return { placeholder: FACES.editing.placeholder(state.edit) };
  if (name === 'forking') return { placeholder: FACES.forking.placeholder(state.fork) };
  return FACES[name];
}


/** Whether a writer holds the opened run's log: its objective has not ended and the machine has not
 * called the process behind it dead — or a follow this page sent is on its way into the log, which is
 * a writer the record has only not stamped yet.
 *
 * The machine's word about the process answers before that belief does: a follow's belief is a stamp the
 * record has only not written yet, and `dead` is a word it only says once the process is gone, so a run
 * the row calls dead is not working however recent the word sent into it was (see `adoptRow`).
 *
 * This is the whole of what the composer's face and the running marker turn on, and it is the same
 * reading of `status` and `live` the channel's rule makes: `dead` is a log nobody is writing, and a
 * log nobody is writing is continued rather than queued to.
 */
export function runWorks() {
  if (!state.run) return false;
  if (state.follow && state.run.live !== 'dead') return true;
  return state.run.status === 'live' && state.run.live !== 'dead';
}

/** Which face the composer wears. The two aims are read first, because they are the operator's own claims
 * about the word in the control: with one standing, what the run's state would have made the next word is
 * beside the point — this word returns to a step, or it branches a new run from one. Otherwise the run's
 * reading answers, as it always did: a new objective, the steer while the run works, the orphan when it
 * stopped short, the follow when it wrote its ending. */
export function composerFace() {
  if (state.edit) return 'editing';
  if (state.fork) return 'forking';
  if (!state.run) return 'new';
  if (runWorks()) return 'steer';
  return state.run.status === 'live' ? 'orphan' : 'follow';
}

/** Whether this step is the record's own copy of the word this page queued as a steer.
 *
 * SAH writes a drained steer twice over: a `command` step naming the action and the block it read, and
 * the block's words themselves as a user message for the model. Either of them is the arrival — and
 * both are matched on the words, because a block that has been sitting in the queue since an objective
 * before this one is somebody else's confirmation, not a receipt for this one.
 */
export function recordsSteer(step, word) {
  const block = step.args && typeof step.args === 'object' ? step.args : {};
  if (step.kind === 'command') {
    return step.action === 'steer' && String(block.text || '').trim() === word;
  }
  return step.kind === 'message' && step.role === 'user' && String(step.text || '').trim() === word;
}

/* --- the edit: the mark on the operator's word, and the composer that returns to it --------------------

   SAH's `--resume <step>` rebuilds the conversation from the prefix ending at a step and detaches what
   came after it — kept in the log, never in a conversation again — and the page's half of that is three
   things and no fourth: the mark on each of the operator's messages, the composer that takes that word
   back to be changed, and a send that posts the changed word with the step it returns to. The log is
   never rewritten by any of it: the mark fills a composer, the route does the cutting, and the detached
   steps stay in the file, which is exactly why the pane mutes them instead of hiding them.

   A fill is not a post, and the clear path is what proves it: `Esc` and the cancel the editing face wears
   both drop the fill and the face, and neither of them has ever reached the route. Where the cut lands in
   the transcript — the marker row and the muted stretch — is the pane's reading of the log it is already
   holding (see `detachedSteps`), so the operator sees the cut whether it came from this page or from
   another window entirely.
*/

/** The mark a user message wears: the row's own small action, quieter than the word it offers to change,
 * and named by the step it returns to — the number is what a cut is aimed with, so it is what the hover
 * says and what the composer's face goes on repeating. A step the page cannot number wears nothing: the
 * cut it would offer is one the route could not be told to make. */
export function editMark(step) {
  const number = stepDigits(step.id);
  if (!number) return null;
  const mark = action(CUT_GLYPH, `Return to step ${number} — change this word and send it back`, () => startEdit(step));
  mark.classList.add('sahw-edit'); // the row's mark, named beside every other row's own affordance
  return mark;
}

/** The fork's icon beside an operator's word: the branch point is the same step the cut is aimed at, and
 * the outcome is a new run rather than a returned conversation, which is what the hover has to say. Like
 * the cut's, it stands only where the page can number the step — `sah fork` wants a step, and a row the
 * page cannot number is a row no route could be told to branch at. */
export function forkMark(step, number) {
  const mark = action(FORK_GLYPH, `Fork from step ${number} — carry the conversation here into a new run`,
    () => startFork(step));
  mark.classList.add('sahw-fork-step');
  return mark;
}

/** The clipboard's icon, on every row that has words: the turn's own text, handed to the browser. It is
 * the one act here that reaches nothing else — no route, no state, no re-render — so it stands on the
 * model's rows as well as the operator's, and on a detached stretch as well as a live one. */
export function copyMark(words) {
  const mark = action(COPY_GLYPH, 'Copy this turn to the clipboard', () => {
    navigator.clipboard.writeText(words).catch(() => {
      state.notice = 'the clipboard would not take the words; the browser refused';
      renderChat();
    });
  });
  mark.classList.add('sahw-copy');
  return mark;
}

/** Take the operator's word back: the composer is filled with it, the face goes on saying that this word
 * returns to step N rather than opening the next objective at the tail, and the cursor goes with the
 * hand. Nothing is posted here and nothing is cut. A second mark clicked while an edit stands aims the
 * edit elsewhere — the control holds one word at a time, so it holds one return. */
export function startEdit(step) {
  const number = stepDigits(step.id);
  if (!number) return;
  if (state.queued) {
    state.notice = 'the queue stands — release it first';
    renderChat();
    renderComposer();
    return;
  }
  state.edit = { id: step.id, step: number };
  if (composer) composer.setDraft(typeof step.text === 'string' ? step.text : '');
  focusComposer();
  renderComposer();
}

/** The composer's clear path, the edit's share of it: the fill goes, the editing face goes with it,
 * nothing is posted and nothing is cut. Both hands that reach for it end here — `Esc`, and the cancel the
 * face wears in the send's own ground — because the way out of an edit is one act however it is asked for.
 * A draft the operator typed themselves is not this function's to take: with no edit standing the page leaves the
 * composer's words where they are, which is what it did before the edit existed. */
export function clearEdit() {
  if (!state.edit) return;
  state.edit = null;
  if (composer) composer.clearDraft();
  renderComposer();
}

/** Take the composer's clear path, the fork's share of it: the face goes, nothing is posted and no run is
 * started, and the words the operator typed stay where they are — an objective that was never sent is
 * theirs, and the cancel drops the aim at a step, not the sentence aimed at it. */
export function clearFork() {
  if (!state.fork) return;
  state.fork = null;
  renderComposer();
}

/** Stand a fork up in the composer, aimed at `runId` and — when one was named — at the step the carried
 * prefix ends at. The editing face is dropped on the way, because the control holds one aim at a time:
 * the word about to be sent either returns to a step of this run or branches a new one, never both.
 *
 * Two hands raise it: the `⑂` on a row names the step it stands on, and the row menu names none, because
 * its fork carries the whole conversation. Nothing is posted here — the objective still has to be typed
 * and sent, which is the difference between an act and an intent. */
export function startFork(step) {
  if (!state.run) return;
  armFork(state.run.id, stepDigits(step.id));
}

export function armFork(runId, number) {
  if (state.queued) {
    state.notice = 'the queue stands — release it first';
    renderChat();
    renderComposer();
    return;
  }
  if (state.edit) {
    state.edit = null;
    if (composer) composer.clearDraft();   // the word the editing face was handed is not this face's
  }
  state.fork = { source: runId, step: number || '' };
  focusComposer();
  renderComposer();
}

/** The keyboard's share of the clear path. `Esc` answers the layer on top of the page, and the two layers
 * this page floats have their own claims on it — the row's menu returns the keyboard to its row, and the
 * confirmation is a modal the browser cancels itself — so this listener asks only while an edit or a fork
 * stands and neither of them is standing. */
export function wireComposerClear() {
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape' || (!state.edit && !state.fork) || standingMenu || standingName) return;
    if (confirmation.dialog && confirmation.dialog.open) return;
    event.preventDefault();
    if (state.edit) clearEdit();
    else clearFork();
  });
}

// --- the operator's hands: the files a word travels with ----------------------------------------------

/* A file cannot ride a word: every channel this page has — the spawn's task, the follow's, the steer a
   working run picks up at its next turn boundary — carries text. So the bytes go to the server and the
   word carries the line the server writes for them, one per file, beside the operator's own sentence.
   That is why this page never names a file the run will read, never appends the line, and never learns
   where the file landed: the routes write the file into the run's estate and the line into the word, and
   the pane reads the line back as the file it names (see the face's eyes).

   What the page does own is the moment between the hand and the send. A file the picker chose, the
   clipboard carried, or the hand dropped on the page is held as the browser handed it and shown
   beside the draft, so what will ride the word is visible before it goes; its bytes are read at the send
   itself, because a word never sent has cost nothing and a send that was refused keeps its files the way
   it keeps its draft.

   The picker, the paste, and the drop are one path with a different hand at the front of it, and one gate
   at the end: a file is taken when this box can show it — a kind it paints or a kind it reads as words. A
   file of neither kind is left where it is, because the face would stand a tile for a thing it then has
   nowhere to open; a pasted *sentence* is left to the browser, which is the difference between a clipboard
   holding a file of words and one holding words; and a drag that carries no file — a text selection, an
   address — is the browser's own business on every path, the drop the textarea makes of a text standing
   as it was made. */
export const PICTURE_MIMES = ['image/png', 'image/jpeg', 'image/gif', 'image/bmp', 'image/webp'];

// The kinds a browser reliably names for itself when a file of words is handed over. Most of the text
// kinds this box offers are claimed by their extension rather than by a type — a clipboard or a platform
// too often reports a text file as no type at all — so this list is the type half of one question, and
// `TEXT_KINDS` (the face's eyes) is the name half.
export const TEXT_MIMES = ['text/plain', 'text/markdown', 'text/x-python', 'text/csv'];
// The room the tray holds: five files ride a word, and a sixth is a file the operator must be told about
// rather than one that vanishes — the number the note's own words are cut to.
export const ATTACH_MAX = 5;

// The mark the page wears while a file drag is over it: a veil above everything the page stands, so the
// hand sees the page is taking the file before it lets go.
export const DROP_MARK = 'sahw-drop';

/** Whether a kind — a type, a name, or both from the same file — is one this box answers as a picture:
 * the browser's own word for what it holds, or the extension the name claims. */
export function isPictureKind(type, name) {
  if (typeof type === 'string' && PICTURE_MIMES.includes(type.toLowerCase())) return true;
  return !!pictureKind(typeof name === 'string' ? name : '');
}

/** The same question about words: the type the browser names, or the extension the name claims, because a
 * file off a clipboard often arrives naming no type and carrying its whole claim in its name. */
export function isTextKind(type, name) {
  if (typeof type === 'string' && TEXT_MIMES.includes(type.toLowerCase())) return true;
  return !!textKind(typeof name === 'string' ? name : '');
}

/** Whether a file rides a word at all: a kind this box paints, or a kind it reads. One gate for the picker
 * and the paste, and the reason the write path was never asked which of the two it was writing. */
export function isFile(file) {
  return !!file && (isPictureKind(file.type, file.name) || isTextKind(file.type, file.name));
}

/** What the clipboard holds that is a file of either kind, and none of what it holds that is not. A file
 * arrives as a `file` when the application that put it there thought of it as one, and only as an `item`
 * when it did not, so both are asked. Words typed into the clipboard are strings and are passed over: this
 * page takes no part of a pasted sentence and leaves the cursor where it was. */
export function clipboardFiles(bag) {
  if (!bag) return [];
  const held = Array.from(bag.files || []).filter(isFile);
  if (held.length) return held;
  for (const item of bag.items || []) {
    if (item.kind !== 'file') continue;
    const file = item.getAsFile();
    if (file && isFile(file)) held.push(file);
  }
  return held;
}

/** The bytes as the route wants them: base64. Chunked, because a picture is a file and one
 * `fromCharCode` call over a megabyte of them is an argument list no engine promised anything about. */
export function base64(bytes) {
  let binary = '';
  for (let at = 0; at < bytes.length; at += 0x8000) {
    binary += String.fromCharCode.apply(null, bytes.subarray(at, at + 0x8000));
  }
  return btoa(binary);
}

/** Stand the files the browser just handed over at the draft's edge, and answer whether anything was
 * taken — which is how the paste knows the event was the page's to handle. The room is five files;
 * the surplus of a hand the room cannot hold is counted, so a hand that overreaches the room knows by
 * how much it overreached. */
export function takeFiles(files) {
  const taken = Array.from(files || []).filter(isFile);
  if (!taken.length) return false;
  const room = Math.max(0, ATTACH_MAX - state.attachments.length);
  const riding = taken.slice(0, room);
  state.attachRefused = taken.length - riding.length;
  for (const file of riding) {
    // Only a picture is owed an object address, because only a picture is painted: a thumb is made from
    // the file's own bytes and not from the route, since until the send there is no file for the route to
    // read and a frame that fails beside a draft says the send already happened. A file of words is
    // wearing its own kind as a word, and an address it never had is one fewer thing to hand back.
    const thumb = isPictureKind(file.type, file.name);
    state.attachments.push({
      name: String(file.name || 'file'),
      file,
      url: thumb ? window.URL.createObjectURL(file) : '',
    });
  }
  renderAttachments();
  renderComposer(); // the note is where the surplus stands, and the note rides renderComposer
  return true;
}

/** The tray beside the draft: one tile per file standing attached — its face, its name, and the mark
 * that takes it off again. What will ride the word is shown before the word goes out, and an attachment
 * that cannot be taken back off is a mistake that would have to be sent. An empty tray is no tray at all,
 * so a composer with nothing attached is the composer it was before attachments. */
export function renderAttachments() {
  nodes.attachTray.replaceChildren();
  state.attachments.forEach((item, index) => {
    const tile = el('div', 'sahw-attachment');
    // The name the tile cuts is the name the record keeps: the hover is where the whole name stands.
    tile.title = item.name;
    tile.appendChild(tileFace(item));
    tile.appendChild(el('span', 'sahw-attachment__name', item.name));
    tile.appendChild(action('✕', `Take ${item.name} off this word`, () => dropAttachment(index)));
    nodes.attachTray.appendChild(tile);
  });
}

/** The tile's face, which is the one place the two kinds look different: a picture wears the thumb its own
 * bytes paint, and a file of words wears the extension it claims, as a word, in the box the thumb fills —
 * the tile's shape is the tile's shape either way. No frame is stood in for words: a text file has no
 * thumb to fail, and a broken frame beside a draft would say the send had already gone out wrong. */
export function tileFace(item) {
  if (isPictureKind(item.file.type, item.name)) {
    const thumb = el('img', 'sahw-attachment__thumb');
    if (item.url) thumb.setAttribute('src', item.url);
    thumb.setAttribute('alt', '');
    return thumb;
  }
  // The extension as the name claims it, lowercased; a name the browser handed over without one wears the
  // kind the gate took it for, because that is all the name has to say about itself.
  return el('span', 'sahw-attachment__mark', extensionOf(item.name) || 'text');
}

/** One file off the word. The bytes go with the address its thumb was painted from: an address the
 * browser revokes only when this page tells it, and a page that forgot would be holding a file by it. A
 * file of words never had one, and owes nothing back. */
export function dropAttachment(index) {
  const [gone] = state.attachments.splice(index, 1);
  state.attachRefused = 0; // the operator's act supersedes the last hand's surplus
  if (gone && gone.url) window.URL.revokeObjectURL(gone.url);
  renderAttachments();
  renderComposer();
}

/** The standing files as the routes read them: each with the name it arrived with and its bytes,
 * base64. Read at the moment of the send, which is the moment the bytes being spoken of are settled. */
export async function attachmentBodies() {
  const bodies = [];
  for (const item of state.attachments) {
    bodies.push({ name: item.name, bytes: base64(new Uint8Array(await item.file.arrayBuffer())) });
  }
  return bodies;
}

/** The word went out and its files went with it: the page keeps neither the bytes nor the addresses. */
export function clearAttachments() {
  for (const item of state.attachments) {
    if (item.url) window.URL.revokeObjectURL(item.url);
  }
  state.attachments = [];
  state.attachRefused = 0; // the word went out with its files: the surplus stood beside a word that is gone
  renderAttachments();
}

/** Whether a drag carries a file: the `Files` type is the browser's own word for a file drag, and a drag
 * of anything else is left to the browser on every path — the way a pasted sentence is — because the drop
 * the textarea makes of a text standing at its cursor is the browser's, not the page's. */
export function isFileDrag(event) {
  const types = (event.dataTransfer && event.dataTransfer.types) || [];
  return Array.from(types).includes('Files');
}

/** The third hand: the file the operator drops anywhere on the page, on the one gate the picker and the
 * paste already stand at. The page takes the decision in the capture phase, on the window — before any
 * control under the hand can answer for the drag — so the page's answer stands whatever the control the
 * hand happens to be over makes of the drag, and the window keeps the browser from the other thing a
 * dropped file invites: opening it as a page. The page wears the mark — a veil above everything it
 * stands, pointer-events off, so nothing the page stands can stand over it and nothing it covers loses
 * the hand — while a file drag is over it, and the mark leaves with the drop or with a leave the hand
 * has nowhere to land: `relatedTarget` is the
 * element the hand is going to, and a leave with none is a leave of the page. A drag of anything but
 * files is the browser's on every path: no mark, no `preventDefault`, and the textarea's own drop stands
 * as it was made. A file of neither kind is the gate's answer, as it is for the picker and the paste: the
 * drop is the page's to handle so the browser makes nothing of it, and the tray stays the way it was. */
export function wireDrop() {
  const page = document.body;
  window.addEventListener('dragover', (event) => {
    if (!isFileDrag(event)) return;
    event.preventDefault();
    page.classList.add(DROP_MARK);
  }, true);
  window.addEventListener('drop', (event) => {
    if (!isFileDrag(event)) return;
    event.preventDefault();
    page.classList.remove(DROP_MARK);
    takeFiles(event.dataTransfer.files);
  }, true);
  window.addEventListener('dragleave', (event) => {
    if (!isFileDrag(event)) return;
    if (event.relatedTarget) return;
    page.classList.remove(DROP_MARK);
  }, true);
}

/** The three hands, wired once: the picker, the page's own paste handler, and the file the hand drops.
 * The picker is reset after a file is taken from it, because a control that still holds the last choice
 * will not report choosing that file again — and a file the operator picks twice is a file they mean to
 * send twice. */
export function wireHands() {
  nodes.attach.addEventListener('change', () => {
    if (takeFiles(nodes.attach.files)) nodes.attach.value = '';
  });
  document.addEventListener('paste', (event) => {
    // Words are left to the browser and to whatever holds the cursor: this handler has no opinion about a
    // pasted sentence and takes none of it — no tray entry, no `preventDefault`. A clipboard carrying a
    // file of a kind this box answers has that file taken out of it, and only then is the event the page's
    // to call handled.
    if (!takeFiles(clipboardFiles(event.clipboardData))) return;
    event.preventDefault();
  });
  wireDrop();
}

// --- the steps the page takes --------------------------------------------------------------------

/* Two debts a frame can settle, because the stream's two frames change two different things.

   A `step` is the record settling a line: the segments the transcript is built from changed, and the
   surface they are built out of is rebuilt. A `delta` is a word arriving into the turn being written: it
   changes the face that turn stands in and leaves the settled record standing, and what it owes is that
   row grown where it stands — or, when it changed no face the pane shows, nothing at all.

   The rebuild pays for the faces as it goes, so a batch holding a step rebuilds and does not also grow:
   the heavier debt is the batch's debt. The header and the composer keep the pass that stands them today —
   they are small regions, and the transcript is the one whose cost is proportional to the record. */
export let frame = 0;
export let frameOwesPane = false;

/** The render pass a stream frame asks for: the whole pane when the frame settled a line of the record,
 * the trace's own faces when it only grew a word. One frame per batch of arrived frames, however many
 * arrived — see the module's second rule — settled at the heavier of the two debts the batch holds. */
export function askFrame(owesPane) {
  frameOwesPane = frameOwesPane || owesPane;
  if (frame) return;
  frame = requestAnimationFrame(() => {
    frame = 0;
    const pane = frameOwesPane;
    frameOwesPane = false;
    renderHeader();
    // The transcript's region pays for what the batch carried. `growTrace` answering `true` is a growth
    // that moved a shape the rebuild reads — a face standing up, an arriving answer needing its box — and
    // that one occasion the frame cannot serve, it hands back to the rebuild.
    if (pane || growTrace()) renderChat();
    // The composer's frame turns on the arriving record too: the face the run's new state wears and the
    // trio the send owes are read off it, and a queued word whose ride has come due is delivered.
    renderComposer();
  });
}

/** The pass a step owes: the record settled a line, and everything built out of the record is stood again. */
export function scheduleRebuild() {
  askFrame(true);
}

/** The pass a trace fragment owes: the turn being written, grown in the row it stands in, and no settled
 * row touched for it. */
export function scheduleTrace() {
  askFrame(false);
}

/** Whether the tree the server just answered differs from the one the page already holds: a run that
 * appears or leaves, a row that moves its stamp or its word, or a row the machine re-answers (its live
 * key, or the number rebirthed the row carries beside a dead one). The order is the server's own, so two
 * trees equal in every fact are equal row for row, and one
 * that differs anywhere is owed the re-render. It is the gate that keeps the working mark from resetting:
 * a run that works steadily answers the same row at every half second, and a row that is the same is not
 * redrawn, so the spinner keeps its spin instead of restarting on a render that would say nothing new.
 */
export function treeMoved(prev, next) {
  if (prev.length !== next.length) return true;
  for (let i = 0; i < prev.length; i += 1) {
    const a = prev[i], b = next[i];
    if (a.path !== b.path || a.runs.length !== b.runs.length) return true;
    for (let j = 0; j < a.runs.length; j += 1) {
      const r = a.runs[j], s = b.runs[j];
      if (r.id !== s.id || r.ts !== s.ts || r.status !== s.status || r.reason !== s.reason
        || r.model !== s.model || r.task !== s.task || r.name !== s.name) return true;
      if (('live' in r) !== ('live' in s) || r.live !== s.live) return true;
      // The reason beside a dead verdict is one of the row's words: the number rebirthed is what the row's
      // hover has to say about a run the machine's own number answers live for, and it arrives and leaves on
      // a row whose `live` never moved.
      if (r.reborn !== s.reborn) return true;
    }
  }
  return false;
}

export async function refreshTree() {
  const answer = await api.runs();
  // The first listing is always drawn — it is the page drawing its tree at all, and an empty tree is
  // still a face the page owes ("No runs yet") — while a later one that answers the rows the page
  // already holds says nothing new and is not redrawn, so the working mark keeps turning rather than
  // restarting on a render that would draw the rows it already draws.
  const moved = !treeRendered || treeMoved(state.workspaces, answer.workspaces);
  state.workspaces = answer.workspaces;
  const changed = adoptRow();
  // Nothing the record has to say moved: the tree stands as it is, and the working mark keeps turning
  // rather than restarting on a render that would draw the rows it already draws.
  if (!moved && !changed) {
    treePulse();
    return;
  }
  // The pulse's tick checked for a standing layer before it asked, and a layer can open in the gap the
  // question takes: the listing is about to replace the row the layer stands on, and the render would
  // take it with its row, so a listing that arrives while one is standing keeps what it learned and skips
  // the render. The tree is at most half a second stale, and the row the layer's act reaches is still the
  // row it stands on, which is all the act needs — and a word being typed into a name is least of all a
  // render has any business moving out from under the hand typing it.
  if (standingMenu || standingName) {
    if (changed) { renderHeader(); renderChat(); renderComposer(); }
    return;
  }
  renderTree();
  treePulse();
  if (changed) {
    renderHeader();
    renderChat();
    renderComposer();
  }
}

// The tree re-lists itself while anything in it works, at the half second the page already owes a
// working run: the spinner is the machine's word rendered, and a word that stops being true stops
// being worn on the next listing. And it re-lists itself while nothing works, at the lazy sweep the
// idle tree still owes: a run launched beside the face (the bat's launch stands in the runs root,
// not in the page) has to stand in the listing without the operator's re-ask — the stand-down the
// timer kept before was the face going blind to its own machine's work. The cadence is fixed at the
// moment the timer is stood, so a move between working and idle re-stands it.
export let treeTimer = 0;
let treeCadence = 0;   // the pace the standing timer owes — a move of pace is a re-stand, not a re-tune

export function treePulse() {
  const anyWorking = state.workspaces.some((ws) => ws.runs.some(rowWorking));
  const cadence = anyWorking ? POLL_MS : POLL_MS_IDLE;
  if (treeTimer && treeCadence === cadence) return;   // the standing timer owes the pace it stands at
  if (treeTimer) clearInterval(treeTimer);
  treeTimer = setInterval(() => {
    // A layer stands on a row the re-render would replace — a menu, or a name being typed — and the
    // render takes the layer with its row: the listing skips the tick a layer stands, and the row
    // catches up on the next one, which the close does not stop. The spinner it is there to correct
    // keeps turning either way.
    if (standingMenu || standingName) return;
    refreshTree().catch(() => {});
  }, cadence);
  treeCadence = cadence;
}

// The operator looking again is the re-ask the hidden tab owes the page: a tab hidden while a run
// started or ended keeps the belief it held when it went out — an idle belief owes no polling, and the
// polling is what corrects the belief — so the correction the hiding withholds, the eyes returning
// give: one `refreshTree`, from which the standing rule resumes on the corrected belief (a run it
// learns working stands the timer at the working pace, one it learns idle at the lazy sweep), and the open run's state
// rides the same re-ask through the refresh's own `adoptRow`. The standing rule itself stands: the
// re-ask asks once, and what the answer says is what the timer then does.
export function wireVisibility() {
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState !== 'visible') return;
    refreshTree().catch(() => {});
  });
}

/** Take the opened run's state from the row the tree just answered with, and say whether it moved.
 *
 * The row is the record read *now*: what the page holds is the record read when the run was opened plus
 * whatever its stream has said since, so a row that has moved is the page learning that the run it is
 * showing was followed up somewhere else, or ended while nobody was looking. A run the row does not hold
 * keeps what it had — a listing with nothing to say about a run is not a verdict about it. And while a
 * follow this page started is still on its way the row is read for one fact only: whether the machine has
 * called the process gone. A row can lag a start — a relaunch that has not written its first line answers
 * from a log the new objective had not reached, and the page's own belief about the word it just sent is
 * the newer fact, so that belief stands and the row is not adopted — and it cannot lag a death, because
 * `dead` is said only after the process was called gone: settled fact, not a record still owed, so the
 * death is adopted and the face takes the reading the record already names. While such a death stands the
 * row is the fact being answered for the process, so the row keeps being read until its word about the
 * process changes again — the death holds only as long as the machine's word does, and the belief the
 * follow stated is what the page holds the moment it stops. The one thing a listing that stopped naming
 * the run does settle is the aim at its record: the word an aim posts goes to a run folder, and a folder
 * the record no longer names is a word the aim cannot post, so the edit and the fork aimed at its steps
 * go with the run (the words stay where the face stands them).
 */
export function adoptRow() {
  if (!state.run) return false;
  const found = findRun(state.run.id);
  if (!found) {
    // The record no longer holds the run the pane stands over. The run's own reading keeps what it had
    // — a listing with nothing to say about a run is not a verdict about it — but an aim is an act, not
    // a reading: the word an aim posts goes to a run folder the record no longer names, so the aim goes
    // with the run, the way the run's switch already stands it down. The words the operator typed stay
    // where a run's face stands them: the aim goes, and the words do not.
    if (state.edit || state.fork) {
      state.edit = null;
      state.fork = null;
      renderComposer();
    }
    return false;
  }
  // The asymmetry, and it is the whole of the gate: the death is adopted while the follow stands, the
  // start is not. `dead` is the machine's word on the process, and a row that carries it is not a guess
  // the record still owes — so the face's optimistic belief yields to it, and the row goes on being read
  // for as long as that word stands, which is the only thing the adopted death was ever standing on.
  const dead = found.row.live === 'dead';
  if (state.follow && !dead && state.run.live !== 'dead') return false;
  const next = {
    id: state.run.id,
    // The model the page already has came from the log's own `started` line, which names the objective
    // in flight; the row names the run. Where they differ, the log is the one being shown.
    model: state.run.model || found.row.model,
    status: found.row.status,
    live: found.row.live || '',
    // The fork is the one fact a run cannot outgrow, so the row's answer is taken whole: a listing that
    // has stopped naming the source would be a listing about a different run.
    fork: found.row.fork || null,
  };
  const changed = next.status !== state.run.status || next.live !== state.run.live;
  state.run = next;
  // A run that is not working takes the composer's note with it: a word still sitting in its queue is
  // owed to the next resume, and this control no longer claims the boundary is where it will land.
  if (!runWorks()) state.steer = '';
  // A death the follow stands to says something about the log as well as the process: `dead` is read only
  // off a run whose newest objective wrote no ending, so the record can hold a tail this pane has never
  // been shown — the objective the follow started, which began and died inside one of the wait's own
  // polls, and which the page's own stop may have stood before the row caught up. With no ending on the
  // record there is no ending for a replay to stop at, which is the one thing the wait is there to hold
  // off, so the stream is asked: the pane reads the record the death leaves, and the wait goes on waiting,
  // an objective that arrives after all still being followed the way it always was. A stream already
  // standing needs no second asking — it has been following the log the whole time.
  if (state.follow && dead && !state.stream) openStream();
  return changed;
}

/** The newest run in the tree, by the same pair the server sorted on: a stamp and, under a tie, the
 * id. The page's notion of newest has to be the server's, or the run it opens is not the last one. A
 * run the operator put out of sight is not the run to open next, newest or not. */
export function newestRun() {
  let best = null;
  for (const workspace of state.workspaces) {
    for (const row of workspace.runs) {
      if (state.archived.has(row.id)) continue;
      const key = `${row.ts} ${row.id}`;
      if (!best || key > best.key) best = { key, workspace: workspace.path, row };
    }
  }
  return best;
}

/** The run to open when the page loads: the one the face remembers, so long as the tree still lists it,
 * and the newest run otherwise. A remembered run that has stopped listing is a run the record no longer
 * holds, and the face lets it go: the fallback is exactly what this page would have opened had it never
 * been told about the one it is forgetting. */
export function rememberedRun() {
  const id = store.read('opened', '');
  const found = typeof id === 'string' && id ? findRun(id) : null;
  return found || newestRun();
}

export function findRun(runId) {
  for (const workspace of state.workspaces) {
    for (const row of workspace.runs) {
      if (row.id === runId) return { workspace: workspace.path, row };
    }
  }
  return null;
}

/** Open a run: show what the tree knows, then follow the log and let the log overrule it.
 *
 * The pane starts empty and every step arrives from the stream, whether the log is finished and being
 * replayed or still being written. `state.seen` is the pane's memory of which steps it has counted, and
 * it is emptied here along with the pane: a run is a record of its own, and the ids that name one run's
 * steps say nothing about another's.
 */
export function openRun(row, workspacePath) {
  closeStream();
  state.run = {
    id: row.id, model: row.model, status: row.status, live: row.live || '', fork: row.fork || null,
  };
  state.steps = [];
  state.seen = new Set();
  state.notice = '';
  state.follow = '';
  state.steer = '';
  // A standing edit or fork is an aim at one run's record, and these are another run's steps. The words
  // in the composer are the operator's and stay, but the face they were wearing goes with the run.
  state.edit = null;
  state.fork = null;
  // A word riding the queue belongs to the run this page leaves: the face that opens another run takes
  // the word back into the control rather than posting it to a run the operator is no longer looking at.
  if (state.queued) { if (composer) composer.setDraft(state.queued); state.queued = null; lockInput(false); }
  state.changes = new Set(); // and so does a change that was asked for: the ids here are this log's
  state.commands = new Set(); // and so does a command that was asked for, for the same reason
  // The dials are the run's own, and the row already carries the two facts of the record they stand on:
  // the model the run talks to and, when a switch moved it, the address it was moved to. The level is not
  // on the row, so the dial wears the face's own default until the record is read — one request, and the
  // same reading every later settle goes through.
  state.dial.name = row.model || '';
  state.dial.endpoint = row.endpoint || '';
  state.dial.think = DEFAULT_LEVEL;
  state.dial.asked = null;
  state.dial.word = '';
  if (workspacePath) state.expanded.add(workspacePath);
  // The face remembers which run this was, and that its workspace was open to show it: a reload opens
  // the same run in the same shape, and lets go of this one the moment it stops listing.
  store.write('opened', row.id);
  store.write('expanded', Array.from(state.expanded));
  renderHeader();
  renderTree();
  renderChat();
  renderComposer();
  paintDials();
  openStream();
  askDials(row.id);
}

/** Follow the opened run's log with one connection, and stop following it when the objective ends.
 *
 * One connection, two files: the route reads the record and the run's trace and sends the first as `step`
 * frames and the second as `delta` frames, and this is where both are taken up. The order is the route's
 * and the pane relies on it — the record's frames of a poll come before that poll's fragments, so a face
 * grows towards a step that has already been seen coming and is settled by the step that follows.
 *
 * The stream closes on an `ended` line — which is now *one objective's* end, not the log's — and what
 * re-opens it is the next objective this page started (see `awaitObjective`), not a connection held
 * open through a run's silence. Re-opening is safe because every step carries the id the log gave it: a
 * stream asked again replays the whole record from the beginning, and the pane keeps what it shows
 * instead of drawing the same step twice beside itself. Live and replay stay one rendering.
 */
export function openStream() {
  closeStream();
  // The run this stream is opened for, held here: the frame that ends it carries no run id — the log it
  // replays is the identity — so this is the only place that knows which run an ending belongs to.
  const runId = state.run.id;
  const source = new EventSource(`/api/runs/${encodeURIComponent(state.run.id)}/stream`);
  state.stream = source;
  source.addEventListener('step', (event) => {
    const step = parseStep(event.data);
    if (!step) return;
    if (step.id) {
      if (state.seen.has(step.id)) return; // a replay catching the pane up, not a line new to it
      state.seen.add(step.id);
    }
    state.steps.push(step);
    // The trace's face for this step, if one was standing: the assistant turn settles the prose that grew
    // into it, and an answer settles the output that grew into its call. The step is pushed first, because
    // the settlement is the record taking over what the fragment was promising.
    settleStep(step);
    // The run's own first step names the model it is answering with, which is the name the header
    // and every assistant turn carry.
    if (step.kind === 'started' && step.model) state.run.model = step.model;
    // The operator's channel, arriving in the record: a console line that switched one of the session's
    // dials. This page need not have asked for it — the run's own prompt answers to the same line — and
    // what it does here is ask the record what the dials stand on, so the controls follow what the log says
    // rather than what this page last clicked. A switch this page spoke and the record has not made true is
    // the one case a word is owed, and the word is the record's own: the console writes its refusals beside
    // its switches, in the same shape, and it is the sentence the operator has to read to know which
    // happened.
    if (step.kind === 'notice' && step.issuer === 'operator' && step.subject === 'command') {
      const line = String(step.text || '');
      // When the record wrote this line. A log replays whole when a run is opened, so the lines arriving
      // here are not all new: a switch spoken a moment ago walks past every notice the session already
      // holds, and a face that read one of those as the answer to it would stand a sentence about the last
      // act in the note hand and give up on the one it asked for.
      const written = Date.parse(String(step.ts || ''));
      readDials(runId).then(() => {
        if (!state.run || state.run.id !== runId || !state.dial.asked) return;
        if (!Number.isNaN(written) && written < state.dial.asked.at) return;
        // The record answered, and it did not say the switch: the refusal stands in the note hand and the
        // dials keep where the record says they stand, which is what it said before this line arrived.
        state.dial.asked = null;
        state.dial.word = line;
        paintDials();
        renderComposer();
      });
    }
    state.notice = '';
    if (state.steer && recordsSteer(step, state.steer)) state.steer = '';
    scheduleRebuild();
  });
  source.addEventListener('delta', (event) => {
    // The trace's frame: one line of `<run-dir>/live.jsonl`, raw, in the same line discipline as the step
    // frames. It grows the face it names and nothing else — the record still holds every word of it, and
    // the step that settles the face is coming. A fragment already on the wire when the operator opened
    // another run belongs to a turn this pane stopped watching, and grows nothing here.
    if (!state.run || state.run.id !== runId) return;
    applyDelta(parseStep(event.data));
    // The frame pays for what it carried: the face this fragment grew, in the row that face stands in.
    // A fragment the pane shows nothing for — the turn the record closed a moment ago, a call this pane
    // has no row drawn for — grows nothing, and the frame that runs for it rebuilds nothing either.
    scheduleTrace();
  });
  source.addEventListener('ended', () => {
    // Close it here: a stream the server has finished is a connection EventSource would otherwise
    // re-open, and a re-opened stream replays the whole log a second time into this run's steps.
    source.close();
    // An ending belongs to the run its stream was opened for. A frame already on the wire when the
    // operator opened another run arrives after the face has moved on, and the run standing open now is
    // not the one that ended: it keeps the face it had — working, if that is what it was doing — and its
    // own stream stays held and unread. The ending that belongs to it is another frame, and that one ends it.
    if (!state.run || state.run.id !== runId) return;
    state.stream = null;
    // The record settles everything, and this frame is the record saying it is whole: an in-flight face
    // that outlived the stream would be the pane holding a word no step ever claimed, standing under a
    // transcript that already has the turn it was promising. Whatever the trace grew is now either settled
    // above or was never going to be, and the face stops growing.
    clearPartials();
    // One objective's end: the composer turns back to the follow, and a word the queue never got is
    // owed to the next resume rather than still pending at this composer.
    state.run.status = 'ended';
    state.run.live = '';
    state.follow = '';
    state.steer = '';
    // The dials come back up with the ending: the sentence they stood down behind was this objective's, and
    // a word left standing there would go on refusing a switch the record has just made room for.
    if (state.dial.word === DIALS_DOWN) state.dial.word = '';
    renderHeader();
    renderChat();
    renderComposer();
    // The tree row still says what it said when the tree was read; the ending is the one fact the
    // stream just changed, so the tree is asked again rather than left to contradict the header.
    refreshTree().catch(() => {});
  });
  source.addEventListener('error', () => {
    // The stream died. The connection is done for whatever the cause — the server went away, or the
    // run it served no longer stands — and the asking again is this face's own act, not the browser's:
    // a re-open the face cannot steer is a re-open the face cannot answer for, because at the moment
    // the browser gives up the two causes it refused — the server that restarted and the run that was
    // deleted — stand as the same silence. The replay the re-open carries is the one the pane already
    // answers for: every step stands with the id the log gave it, and the pane keeps the steps it
    // already shows instead of drawing the same turn twice beside itself.
    source.close();
    state.stream = null;
    // The asking is owed to the run the face still stands on, and to no other: the face moved on —
    // another run opened, the view closed — in the moment the stream died, and the dead stream is no
    // longer this face's to follow.
    if (!state.run || state.run.id !== runId) return;
    reattachStream(runId);
  });
}

/** Ask again for the stream that died, while the face still stands on the run it served.
 *
 * The asking is the face's own act, and the server's answer to the tree is its question. The server
 * does not answer, and the asking stands and tries again a little further out — the server that
 * restarts is the server the stream was owed to, and the record it serves is the record the pane
 * already shows, replayed over the new connection and kept by the pane instead of drawn twice. The
 * server answers and the run it served no longer stands in the answer, and the asking stops and says
 * so: no stream re-attaches to a run the record no longer holds. A reconnect that found the run is a
 * plain `openStream` again: the log replays whole under the stream's own event, the pane keeps the
 * steps it already shows, and the tail resumes where the log stands.
 */
export function reattachStream(runId) {
  state.notice = 'the stream dropped; reconnecting';
  renderHeader();
  renderChat();
  let delay = 500;
  const attempt = () => {
    state.reattach = null;
    // The face moved on in the gap the asking took: the run the dead stream served is not the run the
    // face stands on now, and the asking it owed is done.
    if (!state.run || state.run.id !== runId) return;
    api.runs().then((answer) => {
      if (!state.run || state.run.id !== runId) return;   // the face moved on while the answer was on the way
      const standing = answer.workspaces.some((ws) => ws.runs.some((one) => one.id === runId));
      if (!standing) {
        // The run the stream served no longer stands in the record the server answers with: the asking
        // stops, and says where the stream stands now rather than standing an asking it will not make.
        state.notice = 'the stream dropped, and the run it served no longer stands; open the run again to follow it';
        renderHeader();
        renderChat();
        renderComposer();
        return;
      }
      // The asking is answered: the record the pane shows stands in the server's answer, and the
      // stream is being asked for again. The word the asking owed stands no longer — and if the
      // asking it meets the server not there after all, the error that answers it stands the word
      // again, the way it stood it the first time.
      state.notice = '';
      renderChat();
      openStream();
    }).catch(() => {
      if (!state.run || state.run.id !== runId) return;
      // The server does not answer: the asking stands, the word it owes stands with it, and the next
      // one is a little further out, the way a question the answer is not at keeps standing.
      delay = Math.min(delay * 2, 10000);
      state.reattach = setTimeout(attempt, delay);
      state.notice = 'the stream dropped, and the server is not answering; reconnecting';
      renderHeader();
      renderChat();
    });
  };
  state.reattach = setTimeout(attempt, delay);
}

/** Stop following the opened run, if anyone was.
 *
 * The in-flight faces go with the connection that carried their fragments: a partial is the pane's memory
 * of words no step has settled yet, and the run that was speaking them is not the run the screen is on.
 * Every path that empties the pane — another run opened, the opened run deleted, the view closed — closes
 * its stream first, so this is the one place that sweep has to be.
 */
export function closeStream() {
  if (state.stream) state.stream.close();
  state.stream = null;
  if (state.reattach) { clearTimeout(state.reattach); state.reattach = null; }
  clearPartials();
}

/** Point the browser at a folder: the folder it lists is the folder a new run starts in, and a
 * folder that would not list is nowhere to start, so the refusal to send is cleared along with it. A
 * listing that came back is also the directory being there, which is the answer the toolbar's own
 * refusals said the last time it was asked. */
export async function browse(path) {
  try {
    state.listing = await api.listing(path);
    state.spawnDir = state.listing.path;
    state.paneNotice = '';
  } catch (error) {
    state.listing = { path, entries: [], error: error.message };
    state.spawnDir = '';
  }
  // The filter goes with the directory it was typed over: words that narrowed one folder are not a view
  // on the next one, and a listing that arrives empty under a leftover word is read as an empty folder.
  state.listingFilter = '';
  nodes.browserFilter.value = '';
  filterMark(nodes.browserFilterToggle, false);
  renderBrowser();
}

/** List the directory the path line was typed with — the keyboard's way onto the pane, beside the row
 * click's.
 *
 * The words go to `browse` as they stand: the server is the one that decides what a path is, so the page
 * neither trims them nor rewrites them into a shape it prefers, and the answer it gives is what the line
 * is then written from. The one thing the page decides for itself is the empty case — a line with nothing
 * in it, whitespace included, is a line the hand rested on, not an asking. It sends no request and touches
 * nothing: the pane goes on listing the directory it was listing, and the dir it was pointing
 * at goes on being that one.
 */
export function browseTypedPath() {
  const typed = nodes.browserPath.value;
  if (!typed.trim()) return;
  browse(typed);
}

/** The control the word goes into: the face's own textarea, stood in the markup, and the thing a hand
 * arriving here wants the cursor in. */
export function composerInput() {
  return nodes.composerInput;
}

export function focusComposer() {
  const input = composerInput();
  if (input) input.focus();
}

/* --- the composer's own hands --------------------------------------------------------------------------

   The composer is the face's markup and the face's hands. What the kit's control stood beside the word —
   the queue, the steer, the attachments, the dictation, the approval and the mode machinery — never stood
   a tile, a select or a menu item on this page, and the five things this file reached the vendor's handle
   for are stood here instead, over the face's own elements:

   * the draft: `setDraft` and `clearDraft`, patched by the hand that holds the word. The face's own send
     event is cancelable and this page prevents it, so no hand but this file's clears a word: the paths
     that carry one clear it and the refusals keep it, exactly as they did while the vendor's `submit`
     stood the same promise;
   * the placeholder: the word about where a word lands, patched per face by `renderComposer`;
   * the dials' stands: the word each trigger wears, from the entries the machine carries and the record
     states;
   * the busy moment: the send's own refusal for the length of a word on the wire. The dials' stand-down
     and the note hand are the page's own working moment and stand from `renderComposer`;
   * the empty send: refused the way the control refused it — the button stands down while the control
     holds nothing or whitespace, kept live on the control's own event.

   The send is the face's own event, spoken on the composer region and answered by the one listener that
   owns where a word goes: a spawn, a follow, a steer, a fork, or a line of the run's own console. The
   two dials speak theirs the same way — a pick off the face's own menu, on the face's own event — so the
   settling stands between a hand on a dial and a switch spoken at the run, and nothing else does. */

export const SEND_EVENT = 'sahw:composer-send';
export const DIAL_EVENT = 'sahw:dial-choice';

// The two dials, in the order the row wears them, and the word each opens its menu under.
export const DIAL_FIELDS = ['effort', 'model'];
export const DIAL_LABELS = { effort: 'Reasoning', model: 'Model' };

/* The container that holds the send at its own position is where the trio the composer owes a working run
   stands: the compact and the stop on its left, the queue on its right, each a word an operator reads at a
   glance; until a run works, the container holds the send alone. */
export const sendActs = nodes.composerActs;

// The signature of the acts the row last stood, read off the record that decides them: a record
// unchanged since the last paint stands the nodes the row already holds, and a node replaced under
// the hand is a hover the hand has to re-earn at the next poll.
let actsSignature = null;


/** The word a level wears on this page: the level itself, begun with a capital, because the dial is read
 * as a word in a row of words and not as a value in a form. The wire and the record keep the value. */
export function levelWord(level) {
  const word = String(level || '');
  return word ? word.charAt(0).toUpperCase() + word.slice(1) : '';
}

/** Why the send stands down: the control holds no word, a word rides the queue, or a word is still on its
 * way to the server. */
export function sendStandsDown() {
  const input = composerInput();
  return !String(input ? input.value : '').trim() || Boolean(state.queued) || composer.busy;
}

/** The send's refusal, stood in the one place it is stood: the button's own disabled state, which is what
 * the browser answers a click with and what `Enter` asks before it speaks. */
export function paintSend() {
  const send = nodes.composerSend;
  if (send) send.disabled = sendStandsDown();
}

/** The word's own face: the control rests at one line and stands the height the word it holds owes —
 * the word's own measure, from the control's own scroll — and the sheet's bounds stand the face's:
 * the resting line below, the eight lines above, and the scroll past them. Asked of the control on the
 * input's own event — a type, a paste, a drop — and by the hands that set a word without an event: the
 * draft the editing face stands, the queue's delivery, the clear the send leaves behind. */
export function growComposer() {
  const input = composerInput();
  if (!input) return;
  input.style.height = 'auto';
  input.style.height = `${input.scrollHeight}px`;
}

/** The word one dial's trigger wears: the label of the entry the picker stands on, and nothing when it
 * stands on no entry it was given — the state the face wears as a control stood down — and the level for
 * the level dial. */
export function dialWord(field, entries, stood) {
  if (field !== 'model') return levelWord(stood);
  const carrying = (entries || []).find((one) => one && one.id === stood);
  return carrying ? String(carrying.label || '') : '';
}

/** Stand the word a dial's trigger wears. The label is the dial's face: it is what the operator reads the
 * run standing on, and it is written as text and nothing else. */
export function paintDialWord(field, word) {
  const wrap = dialWrap(field);
  const label = wrap ? wrap.querySelector('.sahw-chat-composer__choice-label') : null;
  if (label) label.textContent = word;
}

export const composer = {
  // The moment this page refuses a word for its own reason: a send on the wire, or a follow that has not
  // reached the record yet. It refuses the send and nothing else — the dials' stand-down reads the run's
  // working moment, which is a different fact and outlives this one.
  busy: false,
  // The dials' stands as the last patch left them: the entries the machine was read as carrying, which
  // of them the picker is on, and the level beside it. The handle keeps what it is told and adds nothing.
  models: [],
  model: '',
  level: DEFAULT_LEVEL,
  setDraft(text) {
    const input = composerInput();
    if (!input) return false;
    input.value = String(text ?? '');
    growComposer();
    paintSend();
    return true;
  },
  clearDraft() {
    const input = composerInput();
    if (!input) return false;
    input.value = '';
    growComposer();
    paintSend();
    return true;
  },
  setBusy(value) {
    this.busy = !!value;
    paintSend();
  },
  /** The dials' stands and the placeholder, as the machine and the record state them: the entries the
   * picker was fed and which of them it stands on, the level beside it, and the word about where a word
   * lands. A patch paints and says nothing else: the dial's own line is a pick, and a pick is a hand on a
   * menu item, so the face's own patch can never come back to it as a switch. */
  updateOptions(patch) {
    if (!patch || typeof patch !== 'object' || Array.isArray(patch)) return false;
    if (patch.placeholder !== undefined) {
      const input = composerInput();
      const word = String(patch.placeholder);
      // A patch that says what the control already wears writes nothing: the word is the fact, and the
      // moment it changes is the only moment the control has to be told.
      if (input && input.placeholder !== word) input.placeholder = word;
    }
    if (patch.models !== undefined) this.models = Array.isArray(patch.models) ? patch.models : [];
    if (patch.model !== undefined) this.model = String(patch.model || '');
    if (patch.effort !== undefined) this.level = String(patch.effort || '');
    if (patch.models !== undefined || patch.model !== undefined) {
      paintDialWord('model', dialWord('model', this.models, this.model));
    }
    if (patch.effort !== undefined) paintDialWord('effort', dialWord('effort', null, this.level));
    return true;
  },
};

/* The marks this page wears in the corner of the row the word goes out of, and the two hands the control
   used to stand: the attach's mark and the console's stand where the toolbar's own corner is (declared
   there, anchored by the sheet, and wired here), the send's click and the control's `Enter` speak the
   face's send, and the dials' triggers open the face's own menu. */

/** Speak the send: the word the control holds and the level the send will think at, on the face's own
 * event. An empty word is refused before the event is spoken — the same refusal the button's own disabled
 * state stands — and a listener that prevents the event keeps the word, because the hand that carries a
 * word clears it. */
export function speakSend() {
  if (sendStandsDown()) return;
  nodes.composer.dispatchEvent(new CustomEvent(SEND_EVENT, {
    bubbles: true,
    cancelable: true,
    detail: { request: { text: composerInput().value, effort: state.dial.think } },
  }));
}

/** Open one dial's menu at its own trigger, or close the one it opened: the face's own menu component,
 * fed when it opens because the entries follow the machine and the record. The pick speaks the dial's own
 * line; picking the word the dial already stands on says nothing, which is the same fact the record and
 * the machine agree on. */
export function dialMenu(field) {
  const trigger = dialWrap(field) ? dialWrap(field).querySelector('.sahw-chat-composer__choice-trigger') : null;
  if (!trigger) return;
  // The dial that owes no choice owes no menu either: the stand's face is the word, the arrow stands
  // down with it, and the keyboard's hand reaches this same door — Enter on the focused trigger — that
  // the pointer's guard alone does not close.
  if (dialLocked(field)) return;
  const entries = field === 'model'
    ? pickerEntries().map((entry) => ({ id: entry.id, word: entry.label }))
    : dialLevels().map((level) => ({ id: level, word: levelWord(level) }));
  toggleMenu(trigger, DIAL_LABELS[field], () => entries.map((entry) => ({
    label: entry.word,
    onAct: () => pickDial(field, entry.id),
  })));
}

/** The pick a dial's menu item stands: the field and the value it carried, on the face's own event, in the
 * fields the control's config line used to carry. */
export function pickDial(field, value) {
  nodes.composer.dispatchEvent(new CustomEvent(DIAL_EVENT, {
    bubbles: true,
    detail: field === 'model' ? { model: value } : { effort: value },
  }));
}

/** The composer's own wiring: the send's two hands, the dials' two triggers, and the marks that stand in
 * the row's corner. `Enter` is the send — but not the shifted one, which is the newline the control is
 * for, and not the input method's own, which is still building the word the send would speak: the guard
 * the control stood on `isComposing` and the IME's keycode stands here as the control's own promise that
 * a half-built word is not a word yet. */
export function wireComposerHands() {
  const input = composerInput();
  if (input) {
    input.addEventListener('input', paintSend);
    input.addEventListener('input', growComposer);
    input.addEventListener('keydown', (event) => {
      if (event.key !== 'Enter' || event.shiftKey || event.isComposing || event.keyCode === 229
        || event.defaultPrevented) return;
      event.preventDefault();
      speakSend();
    });
  }
  if (nodes.composerSend) nodes.composerSend.addEventListener('click', speakSend);
  for (const field of DIAL_FIELDS) {
    const wrap = dialWrap(field);
    const trigger = wrap ? wrap.querySelector('.sahw-chat-composer__choice-trigger') : null;
    // The trigger's own label is a child of the button: a click on it targets the label, not the anchor,
    // and the document's "anywhere else" rule would take the menu this same click just stood. The hand
    // stops before that rule reads it — the row's rename hand carries the same discipline.
    if (trigger) trigger.addEventListener('click', (event) => {
      if (event && typeof event.stopPropagation === 'function') event.stopPropagation();
      dialMenu(field);
    });
  }
  // The eye the level dial stands behind takes the operator's word as the operator gives it: the act
  // is the page's, the memory is the page's, and the transcript hides its thoughts where the body
  // stands the mark.
  if (nodes.thought) nodes.thought.addEventListener('click', () => {
    state.thoughtShown = !state.thoughtShown;
    store.write('thought.shown', state.thoughtShown);
    paintThought();
  });
  if (nodes.slash) nodes.slash.addEventListener('click', () => slashMenu(nodes.slash));
  paintSend();
}

/* --- the session's two dials: the model and the thinking level ----------------------------------------

   The picker and the level dial are the face's own controls, and for a while they reached nowhere: the picker
   stood one entry this page wrote, and the level rode only the word being sent. Both now reach the session.
   What they may be moved to is what the machine carries — `/api/models`, read once at boot, because the
   registry is the machine's file and this page keeps no copy of it to be wrong about. What they stand on is
   what the run's own record states — `/api/runs/<id>/dials`, which reads the run's opening step and every
   console notice after it. And how they are moved, when a run is open and resting, is the run's own console
   line: `/model <id>`, `/think <lvl>`, spoken at the route that hands it to `channel`, which launches the
   command an operator would have typed and writes nothing itself. A switch is never a word to the model,
   and its only receipt is the `notice` the console leaves beside the log — which is why every path here ends
   by asking the record again rather than by believing the request that just came back okay.

   While the run generates, both dials stand down, and they stand down as a word: the class the face puts on
   them, the reason in each control's own title, and the same sentence in the note hand that the route behind
   them answers a mid-turn switch with. A hand reaching for a stood-down dial is stopped where the event is
   captured, before the dial's own trigger hand hears it, and answered with that sentence — a menu that opened
   on a dial the
   face has stood down is an offer the operator then has to refuse themselves.

   The picker is fed the machine's profiles, plus exactly one entry more in exactly one case: when the name
   the dials stand on is not among them. Such a name is either the record's model, when the console switched
   to a literal name on the box in force, or the machine's own reference, when no profile carries it. Both
   were said by something that owns them; the entry is that saying, not a model this page invented. */

/** The control one dial is, by the field the markup names it with: the picker and the level dial, each
 * standing the row's own choice, each wearing the `data-field` the face reads it by. */
export function dialWrap(field) {
  return nodes.composer.querySelector(`.sahw-chat-composer__choice[data-field="${field}"]`);
}

/** The entry a model name stands by: the profile that carries it — by id, or by the wire name the profile
 * holds, which is the name the record states — and the name itself when no profile carries it, which is
 * also SAH's own treatment of a model reference it cannot resolve: a literal name on the endpoint in force,
 * and a line the console answers to exactly as it answers to a profile id. */
export function entryFor(name) {
  if (!name) return '';
  const carrying = (state.profiles || []).find((profile) => profile.id === name || profile.model === name);
  return carrying ? carrying.id : name;
}

/** The entries the picker is fed: what the machine carries, the stood-on name when the machine does not
 * carry it, and — when there is nothing at all to carry — the one entry that means "no model named", which
 * is what sends no `--model` and takes the machine's own default. The last case matters because the kit's
 * picker filled an empty list from its own demo models, and a picker wearing models this machine does not have
 * is the precise thing this control was rebuilt to stop being. */
export function pickerEntries() {
  const entries = (state.profiles || []).map((profile) => ({
    id: profile.id, label: profile.id, efforts: levelsFor(profile),
  }));
  const stood = entryFor(state.dial.name);
  if (stood && !entries.some((entry) => entry.id === stood)) {
    entries.push({
      id: stood,
      label: state.dial.endpoint ? `${stood} @ ${state.dial.endpoint}` : stood,
      efforts: [DEFAULT_LEVEL],
    });
  }
  if (!entries.length) entries.push({ id: MACHINE_MODEL, label: MACHINE_LABEL, efforts: [DEFAULT_LEVEL] });
  return entries;
}

/** The entry the picker stands on: the record's or the machine's name as an entry, and the first of what
 * the machine carries when neither has named one — a stand the machine's own list authorises, and one the
 * operator sees and can move before any word is sent. */
export function dialStand() {
  const entries = pickerEntries();
  const stood = entryFor(state.dial.name);
  return entries.some((entry) => entry.id === stood) ? stood : entries[0].id;
}

/** The model a launch is sent with: the entry the picker stands on, and nothing at all when the machine
 * carries none — an empty word sends no `--model`, which is the machine's own default speaking. It rides a
 * spawn, a fork and a follow alike, because a switch spoken at a run that had settled is a fact about a
 * process that has already gone and comes true on the objective after it. */
export function dialModel() {
  const entries = pickerEntries();
  const stood = entryFor(state.dial.name);
  return entries.length > 1 || entries[0].id !== MACHINE_MODEL ? (stood || dialStand()) : '';
}

/** Whether one dial stands down. Both do while the run is generating — the face's own working moment, the
 * spinner the tree head wears — and the picker alone while there is nothing it could stand on or move to:
 * no profile the machine carries, and no name the record or the machine has stated. It is the same gate the
 * server answers a spoken switch with, so the control never offers an act its own route refuses and never
 * refuses one its route would carry. */
export function dialStandsDown(field) {
  if (runWorks()) return true;
  return field === 'model' && !entryFor(state.dial.name) && !(state.profiles || []).length;
}

/** The dial that owes no choice: its menu would stand on one entry or fewer — the value the dial
 * already stands on — so the act its hand owes is nothing. The model's word is the machine's (the
 * registry is the machine's file), the level's word the machine's table's, per profile, and the face
 * carries no vocabulary of its own. Mid-turn takes precedence over no-choice: the stand-down owes one
 * reason at a time, the nearer one. */
export function dialLocked(field) {
  const entries = field === 'model' ? pickerEntries() : dialLevels();
  return entries.length <= 1;
}

/** The word the locked dial's title wears, where the dial wears it. */
export function dialLockedReason(field) {
  return field === 'model' ? DIALS_ONE_MODEL : DIALS_ONE_LEVEL;
}

/** The profile the dials stand on: the picker's stand, the same model a launch rides, read back as the
 * profile that declares it — or nothing, when the machine's registry carries no profile by that stand:
 * the machine's own reference, a stand the registry does not hold, or no registry at all. The profile is
 * what declares the model's thinking, because the declaration is the machine's and the face keeps no
 * copy of it to be wrong about. */
export function standingProfile() {
  return (state.profiles || []).find((profile) => profile.id === dialStand()) || null;
}

/** The level words the dial offers for one profile: the face's own `default` word — which sends no
 * `--think`, so the machine's own default speaks — plus the words the machine's table declares the
 * profile's server takes, in the table's order. A table that declares no levels names the profile's own
 * default word as the only level word, and a table that declares nothing is read by the dial's absence,
 * which stands the dial down rather than offers. The declaration is the machine's, so the face keeps no
 * vocabulary of its own to be wrong about. */
export function levelsFor(profile) {
  const declared = profile && Array.isArray(profile.think_levels) ? profile.think_levels : [];
  const words = declared.length ? declared
    : (profile && String(profile.think || '').trim() ? [profile.think] : []);
  return [DEFAULT_LEVEL, ...words];
}

/** The level words the dial offers at the stand: the standing profile's own, and nothing beside the
 * face's default word where the stand is no profile the registry holds — a stand that declares no
 * thinking owes no menu, and the dial's absence says so on the control itself. */
export const dialLevels = () => levelsFor(standingProfile());

/** Whether the model the dials stand on thinks, in the machine's own word: the standing profile
 * declares a `think` level — the same field a launch rides as `--think` — or names the levels the
 * profile's server takes, and a machine that declares nothing is a machine whose model thinks no
 * thought, the way it names no sight. The declaration is the gate, so the dial never offers a level
 * the machine will not carry, and never withholds one it would. */
export function thinkingDeclared() {
  const profile = standingProfile();
  if (!profile) return false;
  return String(profile.think || '').trim() !== ''
    || (Array.isArray(profile.think_levels) && profile.think_levels.length);
}

/** Why one dial stands down, in the sentence the note hand wears and the control's own title holds: the
 * mid-turn words are the server's own, so an operator reading the control and one reading the refusal the
 * same act brings back are told the same fact. */
export function dialReason(field) {
  if (runWorks()) return DIALS_DOWN;
  return field === 'model' ? DIALS_NONE : '';
}

/** Mark the stand-down on the two controls. The kit's composer disabled a dial only while its composer was
 * `busy`, and this face is never busy while its run works — a working run is exactly the run a word can be
 * sent to — so the mark is the face's own class, with `aria-disabled` beside it because the control still
 * takes the keyboard and only the word says it will not take the act. */
/** Mark the stand-down on the two controls, under either of its two reasons — the turn the run is mid,
 * and the choice the dial does not owe — each the face's own class, with `aria-disabled` beside it
 * because the control still takes the keyboard and only the word says it will not take the act. */
export function paintDialStand() {
  const thinking = thinkingDeclared();
  const eye = nodes.thought;
  if (eye) eye.classList.toggle('sahw-dial--absent', !thinking);
  ['model', 'effort'].forEach((field) => {
    const wrap = dialWrap(field);
    if (!wrap) return;
    // The level the machine declares nowhere is no level to offer: the dial that would stand it stands
    // nowhere at all — not down, not locked, absent — because the machine's declaration is the nearer
    // reason than either, and a control it withholds is not a control the row keeps.
    const absent = field === 'effort' && !thinking;
    wrap.classList.toggle('sahw-dial--absent', absent);
    if (absent) {
      wrap.setAttribute('aria-disabled', 'true');
      wrap.title = DIALS_NO_THINKING;
      return;
    }
    const down = dialStandsDown(field);
    const locked = !down && dialLocked(field);
    wrap.classList.toggle('sahw-dial--down', down);
    wrap.classList.toggle('sahw-dial--locked', locked);
    if (down || locked) {
      wrap.setAttribute('aria-disabled', 'true');
      wrap.title = down ? dialReason(field) : dialLockedReason(field);
      return;
    }
    wrap.removeAttribute('aria-disabled');
    wrap.removeAttribute('title');
    // A sentence the refusal owes the operator stands on the control that owes it: the run is at rest, so
    // the stand-down is not the reason the control says what it says — the sentence is. It is owed to both
    // dials, because the sentence names both, and it goes out of the titles the moment it is spent.
    if (state.dial.word) wrap.title = state.dial.word;
  });
  paintThought();
}

/** The eye the level dial stands behind: the operator's own hand on the thought a turn stands in.
 * Shown or hidden is the operator's and is remembered, because a hiding the operator made is the
 * operator's to keep between the page's standings. It goes out over the page rather than onto the
 * transcript — the body's own mark — because the thought stands in rows the face rebuilds, and the
 * mark that hides it must outlast the rebuild. */
export function paintThought() {
  const eye = nodes.thought;
  if (!eye) return;
  eye.setAttribute('aria-pressed', state.thoughtShown ? 'true' : 'false');
  eye.title = 'toggle reasoning display';
  document.body.classList.toggle('sahw-thought-hidden', !state.thoughtShown);
}

/** Stop the ask a stood-down dial gets, before the dial's own trigger hand hears the event at all: the
 * alternative is a menu opening under a dial that will not answer. The reason the ask is owed stands
 * where the dial's own paint already put it — the title the dial wears while it stands down. */
export function noteDialAsk(event) {
  const target = event.target;
  const wrap = target && typeof target.closest === 'function'
    ? target.closest('.sahw-chat-composer__choice[data-field]')
    : null;
  const field = wrap ? wrap.getAttribute('data-field') : '';
  if ((field !== 'model' && field !== 'effort') || !(dialStandsDown(field) || dialLocked(field))) return;
  event.preventDefault();
  event.stopPropagation();
}

/** Hand the picker its entries and its stand and the dial its level, as the machine and the record state
 * them — under the settling mark, because a patch paints and says nothing: the dial's own line is a pick,
 * and the mark is the face's second word about which of the two is moving a control. */
export function paintDials() {
  state.dial.settling = true;
  try {
    composer.updateOptions({ models: pickerEntries(), model: dialStand(), effort: state.dial.think });
  } finally {
    state.dial.settling = false;
  }
  paintDialStand();
}

/** Settle the dials on the record's answer: the model's name, the address a switch named beside it, and the
 * level the run stands at. `none` is the console's spelling for the level left out of the request and the
 * face's 'default' is the same absence spelled for the launch, so the two are read as one here and as the
 * pair they are on the wire.
 *
 * A switch this page spoke is confirmed here and nowhere else: the record stating the value asked for is the
 * notice having arrived, and until it does the dials keep where the last reading left them and the sentence
 * they owe the note hand keeps standing. A record that states nothing for a dial moves nothing: the machine's
 * default, or the last thing the record did state, is still what the run stands on.
 */
export function settleDials(answer) {
  const stated = answer && typeof answer.model === 'string' ? answer.model : '';
  const level = answer && typeof answer.think === 'string' && answer.think && answer.think !== LEVEL_NONE
    ? answer.think
    : DEFAULT_LEVEL;
  const asked = state.dial.asked;
  if (stated) state.dial.name = stated;
  state.dial.endpoint = answer && typeof answer.endpoint === 'string' ? answer.endpoint : '';
  state.dial.think = level;
  if (asked) {
    const stood = asked.kind === 'model' ? entryFor(state.dial.name) : level;
    if (stood === asked.value) {
      state.dial.asked = null;
      state.dial.word = '';
    }
  }
  paintDials();
  renderComposer();
}

/** One reading of what the record says the dials stand on, settled into the controls: whether the answer
 * came back for the run this page is still standing on, which is all its caller needs to know — a reading
 * that belongs to another run settles nothing, and a page that moved on is owed no settle.
 */
export async function readDials(runId) {
  let answer;
  try {
    answer = await api.dials(runId);
  } catch {
    return false;                       // the record will not answer: the dials keep where it last spoke
  }
  if (!state.run || state.run.id !== runId) return false;
  settleDials(answer);
  return true;
}

/** Ask the record what the opened run's dials stand on — and go on asking while a switch this page spoke is
 * waiting for its notice, because the console line is a child that has to boot, resolve the endpoint, record
 * what it changed and go, and the answer that said the line was carried is not the record saying it landed.
 *
 * The asking belongs to the run it was asked for: the face may have moved on while an answer was on its way,
 * and a settle for a run no longer in the pane would stand another run's dials in this one's controls. With
 * nothing waiting on it this is one reading and no more, which is what an opened run costs and nothing more.
 */
export async function askDials(runId) {
  if (state.dial.reading) return false; // a reading is already on its way, and it will see what this is for
  state.dial.reading = true;
  try {
    for (let attempt = 0; attempt < DIAL_SETTLE_TRIES; attempt += 1) {
      if (!await readDials(runId)) return false;
      if (!state.dial.asked) return true; // nothing pending: one reading is the whole of what was asked for
      await sleep(DIAL_SETTLE_MS);
      if (!state.run || state.run.id !== runId) return false;
    }
    if (state.dial.asked) {
      // Spoken, and the record never said it landed. The switch is not believed, the dials stay where the
      // record says they stand, and the sentence is what the operator is owed instead of a settled control.
      state.dial.asked = null;
      state.dial.word = DIALS_LATE;
      renderComposer();
    }
    return true;
  } finally {
    state.dial.reading = false;
  }
}

/** Move one dial. With a run open and resting that means speaking the session's own line and then going to
 * the record for the notice; with no run open it means standing the spawn's dial somewhere new, which is
 * this page's own business and reaches nothing but the face's own memory — the standing a launch will ride
 * is kept the way the last run is kept, because a standing the page never writes is a pick the reload takes
 * back. And with a run generating it means the sentence, which is
 * what the control already says and the route would answer anyway — the three ways of being refused for it
 * are one sentence, so the operator hears one fact wherever they asked. */
export async function switchDial(kind, value) {
  const level = kind === 'think' && value === DEFAULT_LEVEL ? LEVEL_NONE : value;
  if (!state.run) {
    // The standing's own moment: the pick stands the dial and writes the word it stood, one key per dial,
    // because the model's word and the level's word each answer for themselves on the next boot.
    if (kind === 'model') { state.dial.name = value; store.write('dial.model', value); }
    else { state.dial.think = value; store.write('dial.think', value); }
    state.dial.word = '';
    paintDials();
    renderComposer();
    return;
  }
  const runId = state.run.id;
  if (runWorks()) {
    state.dial.word = DIALS_DOWN;
    paintDials();                     // the control has already moved; the record's stand goes back on it
    renderComposer();
    return;
  }
  state.dial.asked = { kind, value, at: Date.now() };
  state.dial.word = '';
  try {
    await api.command(runId, `/${kind === 'model' ? 'model' : 'think'} ${level}`);
  } catch (error) {
    // The route's own refusal, in its own words: the run started working between the click and the request,
    // or the line was not one of the two it carries. Either way nothing changed, and the dial goes back
    // where the record says it stands while the sentence stays where it was put.
    state.dial.asked = null;
    state.dial.word = error.message;
    paintDials();
    renderComposer();
    return;
  }
  await askDials(runId);
  // The record has the console's word by now — that is what the settle above waited for — and the pane is
  // read from the record, so the line is asked for here the way a follow-up word asks for the objective it
  // just started: a run at rest holds no stream, and a switch that never reached the transcript would be
  // an act the operator made that the pane denies. The replay reconciles by step id, so what arrives new
  // is the notice and nothing that stood above it.
  if (state.run && state.run.id === runId) openStream();
}

/** The standing the page keeps for the run it has not started: the model's word and the level's word the
 * operator last stood the dials on with no run open, stood the way the boot and the return from a run both
 * stand them — through this one settling, so the two never wear two answers. A kept word the machine no
 * longer carries stands nowhere: a profile the registry no longer holds, or a level the standing profile's
 * table no longer declares, is a word the machine will not ride, and the fallback is the standing the face
 * would have worn had it never remembered. The model is resolved first, because the profile that declares
 * the level's words is the one the model stands on, and a level is resolved against the table of the
 * profile it rides. */
export function rememberedStanding() {
  const profiles = state.profiles || [];
  const kept = store.read('dial.model', '');
  let model = '';
  if (typeof kept === 'string' && kept) {
    const carrying = profiles.find((profile) => profile.id === kept || profile.model === kept);
    if (carrying) model = carrying.id;
    else if (kept === state.machine) model = kept;                  // the machine's own reference, still declared
    else if (kept === MACHINE_MODEL && !profiles.length) model = kept;   // the entry a bare registry owes
  }
  state.dial.name = model || entryFor(state.machine) || (profiles.length ? profiles[0].id : '');
  const level = store.read('dial.think', DEFAULT_LEVEL);
  state.dial.think = levelsFor(standingProfile()).includes(level) ? level : DEFAULT_LEVEL;
}

/** Read the machine, once, for the picker: the profiles its registry declares and the model a run launched
 * from this tree speaks as when nothing names one. A refusal is kept as the fact it is — no list, and the
 * sentence the route gave — because a face that answered the machine's silence with a list of its own would
 * be naming endpoints this box does not have. */
export async function readMachine() {
  try {
    const answer = await api.models();
    state.profiles = Array.isArray(answer.models) ? answer.models : [];
    state.machine = typeof answer.machine === 'string' ? answer.machine : '';
  } catch (error) {
    state.profiles = null;
    state.machine = '';
  }
  if (!state.run) rememberedStanding();
  if (!state.run) state.dial.word = '';
  paintDials();
  renderComposer();
}

/** Stand the dials where a run with no record of its own stands: the standing the page keeps — the word
 * the operator last stood the dials on with no run open — and the machine's own standing where the kept
 * word no longer stands, so the boot's own settling and the return from a run wear one answer. */
export function resetDials() {
  rememberedStanding();
  state.dial.endpoint = '';
  state.dial.asked = null;
  state.dial.word = '';
}

/** What the picker and the dial answer to: the two controls' own event, which is the operator's hand on
 * them. The settling mark is the face moving them on the record's word and says nothing about an act, and
 * the model is asked about first because a picker that moved took the level's list with it. */
export function wireDials() {
  nodes.composer.addEventListener(DIAL_EVENT, (event) => {
    const config = event.detail;
    if (state.dial.settling || !config || typeof config !== 'object') return;
    if (config.model && config.model !== entryFor(state.dial.name)) {
      switchDial('model', config.model);
      return;
    }
    if (config.effort && config.effort !== state.dial.think) switchDial('think', config.effort);
  });
  nodes.composer.addEventListener('pointerdown', noteDialAsk, true);
  nodes.composer.addEventListener('keydown', noteDialAsk, true);
}

/** Repaint the composer's frame: the face's placeholder and whether it will take a word at all.
 *
 * Busy is the page's own moment, not the run's state: a run that is working is exactly the run a word
 * can be sent to, which is what makes it a conversation. The two moments this control refuses a word
 * are a send still on the wire and a follow that has not reached the record yet — the second because a
 * further word in that window would be a second writer on a log the first has only not opened, the one
 * case the server's rule exists to keep apart and this one can simply not offer.
 *
 * The queued word's confirmation stands with the queue's mark at the send's own ground, and the faces
 * that name a step of the record wear their way out there too — the edit's cancel, one word, the same
 * act `Esc` answers.
 */

/* --- the trio the composer owes a working run: stop it, steer it, or queue a word for after -----------

   A run that works is a run the operator still talks to, and the control's word owes three different
   acts on it. The stop ends the run's process — its record stands, and the next word relaunches it —
   and it is the face's own act, standing in the send's own ground the way the edit's cancel does. The steer is
   the send itself: the word goes to the run at its next turn boundary, the confirmation the steer
   always leaves. The queue holds the word as the next objective — a promise to the run, delivered
   through the follow channel when the run ends or is stopped, whichever the record says happened.

   While a word rides the queue the control takes no word: the input locks, the send stands down, and
   the queue's own mark offers the release. The delivery is the composer's render to make — the ending
   and the stop both end in one — and it is owed the same path a typed follow takes: the run's own
   record decides the channel, the dials ride where the record says they stand, and the files the tray
   holds ride with the word. */

/** The control the queue locks: the face's own textarea, disabled while a word rides. */
export function lockInput(locked) {
  const input = composerInput();
  if (input) input.disabled = locked;
}

/** The queue's act on the word the control holds: the word goes onto the ride, the control locks, and
 * the note hand says what the word owes now rather than what the face was saying. A control that holds
 * no word is refused with its own sentence: the queue takes a word, and there is none to take. */
export function queueWord() {
  const input = composerInput();
  const word = String(input ? input.value : '').trim();
  if (!word) {
    state.notice = 'the queue takes a word — the control holds none';
    renderChat();
    renderComposer();
    return;
  }
  state.queued = word;
  if (composer) composer.clearDraft();
  lockInput(true);
  renderComposer();
}

/** The release: the word returns to the control, the lock lifts, and the face stands what it stood
 * before the word went onto the ride. */
export function unqueueWord() {
  if (!state.queued) return;
  if (composer) composer.setDraft(state.queued);
  state.queued = null;
  lockInput(false);
  focusComposer();
  renderComposer();
}

/** The delivery the ending owes a word on the ride: the same word the operator would have sent, posted
 * the way the follow posts it. The queue clears before the post, so a render asked again while the word
 * is on the wire sees no queue and delivers nothing twice. */
export async function deliverQueued() {
  const word = state.queued;
  if (!word || !state.run) return;
  const runId = state.run.id;
  state.queued = null;
  lockInput(false);
  state.sending = true;
  renderComposer();
  try {
    const answer = await api.message(runId, word, thinkLevel(state.dial.think), dialModel(), '',
                                     await attachmentBodies());
    clearAttachments();
    if (composer) composer.clearDraft();
    state.notice = '';
    if (answer.channel === 'steer') { state.steer = word; renderChat(); attachToTail(); }
    else startFollow(runId);
  } catch (error) {
    state.notice = error.message;
    renderChat();
  } finally {
    state.sending = false;
    renderComposer();
  }
}

/** The acts the row owes, as data the paint stands or re-stands, in the order they stand: the
 * compact's mark and the edit's cancel on the send's left, the stop beside them, the queue on the
 * send's right.
 *
 * The compact's mark stands from the floor up: a mark for an act the machine would refuse is a word
 * the record cannot keep, so the mark stands where the record says the act would not be refused at
 * the turn boundary — the conversation longer than the backfill a summary leaves standing, and the
 * window holding the result the act must leave within, beside the load every request carries — and
 * stands down where the record tells no floor. The in-flight notice stands the mark as the stop; the
 * flight's two endings stand it back the way they stand the record down.
 *
 * The edit's cancel stands left of the send, the way the run's own cancel stands: an aim that is not
 * sent is stood down at the send's own ground, where the operator's hand already looks for the word's
 * other endings. The stop wears the cancel optic: the act it names ends what the machine is doing,
 * and the ending an act takes is the warning color the edit's own cancel wears — one optic for the
 * acts that stand down the working.
 */
export function actsDue(name, state) {
  const acts = [];
  if (state.run) {
    const flight = compactInFlight(state.steps);
    const floor = compactFloor(state.steps);
    if (flight || (floor && floor.possible)) {
      // The window the conversation stands in, read off the last turn: the round number in the label,
      // the fill the mark's own ground wears, and the whole figures one hover away in the claim. A
      // flight without numbers owes the mark no gauge: the plain word, the fill stood down the way a
      // mark stands down.
      const turn = floor ? floor.turn : lastTurn(state.steps);
      const usage = (turn && typeof turn.tokens_in === 'number'
        && typeof turn.context_max === 'number' && turn.context_max > 0)
        ? Math.min(100, Math.round((turn.tokens_in / turn.context_max) * 100))
        : null;
      // The number the mark owes a step: the window spent, told twice as loud as the glance — the
      // half-window step, then the warning's, so the fill that predicts the act changes its voice
      // before the act has to be taken. One tier at a time: the mark wears the step it owes, not a
      // memory of the one it shed.
      const tier = usage === null ? '' : usage >= 70 ? ' sahw-compact--hot' : usage >= 50 ? ' sahw-compact--warn' : '';
      // The claim the mark owes when it stands: the window, glanced at — what the last turn spent, of
      // what the turn had, at the share it owes: X/Y Z%. The figures the record reads no window for
      // stand no claim, and the plain word does.
      const claim = usage === null
        ? 'the record reads no window'
        : `${turn.tokens_in}/${turn.context_max} ${usage}%`;
      acts.push({
        word: (flight ? 'stop compact' : 'compact') + (usage === null ? '' : ` (${usage}%)`),
        claim,
        onAct: () => compactAct(flight),
        className: `sahw-btn sahw-btn--ghost sahw-compact${tier}`,
        usage,
      });
    }
  }
  if (name === 'editing') {
    acts.push({
      word: '✕ cancel edit',
      claim: `Stop returning to step ${state.edit.step}: nothing is sent and nothing is cut`,
      onAct: clearEdit,
      className: 'sahw-btn sahw-btn--ghost sahw-edit-cancel',
    });
  }
  if (name === 'steer') {
    acts.push({
      word: STOP_GLYPH + ' stop',
      claim: 'stop the run now — its record stands, and the next word relaunches it',
      onAct: stopRunComposer,
      className: 'sahw-btn sahw-btn--ghost sahw-stop sahw-edit-cancel',
    });
    acts.push(state.queued
      ? {
          word: QUEUE_GLYPH + ' un-queue',
          claim: 'release the queued word back to the control — it goes nowhere',
          onAct: unqueueWord,
          className: 'sahw-btn sahw-btn--ghost sahw-unqueue',
          after: true,
        }
      : {
          word: QUEUE_GLYPH + ' queue',
          claim: 'hold the word in the control as the next objective — it rides the follow when the run ends, and while it rides the control takes no word',
          onAct: queueWord,
          className: 'sahw-btn sahw-btn--ghost sahw-queue',
          after: true,
        });
  }
  return acts;
}

export function renderComposer() {
  // The ride's delivery, owed before the face is read: the run it promised has stopped working —
  // ended, or stopped — and the word it holds is the next objective that run now owes.
  if (state.queued && state.run && !runWorks()) deliverQueued();
  const name = composerFace();
  const face = faceWords(name);
  if (composer) {
    composer.updateOptions({ placeholder: face.placeholder });
    composer.setBusy(state.sending || state.follow !== '');
  }
  paintDialStand();
  // The console's mark stands beside the attach's mark while a run is open — the session the channel
  // speaks to is the run's, and with no run there is no session to speak to — and stands down on the
  // spawn face the same way the compact's mark does, the mark absent rather than a word explaining it.
  if (nodes.slash) nodes.slash.style.display = state.run ? '' : 'none';
  // The trio the composer owes a working run, at the send's own position: the container the send is
  // wrapped in holds the stop on the send's left and the queue on its right, and the send in the middle
  // says the word of the face it wears. A word on the ride survives the stop that stands beside it, which
  // is the stop's own case to answer; a container that holds the send alone is a face that owes no trio,
  // and it stands no mark.
  const send = nodes.composerSend;
  if (send) {
    paintSend();
    if (sendActs) {
      // The acts as data before they are nodes: the row's standing is a pure reading of the record —
      // the face, the word on the ride, the edit's aim, the compact's floor and flight — and a record
      // unchanged since the last paint stands the nodes the row already holds. A node replaced under
      // the hand is a hover the hand has to re-earn at the next poll, and the poll owes the row its
      // standing, not a redraw of it.
      const due = actsDue(name, state);
      const signature = due.map((one) => `${one.className}|${one.word}|${one.claim}|${one.usage ?? ''}`)
        .join('~');
      if (signature !== actsSignature) {
        actsSignature = signature;
        for (const one of [...sendActs.children]) {
          if (one !== send) one.remove();
        }
        for (const one of due) {
          const node = action(one.word, one.claim, one.onAct, one.className);
          if (one.usage !== null && one.usage !== undefined) node.style.setProperty('--sahw-usage', `${one.usage}%`);
          if (one.after) sendActs.appendChild(node);
          else sendActs.insertBefore(node, send);
        }
      }
    }
    if (name === 'steer') {
      send.title = state.queued
        ? 'the queue stands — release it, or stop the run'
        : 'steer the run — it takes effect at the run\'s next turn boundary';
    }
  }
}

/* --- the compact's mark: the panel's own word for the run's conversation, in its three standings -------

   The mark stands from the floor up: a compaction is possible where the machine's own arithmetic says
   the act would not be refused at the turn boundary — the conversation longer than the backfill a
   summary leaves standing, and the window holding the result the act must leave within, beside the load
   every request carries — so the panel owes the operator no mark for an act the record says would be
   refused, and no mark where the record tells no floor at all. It posts the verb through the channel —
   the queue is the run's own surface, and the run decides at its turn boundary — and the in-flight
   notice beside the log stands it as the stop: the flight's two endings (the landing, the stopped act)
   are the two lines that stand the compact mark back, and the notice the act owes stands in the
   transcript the way every act's word does. */

/* The machine's own numbers, in the words the record stands: the share of the context a compaction's
 * result must leave within (sah compact's TARGET), the messages a summary leaves standing verbatim (its
 * KEEP_RECENT — a conversation no longer than this owes nothing to a summary), and the slot's smallest
 * text at the standing rate, in tokens (its slot's failed note, the size the fit check budgets for
 * before any summary is asked). */
export const COMPACT_TARGET = 0.4;
export const COMPACT_KEPT = 6;
export const COMPACT_NOTE = 30;

/** The floor a compaction must land above, read off the record the machine reads — the last turn's
 * window reading, the load the run's own head stands in (the latest opening step's resident number, the
 * same count the machine's arithmetic runs on), and the limit the result must stay within: the smaller
 * of the target share of the window and of what the last turn spent. `possible` is the machine's fit
 * question in the record's own numbers — the limit holds the resident load and the slot's smallest
 * text, beside whatever backfill the act's cut rung drops to meet it. The last turn's reading is the
 * record's nearest to the request the act will be asked against: what that request carries beside it
 * would be a cut the machine makes, not a refusal it sends, so the reading stands the mark the way the
 * machine would. Null where the record tells no floor — no turn reads the window, no step stamps the
 * head's load, or the conversation is no longer than the backfill — and a floor the record does not
 * tell is a floor the face will not stand. */
export function compactFloor(steps) {
  const turn = lastTurn(steps);
  if (!turn || typeof turn.tokens_in !== 'number' || typeof turn.context_max !== 'number'
    || turn.context_max <= 0) return null;
  let head = null;
  for (let at = steps.length - 1; at >= 0; at -= 1) {
    if (steps[at].kind === 'started') { head = steps[at]; break; }
  }
  if (!head || typeof head.resident_tokens !== 'number') return null;
  const talk = steps.filter((step) => step.kind === 'message' || step.kind === 'result').length;
  if (talk <= COMPACT_KEPT) return null;
  const limit = Math.floor(Math.min(COMPACT_TARGET * turn.context_max, COMPACT_TARGET * turn.tokens_in));
  return { turn, resident: head.resident_tokens, limit,
           possible: limit >= head.resident_tokens + COMPACT_NOTE };
}

/** Whether the compact's flight stands: the in-flight notice stands beside the log with no summary step
 * after it — the landing and the stopped act are the two lines that stand the flight down, and either
 * one walking the record's order past the notice is the flight being over. */
export function compactInFlight(steps) {
  for (let at = steps.length - 1; at >= 0; at -= 1) {
    const step = steps[at];
    if (step.kind === 'summary') return false;
    if (step.kind === 'notice' && step.subject === 'compact'
      && typeof step.text === 'string' && step.text.startsWith('compact: in flight')) return true;
  }
  return false;
}

/** The compact's act, in the hand its mark stands: the verb the flight's standing names. The answer is
 * the verb carried, and the word the act owes stands in the transcript — the flight's own notice is the
 * record's to stand, and it arrives the way every step arrives. */
export async function compactAct(stop) {
  if (!state.run) return;
  const runId = state.run.id;
  let answer;
  try {
    answer = stop ? await api.compactStop(runId) : await api.compact(runId);
  } catch (error) {
    state.notice = error.message;
    renderChat();
    return;
  }
  if (state.run && state.run.id === runId) {
    state.notice = stop
      ? 'the stop rides the queue — the compaction stands down at its next stage boundary, before the summary lands'
      : 'the compaction rides the queue — it lands at the run\'s next turn boundary';
    renderChat();
  }
}

/* --- the run's numbers: the last assistant turn's own, at the composer's left -------------------------

   The stream carries these on every assistant message — the tokens the turn was sent with and the
   ceiling they are measured against, and how fast the words came — so the line is a reading of the
   steps already here and owes the server nothing. It moves while the stream does because it is rendered
   with each frame, and it stands at the last turn's numbers once the run rests because the last turn is
   still the last thing the record has said. The line is the composer's, so it is the composer's render
   that fills it. */

/** The turn whose numbers these are: the last assistant message that carried any. */
export function lastTurn(steps) {
  for (let index = steps.length - 1; index >= 0; index -= 1) {
    const step = steps[index];
    if (step.kind === 'message' && step.role === 'assistant'
      && (typeof step.tokens_in === 'number' || typeof step.tps === 'number')) return step;
  }
  return null;
}

/** A token count, told in the room it has: the line is read at a glance, so 47,520 of them are 48k. */
export function compact(count) {
  return count >= 10000 ? `${Math.round(count / 1000)}k` : String(Math.round(count));
}

// The page's own tick — how often the page asks the tree whether a run it started has begun to be a
// run it can follow. The server's own stream poll is a different rhythm; this one is the page's.
export const POLL_MS = 500;
// The lazy sweep the idle tree still owes: a run launched beside the face stands in the runs root,
// not in the page, and it has to stand in the listing without the operator's re-ask. The ask costs
// the server the poll's stamp question, which a root that did not move answers from memory — the
// sweep is the page's own half second, not the machine's.
export const POLL_MS_IDLE = 2000;

// How long the page waits for a followed run's new objective to reach the record before it simply
// follows the log it can see: a resume rebuilds the whole conversation before it writes its first line,
// and a child that writes none is a run no amount of asking will make followable.
export const FOLLOW_ATTEMPTS = 120;

export const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/** The composer's 'default' level means "leave the machine's own default alone": it must not ride to
 * the child's --think, because the backend has no level called 'default' and refuses it at the first
 * turn. An empty think sends no --think at all, which is the machine's default.
 */
export function thinkLevel(effort) {
  return effort === 'default' ? '' : effort;
}

/** Wait for a run that was just started to be a run the page can open.
 *
 * `POST /api/runs` answers with the id as soon as the folder is claimed, and it is the child's own
 * first log line that makes the folder one the tree lists and one the stream has a file to follow;
 * between those two facts there is a moment in which the id names a folder and nothing else. So the
 * tree is asked again — the same half second the server's own follow polls at — until the id has a
 * row, and if it never does the page says which run left no log rather than showing an empty pane
 * that looks like a run with nothing to say.
 */
export async function awaitRun(runId, attempts = 60) {
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    await refreshTree().catch(() => {});
    const found = findRun(runId);
    if (found) return found;
    await sleep(POLL_MS);
  }
  return null;
}

/** Ask the server for a run, and open the one it started.
 *
 * The draft outlives the request: `preventDefault` keeps the composer's text until the run is open
 * in front of the reader, because a run that was never started — or never left a record — has no
 * business having eaten the task.
 */
export async function spawnRun(text, effort) {
  const task = String(text || '').trim();
  if (!task) return;
  const think = thinkLevel(effort);
  if (!state.spawnDir) {
    state.notice = 'no dir: the server could not list one, so there is nowhere to start a run';
    renderChat();
    return;
  }
  try {
    const answer = await api.spawn(state.spawnDir, task, think, dialModel(),
                                   await attachmentBodies());
    // The files are the run's estate from here, whatever the log does next: the word that carries
    // their lines is out of this page's hands, and the tray beside the draft is empty again.
    clearAttachments();
    const found = await awaitRun(answer.run_id);
    if (!found) {
      state.notice = `run ${answer.run_id} was started and never wrote a log to follow`;
      renderChat();
      return;
    }
    if (composer) composer.clearDraft();
    openRun(found.row, found.workspace);
    attachToTail();
  } catch (error) {
    state.notice = error.message;
    renderChat();
  }
}

/** Send the objective to the fork route rather than to the run in the pane.
 *
 * The word is typed here and works elsewhere: the branch is a new run, and the only thing this page's
 * state says about it is the source and the step named when the aim was taken up. The step is settled on
 * the server against the source's log, and a refusal launches nothing — which is why a refused fork keeps
 * its aim and its words: the sentence names the step, not the objective, and the next send is at hand.
 *
 * A fork that landed is waited for the way a spawn is, then opened: the new run's row is the branch's
 * first fact the tree can carry, and opening it shows the carried prefix under the fork marker.
 */
export async function forkRun(text, effort) {
  const task = String(text || '').trim();
  if (!task) return;
  const { source, step } = state.fork;
  state.sending = true;
  renderComposer();
  try {
    // The branch route carries the objective's words and no bytes, so a fork takes nothing with it — and
    // the files a hand had stood at the draft stay standing there, shown in the tray, rather than
    // riding a route that would silently leave them behind.
    const answer = await api.fork(source, task, thinkLevel(effort), dialModel(), step);
    if (composer) composer.clearDraft();
    state.fork = null;
    state.notice = '';
    const found = await awaitRun(answer.run_id);
    if (!found) {
      state.notice = `run ${answer.run_id} was forked and never wrote a log to follow`;
      renderChat();
      return;
    }
    openRun(found.row, found.workspace);
    attachToTail();
  } catch (error) {
    state.notice = error.message;
    renderChat();
  } finally {
    state.sending = false;
    renderComposer();
  }
}

/** Send one word to the run that is open, and take the channel the server answered with.
 *
 * The page frames the composer; the server places the word. `steer` means the words are in the run's
 * queue, and the note at this composer stands until the record carries them back; `follow` means a new
 * objective is starting on the log this pane already shows, so the stream is asked again for it. The one
 * refusal the rule keeps for itself arrives as the sentence it names, in the place the pane keeps the
 * sentences a reader is owed.
 *
 * While an edit stands the word carries the cut with it — the same route, the one extra field, and the
 * step's digits as the log wrote them. The edit is spent either way the answer goes: posted, the words are
 * the conversation's now, and refused, the cut did not happen and the face that promised it goes — while
 * the composer keeps the words a refused word always keeps, so the next aim is at the same text.
 */
export async function sendWord(text, effort) {
  const word = String(text || '').trim();
  if (!word) return;
  const runId = state.run.id;
  const cut = state.edit ? state.edit.step : '';
  state.sending = true;
  renderComposer();
  try {
    const answer = await api.message(runId, word, thinkLevel(effort), dialModel(), cut,
                                     await attachmentBodies());
    // The files went with the word — posted as a steer or as a follow, the routes wrote each into the
    // run's estate and left its line in the word before the run ever saw it.
    clearAttachments();
    if (composer) composer.clearDraft();
    state.notice = '';
    state.edit = null;
    if (answer.channel === 'steer') { state.steer = word; renderChat(); attachToTail(); }
    else startFollow(runId);
  } catch (error) {
    state.notice = error.message;
    state.edit = null;
    renderChat();
  } finally {
    state.sending = false;
    renderComposer();
  }
}

/** Take the pane to the tail of its words and reattach the follow. The operator has just sent a
 * word — a steer, a follow, the spawn's first objective — and the standing the word owes is owed at
 * the end of the record: the marker that rides with it, the turn it will land at. The place the
 * reader stood while the run worked is theirs, and it is not where a sent word lands. */
function attachToTail() {
  const pane = scrollers.get(nodes.scroller);
  if (pane) pane.scrollToEnd();
}

/** Believe the opened run is working again, on the strength of the follow sent a moment ago.
 *
 * The belief is stated here and the record is then waited for, because of what the resume does before
 * it writes: it rebuilds the conversation from the log, so for a moment or two the log still ends with
 * the objective that finished — and a stream asked in that window replays that ending and closes, since
 * the ending at the end of a log is what a stream stops at.
 */
export function startFollow(runId) {
  state.follow = runId;
  state.run.status = 'live';
  state.run.live = 'live';
  renderHeader();
  renderChat();
  renderComposer();
  attachToTail();
  awaitObjective(runId);
}

/** Wait until the tree says the followed run works, then follow it.
 *
 * Asked of the tree, because the tree is the one place the page learns a log grew without opening a
 * stream that would stop at the ending already sitting at its end. The replay that arrives with the new
 * objective is the whole record, both objectives, and it reconciles with what the pane shows by step id
 * (see `openStream`) — so waiting costs a line that appears slightly late, and never a line lost. A run
 * whose follow never arrives is waited for so long and then followed anyway: the stream replays what the
 * log holds, closes on the ending at the end of it, and the composer goes back to offering the next word.
 */
export async function awaitObjective(runId) {
  for (let attempt = 0; attempt < FOLLOW_ATTEMPTS; attempt += 1) {
    await refreshTree().catch(() => {});
    const found = findRun(runId);
    if (found && found.row.status === 'live' && found.row.live !== 'dead') break;
    await sleep(POLL_MS);
  }
  if (state.follow !== runId) return;      // another run was opened in the meantime, or this one closed
  state.follow = '';                       // the record agrees: the objective is under way
  renderComposer();                        // and the control takes another word again
  if (state.run && state.run.id === runId) openStream();
}

/* --- the run's own console: the operator's channel on the session, standing beside the attach's mark --

   The session this page follows is the run's own, and SAH's console is the operator's channel on it:
   a line that begins with the operator's mark belongs to the operator, not the model — it never goes
   out as a word, and its outcome, an act or a refusal, is recorded as a `notice` beside the log by the
   session itself. The face is handed that surface as a whole, in the two places it reaches it: the menu
   the `/` mark opens — the commands the console names, in the order its table names them — and the
   control's own send, where a line the operator types and that begins with the mark rides the channel
   instead of the message route. What a line is, and whether the session runs it, refuses it, or answers
   it with its own list, is the console's judgement and not the face's: the face checks nothing the route
   and the session do not, and settles on the record the way the dials settle — the notice the console
   leaves is the answer, and a line the record never names is a line the pane does not believe.

   The commands that stand whole — the act complete without an argument — post on the pick. The commands
   that take one stand their own word in the control, after the words it already held, for the argument
   the operator types, and the line the send gives them rides the channel. The one that is a query — the
   session's vitals — stands the live console's own word: the one-line session it would ride in prints its
   answer to a console this page cannot read and records nothing, so the pick owes the operator the fact
   instead of a command that silently does nothing. */

// The commands the console names, in the order its table names them: the line the act posts, the word the
// item stands, and the word the operator is owed beside it. `whole` is the act complete on its own —
// the pick posts it — and `query` is the command whose word the one-line channel cannot stand.
export const CONSOLE_COMMANDS = [
  { line: '/model', label: '/model [ID]', claim: 'the endpoint the run talks to', whole: false },
  { line: '/think', label: '/think [LVL]', claim: 'the level the next turn runs at', whole: false },
  { line: '/compact', label: '/compact', claim: 'the compaction, now — the same act the trigger runs when the window is full', whole: true },
  { line: '/backto', label: '/backto [N]', claim: 'cut the conversation back before the operator’s Nth prompt', whole: false },
  { line: '/new', label: '/new', claim: 'start over from this run — the conversation in force detaches whole', whole: true },
  { line: '/fork', label: '/fork [N] “objective”', claim: 'branch the conversation into a new run; with a number, before the Nth prompt', whole: false },
  { line: '/export', label: '/export', claim: 'the run’s own report.md, now — the Markdown projection of everything the log holds', whole: true },
  { line: '/live', label: '/live', claim: 'the session’s vitals on demand — a query that prints and records nothing', query: true },
];

/** Open the console's menu at its mark, or close the one it already opened: the affordance is a toggle,
 * the face's own context menu, and the items are read when the menu opens, the way the row's menu is.
 */
export function slashMenu(anchor) {
  // The mark stands in the panel's corner, and the menu it opens owes the page's own space between its
  // right hand and the panel's edge — the shift the keep-on-screen math does not stand on its own. The
  // page's word for the space is the page's own token, read where the page stands.
  const shift = Number.parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--sahw-space-4')) || 0;
  toggleMenu(anchor, 'Console', () => CONSOLE_COMMANDS.map((entry) => ({
    label: entry.label,
    claim: entry.claim,
    onAct: () => slashPick(entry),
  })), shift);
}

/** The pick a menu item stands. A command the session runs whole posts on the pick; a command that takes
 * an argument stands its own word in the control for the operator's — the line it becomes rides the
 * channel when the send gives it, and the words the control already held keep their place before it;
 * and a query that the one-line channel cannot stand owes the operator the fact instead.
 */
export function slashPick(entry) {
  if (!state.run) return;
  if (entry.query) {
    state.notice = 'the one-line console carries the line, but its word stands only where the session’s '
      + 'own console reads it — the pane reads the record, and a query records nothing';
    renderChat();
    renderComposer();
    return;
  }
  if (entry.whole) {
    speakConsoleLine(entry.line);
    return;
  }
  const input = composerInput();
  const held = input ? String(input.value || '').trimEnd() : '';
  if (composer) composer.setDraft(held ? `${held}\n${entry.line}` : entry.line);
  if (input) input.focus();
}

/** The dial's own line, read from the line itself: `/model <id>` and `/think <lvl>` settle the dial the
 * way the picker does, because the console's notice for them is the dial's notice and the picker's stand
 * owes the same settle. The `none` the console spells stands for the level the face spells for the
 * absent — the face's own reading, so the settle confirms the way the picker's confirm.
 */
export function dialAskedBy(line) {
  const words = line.split(' ');
  if (words[0] === '/model' && words.length === 2) return { kind: 'model', value: words[1], at: Date.now() };
  if (words[0] === '/think' && words.length === 2)
    return { kind: 'think', value: words[1] === LEVEL_NONE ? DEFAULT_LEVEL : words[1], at: Date.now() };
  return null;
}

/** The console's child, waited for: it stamps its own `started` line and ends at the end of the input it
 * spoke, so the row says live while it works and settled after it — and the word it wrote stands in the
 * log before its ended line. A stream asked before the child has written replays the record without the
 * line and closes on the ending, and the word would stand in the log where the pane does not read it. If
 * the settle never stands — the child settled between two looks — the stream is asked anyway at the
 * caller: a replay stands whatever the log holds, and the line rode the channel either way.
 */
export async function settleConsoleChild(runId) {
  for (let attempt = 0; attempt < CONSOLE_SETTLE_TRIES; attempt += 1) {
    await refreshTree().catch(() => {});
    const found = findRun(runId);
    if (found && found.row.status === 'live') break;
    await sleep(POLL_MS);
  }
  for (let attempt = 0; attempt < CONSOLE_SETTLE_TRIES; attempt += 1) {
    await refreshTree().catch(() => {});
    const found = findRun(runId);
    if (found && found.row.status !== 'live') return;
    await sleep(POLL_MS);
  }
}

/** Speak one line of the session's own console at the run, and settle on the record the way the dials
 * do: the answer the route gives is the line carried, the console's notice beside the log is the
 * answer to it, and a run at rest holds no stream — so the stream is asked only after the record has
 * stood what the line did: the dial's own line settles the dial the picker does, and the other lines
 * wait for the console's child to settle, because a stream asked before the child has written stands
 * the record without the line. A refusal the route answers stands in the note hand in the route's own
 * words, and the draft the control held stays for the operator, because a line refused is a line the
 * operator gets to change.
 */
export async function speakConsoleLine(line) {
  const runId = state.run.id;
  state.sending = true;
  renderComposer();
  try {
    await api.command(runId, line);
    if (composer) composer.clearDraft();
    state.notice = '';
    const dial = dialAskedBy(line);
    if (dial) {
      state.dial.asked = dial;
      await askDials(runId);
    } else {
      await settleConsoleChild(runId);
    }
    if (state.run && state.run.id === runId) openStream();
  } catch (error) {
    state.notice = error.message;
    renderChat();
  } finally {
    state.sending = false;
    renderComposer();
  }
}

/** Whether a sent word is a line of the session's own console: it begins with the operator's mark and
 * is one line. What the line is — which command, and whether the session runs it — is not the face's
 * to judge: the console's dispatch answers a command it does not know with its own refusal beside the
 * log, and a line the route refuses for its shape stands the route's word in the note hand. A word that
 * does not begin with the mark goes out as a word, where words go.
 */
export function isConsoleLine(word) {
  return word.startsWith('/') && !word.includes('\n');
}

nodes.composer.addEventListener(SEND_EVENT, (event) => {
  event.preventDefault();
  // A word on the ride is not a steer: the queue holds it, the control is locked, and the send that
  // still reached the event is the queue's own mark's, answered with the queue's own fact.
  if (state.queued) {
    state.notice = 'the queue stands — release it, or stop the run';
    renderChat();
    renderComposer();
    return;
  }
  // One control and its faces: with a fork aimed the words open the branch, with no run open they describe
  // the run to start, and with a run open they go to that run — carrying the step an edit standing returns
  // to. Which of them the composer's face already said, and the server decides. A word that begins with
  // the operator's mark is none of the words: it is a line of the session's own console, and it rides the
  // channel the mark's menu posts through, never the message route.
  if (state.fork) forkRun(event.detail.request.text, event.detail.request.effort);
  else if (state.run) {
    const line = String(event.detail.request.text || '').trim();
    if (isConsoleLine(line)) {
      speakConsoleLine(line);
      return;
    }
    sendWord(event.detail.request.text, event.detail.request.effort);
  }
  else spawnRun(event.detail.request.text, event.detail.request.effort);
});
