/* web/assets/js/state.js — the page's own record: the regions it draws into, the memory it keeps between one
   standing of the page and the next, and the one object every region reads.

   `nodes` are the regions, resolved once out of the markup `index.html` declares — every render fills one
   of them and nothing else is written. `store` is the browser's own memory, namespaced under `sahw.` and
   forgiving of a value it cannot read: the face's widths, folds and shelves, never a claim about the
   record, which lives in the runs root and is read from there by everyone. `state` is what the page
   remembers between one render and the next and nothing else, which is why any region can be re-drawn from
   scratch. The levels the thinking dial is spelled with stand here because the record holds a level:
   `state.dial.think` is born at `DEFAULT_LEVEL`, and the face's own spelling of the absence is
   `LEVEL_NONE`.

   The face's own arrangement stands with the record, because it is the face's own and the record's own
   memory keeps it: how wide each column is, which of them is folded away, where the sidebar's split
   stands — the one thing the face owns rather than mirrors, held between one standing of the page and
   the next rather than claimed of the record. The arrangement's own hands stand beside it here, and the
   entry stands them on the page at the boot (wireGeometry), the way it stands every other hand.

   The record is exported live, the way the page already stood it: the one object, mutated in place by
   whichever region holds the fact, so every importer reads what the page keeps rather than a copy of it.
   It imports nothing — not the wire, not a region, not another foundation — because the record cannot ask
   what the page is showing. That is the bottom of the one way the face's imports run.
   */

// The regions, resolved once: every render fills one of these and nothing else is written.
export const nodes = {
  shell: document.getElementById('shell'),
  left: document.getElementById('left'),
  split: document.getElementById('split'),
  treePane: document.getElementById('pane-tree'),
  browserPane: document.getElementById('pane-browser'),
  spawnGo: document.getElementById('spawn-go'),
  treeSpawnGo: document.getElementById('tree-spawn-go'),
  edgeLeft: document.getElementById('edge-left'),
  edgeRight: document.getElementById('edge-right'),
  foldLeft: document.getElementById('fold-left'),
  foldRight: document.getElementById('fold-right'),
  badges: document.getElementById('header-badges'),
  tree: document.getElementById('tree'),
  treeHead: document.getElementById('tree-head'),
  treeUnfold: document.getElementById('tree-unfold'),
  treeFold: document.getElementById('tree-fold'),
  treeMenu: document.getElementById('tree-menu'),
  treeNote: document.getElementById('tree-note'),
  treeFilter: document.getElementById('tree-filter'),
  treeFilterToggle: document.getElementById('tree-filter-toggle'),
  treeFilterPop: document.getElementById('tree-filter-pop'),
  browserPath: document.getElementById('browser-path'),
  browser: document.getElementById('browser'),
  browserNote: document.getElementById('browser-note'),
  browserFilter: document.getElementById('browser-filter'),
  browserFilterToggle: document.getElementById('browser-filter-toggle'),
  browserFilterPop: document.getElementById('browser-filter-pop'),
  openTerminal: document.getElementById('open-terminal'),
  openExplorer: document.getElementById('open-explorer'),
  paneRefresh: document.getElementById('pane-refresh'),
  paneMkdir: document.getElementById('pane-mkdir'),
  paneUpload: document.getElementById('pane-upload'),
  browserUpload: document.getElementById('browser-upload'),
  scroller: document.getElementById('scroller'),
  messages: document.getElementById('messages'),
  composer: document.getElementById('composer'),
  composerInput: document.getElementById('composer-input'),
  composerSend: document.getElementById('composer-send'),
  composerActs: document.getElementById('composer-acts'),
  thought: document.getElementById('composer-thought'),
  attach: document.getElementById('attach-input'),
  attachMark: document.getElementById('attach'),
  slash: document.getElementById('slash'),
  attachTray: document.getElementById('attach-tray'),
  preview: document.getElementById('preview'),
};

// --- the face's own memory ---------------------------------------------------------------------------

/* localStorage, namespaced and forgiving. One key per concern, because a value that does not parse is
   no value at all and the fallback is the value the page would have worn had it never remembered.
   Nothing the record holds is kept here — the runs root is the record — and nothing written here is a
   claim about it: these are the face's widths, folds, and which rows the operator was looking at. */
export const MEMORY = 'sahw.';
export const store = {
  read(key, fallback) {
    try {
      const raw = window.localStorage.getItem(MEMORY + key);
      return raw === null || raw === '' ? fallback : JSON.parse(raw);
    } catch {
      return fallback;
    }
  },
  write(key, value) {
    try {
      window.localStorage.setItem(MEMORY + key, JSON.stringify(value));
    } catch {
      // A face that cannot remember still works; the memory is the face's, and so is the loss.
    }
  },
};

// A remembered list, or nothing: a value that is not the array it was written as is not a list the page
// can read, and a set built out of a string is a set of its characters.
export const storedList = (key) => {
  const value = store.read(key, []);
  return Array.isArray(value) ? value : [];
};

// The face's own word for leaving the level alone: 'default' is not a level — it sends no `--think` at a
// launch, so the machine's own default (SAH_THINK, then the endpoint's) applies. SAH's console spells the
// same absence `none`, which is the word the record carries and the word a `/think` line has to carry back
// — the endpoint has no level called 'default'. The levels themselves the machine's table names, per
// profile: the dial's words are the operator's statement about the box, and the face keeps no list of its
// own to be wrong about.
export const DEFAULT_LEVEL = 'default';
export const LEVEL_NONE = 'none';

// What the page remembers between one render and the next — and nothing else, which is why a
// render can always be re-run from scratch.
export const state = {
  workspaces: [], // the tree, as `/api/runs` last answered
  expanded: new Set(storedList('expanded')), // the workspace paths shown with their runs open
  archived: new Set(storedList('archived')), // the runs hidden from the tree, by id — the folders stand
  showArchived: false, // whether the tree is showing the shelf instead of the runs
  run: null, // the opened run: {id, model, status, live}, the row the tree answered with
  steps: [], // the opened run's steps, in log order, as they arrived
  seen: new Set(), // the step ids already in the pane, so a replayed log reconciles with it
  follow: '', // a run this page followed up, until its new objective shows up in the log
  steer: '', // a word queued as a steer, until the record carries it back
  // The edit standing in the composer, or null: the step the send would return the conversation to, as
  // the log's id and as the digits the route is posted with. The words being edited are the composer's —
  // this is only the aim, and it is what makes the composer's face an editing one.
  edit: null,
  // The fork standing in the composer, or null: the run whose conversation the next word branches, and
  // the step its carried prefix ends at (empty for the whole conversation, which is the row-menu act —
  // the per-message act names the step it was clicked from). The objective is the composer's own words.
  fork: null,
  // The files standing attached to the word being composed: each is the browser's own file, the name it
  // arrived with, and — for a picture, and only for a picture — the address its thumb is painted from.
  // They ride the next send and that send clears them — what went out with a word is no longer the page's
  // to hold — and a send that was refused keeps them, exactly as it keeps the words it was refused with.
  attachments: [],
  attachRefused: 0, // the files the room would not take on the last hand; the count an overreaching hand leaves behind
  sending: false, // whether a send is on the wire, the only moment the control refuses another
  notice: '', // a sentence the transcript owes the reader: a failed send, a closed stream
  // The turn whose own line stands open, or none: the id of the segment the info panel is standing
  // under. A second mark clicked elsewhere aims it there, a second click on the same mark closes it.
  // It survives the render because the panel is built from it, not held beside the mark it opened.
  infoOpen: '',
  // The changes the reader has asked the pane to stand: the ids of the `edit` calls whose change stands
  // open under its line. The reading is written from the record's own words whenever the row is drawn,
  // so this set holds nothing but the asking — and it goes with the run the asking was aimed at.
  changes: new Set(),
  // The commands the reader has asked the pane to stand: the ids of the `bash` calls whose whole command
  // stands open under its line. The asking is all this set holds — the word it stands is the record's own
  // call's, read again whenever the row is drawn — and a frame the record speaks re-stands the asking
  // standing, because the render is not an asking. It goes with the run the asking was aimed at.
  commands: new Set(),
  // The trace's in-flight faces, and nothing else: `prose` is the turn whose `message` step has not
  // landed (one string and the moment its first fragment arrived), `reasoning` is the thought that
  // turn is thinking into it, and `tools` is the output of the calls whose `result` step has not
  // landed, keyed by the call step's id. Display state every word of it owes a step: it is emptied
  // when those steps land, when the stream ends, and when the run is replaced or closed — and a
  // stream carrying no delta frames never fills it, which is what keeps a run started without SAH's
  // `--live` the pane it always was.
  partials: { prose: null, tools: new Map(), reasoning: null },
  spawnDir: '', // the directory a new run would start in
  listing: null, // the browser's answer for `spawnDir`, or that answer's error
  treeNotice: '', // the sentence the tree's head owes: a delete the machine refused, in its words
  paneNotice: '', // the same at the directory pane's head: a window the machine would not open
  // The two filters, each the pane's own view over what it already drew and nothing else: the words typed
  // into the head's line, held here so a re-draw narrows the same rows the operator is looking at and an
  // empty word restores all of them. Neither is remembered across a reload, neither is sent anywhere, and
  // they do not read each other — the listing the pane holds and the rows the tree holds are two answers
  // to two questions, and a filter that crossed them would be one control lying about the other pane.
  // The pane's own is cleared when the listing changes, since a filter over a folder that is not the one
  // being looked at is a listing that shows nothing for no reason the operator can see.
  listingFilter: '',
  treeFilter: '',
  file: null, // the previewed file: {path, content, truncated}, or {path, error}
  // The same again at the preview's head: the editor the machine would not open. It is the file's own
  // sentence, so a new file and the close both take it away.
  fileNotice: '',
  // How the preview reads a file of words: false is the rendering the name claims — the document a
  // markdown name stands, the highlighting a carried code name stands — and true is the file's own words
  // plain. The operator's one standing for every file, not a fact about any one of them.
  raw: store.read('preview.raw', false) === true,
  // The machine's model registry, as `/api/models` answered it: the profiles' entries when it answered,
  // and null when it refused, the picker then standing on the one thing that is true, which is that the
  // machine names none. `machine` is the reference a run launched from this tree speaks as when nothing
  // names a model, which is where the picker stands until a run's own record says otherwise.
  profiles: null,
  machine: '',
  // What the two dials stand on, settled from the record rather than from the picker's last click — and
  // with no run open, from the standing the page keeps for the run it has not started, so a pick made on
  // the spawn face is the standing a launch will ride — the model's name as the record states it
  // ('' until anything states one), the address a switch named
  // beside it, the level in the face's own spelling, the sentence the dials owe the note hand, the switch
  // this page has spoken and is waiting for the record to confirm, and the mark that says the control is
  // moving on the record's word and nobody's hand.
  dial: { name: '', endpoint: '', think: DEFAULT_LEVEL, word: '', asked: null, settling: false,
          reading: false },
  // The thought a turn stands in, shown or hidden, under the operator's own eye: remembered, because a
  // hiding the operator made is the operator's to keep between the page's standings.
  thoughtShown: store.read('thought.shown', true) !== false,
  stream: null, // the opened run's EventSource, closed when the run ends or is replaced
  reattach: null, // a pending ask again for a dropped stream: the timer id, cleared when the face moves on
};

// --- the face's own arrangement: the columns, the folds, the split -----------------------------------

/* Three numbers and two switches, all of them the operator's: the width of each side column, the share
   of the sidebar the upper half keeps, and whether either column is folded to nothing. The grid reads
   the widths off the two custom properties the document carries, a fold sets one of them to `0px` and
   stops the column rendering at all, and the split is written to the two halves as their share of the
   height between them — a share, not a pixel count, because it has to survive a window that changed
   size between one sitting and the next. */
export const COLUMN_MIN = 220; // narrower than this a run id is cut and a path is unreadable
export const CENTRE_MIN = 420; // the chat keeps at least this much of the window
export const HALF_MIN = 64;    // the few rows neither half of the sidebar may be squeezed below

export const number = (value, fallback) => (typeof value === 'number' && Number.isFinite(value) ? value : fallback);
export const remembered = (key, fallback) => number(store.read(key, fallback), fallback);

export const geometry = {
  left: remembered('width.left', 320),
  right: remembered('width.right', 420),
  leftFolded: store.read('fold.left', false) === true,
  // The preview column's fold is not a remembered choice: it is a fact about the file the column
  // holds (see syncPreviewColumn), and a fresh load holds no file, so the column stands folded.
  rightFolded: true,
  split: Math.min(1, Math.max(0, remembered('split', 0.5))),
};

// The right line's own listeners, kept so the line can stand down with the file its column holds: a
// handle that no column is waiting for is a handle that must not be listening.
export let rightEdgeListeners = null;

/** Put the arrangement on the page. This is the one place any of it is written, so a drag, a fold and a
 * remembered load all arrive here and the page can never be holding two answers about its own shape. */
export function applyGeometry() {
  const wide = document.documentElement.style;
  wide.setProperty('--sahw-left', `${geometry.leftFolded ? 0 : geometry.left}px`);
  wide.setProperty('--sahw-right', `${geometry.rightFolded ? 0 : geometry.right}px`);
  nodes.shell.classList.toggle('sahw-shell--left-folded', geometry.leftFolded);
  nodes.shell.classList.toggle('sahw-shell--right-folded', geometry.rightFolded);
  renderFold(nodes.foldLeft, 'left');
  renderFold(nodes.foldRight, 'right');
  nodes.treePane.style.flexGrow = String(geometry.split);
  nodes.browserPane.style.flexGrow = String(1 - geometry.split);
  nodes.split.setAttribute('aria-valuenow', String(Math.round(geometry.split * 100)));
}

/** A fold button, in the direction it is about to move the column and the words that say so. */
export function renderFold(button, side) {
  const folded = geometry[`${side}Folded`];
  const name = side === 'left' ? 'sidebar' : 'file preview';
  button.textContent = (folded ? (side === 'left' ? '»' : '«') : (side === 'left' ? '«' : '»'));
  button.title = `${folded ? 'Show' : 'Hide'} the ${name}`;
  button.setAttribute('aria-label', button.title);
  button.setAttribute('aria-expanded', String(!folded));
}

/** A column's width, kept between what is readable and what the window has: the two columns and the
 * centre all have to fit, so how wide one may be is a fact about the other and the window. */
export function clampWidth(px, side) {
  const other = side === 'left' ? geometry.right : geometry.left;
  const room = Math.max(COLUMN_MIN, window.innerWidth - other - CENTRE_MIN);
  return Math.min(Math.max(COLUMN_MIN, px), room);
}

export function setWidth(side, px) {
  geometry[side] = clampWidth(px, side);
  applyGeometry();
}

export function setFolded(side, folded) {
  if (geometry[`${side}Folded`] === folded) return;
  geometry[`${side}Folded`] = folded;
  // The left column's fold is a choice the operator made, and the page owes it to keep. The right
  // column's fold is a fact about the file it holds (see syncPreviewColumn), and the store keeps no
  // half of a fact.
  if (side === 'left') store.write('fold.left', folded);
  applyGeometry();
}

/** The split, as a share of the height the two halves were given, floored so that neither half is
 * squeezed below a few rows: the operator trades estate between them, not existence. */
export function setSplit(share) {
  const floor = Math.min(0.5, HALF_MIN / Math.max(1, nodes.left.clientHeight));
  geometry.split = Math.min(1 - floor, Math.max(floor, share));
  applyGeometry();
}

/** The column the file stands in follows the file: it opens when a file is looked at, and it goes —
 * frame, line, and the line's own listeners — when the file goes, because a column that holds nothing
 * holds no line to drag. The column's fold is that fact, not a choice, so the store keeps no half of
 * it (see `setFolded`). */
export function syncPreviewColumn() {
  const loaded = Boolean(state.file);
  nodes.shell.classList.toggle('sahw-shell--right-idle', !loaded);
  if (!rightEdgeListeners) return; // the geometry is not wired yet: the boot's own call stands it down
  for (const [type, listener] of rightEdgeListeners) {
    if (loaded) nodes.edgeRight.addEventListener(type, listener);
    else nodes.edgeRight.removeEventListener(type, listener);
  }
  if (loaded && geometry.rightFolded) setFolded('right', false);
  if (!loaded && !geometry.rightFolded) setFolded('right', true);
}

/** A drag along a line: down on the line, moves while the button is held, up ends it and the position
 * is written down. `track` is the axis the line runs along, `start` answers with the value the drag
 * began from, `move` takes it as it should be now and re-renders as it goes — a dragged pane is dragged,
 * not guessed at and corrected when the hand lets go. `sign` is the direction the drag works in: a line
 * beside the left column grows that column as the hand goes right, while the line beside the right
 * column is the right column's left boundary, so the same hand makes that column give ground. A press
 * that begins on a child of the line — the fold that stands on it — is the child's, not the drag's:
 * answering it would swallow the click the fold is waiting for. `begin`, when given, is the move the
 * drag owes before it measures: the line of a folded column stands at the window's rim, and the hand on
 * that rim is asking for the column, so a drag on it unfolds the column and then works the width. The listener is returned, so a line that can stand down
 * can take its listener with it. */
export function dragLine(handle, track, start, move, end, sign = 1, begin) {
  const down = (event) => {
    if (event.button !== 0 || event.isPrimary === false) return;
    if (event.target !== handle) return;
    event.preventDefault();
    if (typeof handle.setPointerCapture === 'function' && event.pointerId !== undefined) {
      handle.setPointerCapture(event.pointerId);
    }
    if (begin) begin();
    const from = start();
    const coordinate = (one) => (track === 'x' ? one.clientX : one.clientY);
    const going = (event2) => {
      if (event.pointerId !== undefined && event2.pointerId !== event.pointerId) return;
      move(from + sign * (coordinate(event2) - coordinate(event)));
    };
    const stop = (event2) => {
      if (event.pointerId !== undefined && event2.pointerId !== event.pointerId) return;
      window.removeEventListener('pointermove', going);
      window.removeEventListener('pointerup', stop);
      window.removeEventListener('pointercancel', stop);
      end();
    };
    window.addEventListener('pointermove', going);
    window.addEventListener('pointerup', stop);
    window.addEventListener('pointercancel', stop);
  };
  handle.addEventListener('pointerdown', down);
  return down;
}

/** The arrows on a separator: the same moves the drag makes, for a hand that is on the keyboard, in the
 * same direction the drag works (see `dragLine`'s `sign`), and the same beginning move (`begin`) when the
 * column is folded away. The listener is returned, for the same reason the drag's is. */
export function keyLine(handle, track, start, move, step, end, sign = 1, begin) {
  const keys = (event) => {
    const back = track === 'x' ? 'ArrowLeft' : 'ArrowUp';
    const on = track === 'x' ? 'ArrowRight' : 'ArrowDown';
    if (event.key !== back && event.key !== on) return;
    event.preventDefault();
    if (begin) begin();
    const delta = event.key === on ? step : -step;
    move(start() + sign * delta);
    end();
  };
  handle.addEventListener('keydown', keys);
  return keys;
}

/** Wire the three lines the page is measured by and the two folds that put a column away. */
export function wireGeometry() {
  const height = () => Math.max(1, nodes.left.clientHeight);
  const leftEdge = () => geometry.left;
  const rightEdge = () => geometry.right;
  const splitPx = () => geometry.split * height();
  dragLine(nodes.edgeLeft, 'x', leftEdge, (px) => setWidth('left', px),
    () => store.write('width.left', geometry.left), 1,
    () => { if (geometry.leftFolded) setFolded('left', false); });
  rightEdgeListeners = [
    ['pointerdown', dragLine(nodes.edgeRight, 'x', rightEdge, (px) => setWidth('right', px),
      () => store.write('width.right', geometry.right), -1,
      () => { if (geometry.rightFolded) setFolded('right', false); })],
    ['keydown', keyLine(nodes.edgeRight, 'x', rightEdge, (px) => setWidth('right', px), 24,
      () => store.write('width.right', geometry.right), -1,
      () => { if (geometry.rightFolded) setFolded('right', false); })],
  ];
  dragLine(nodes.split, 'y', splitPx, (px) => setSplit(px / height()),
    () => store.write('split', geometry.split));
  keyLine(nodes.edgeLeft, 'x', leftEdge, (px) => setWidth('left', px), 24,
    () => store.write('width.left', geometry.left), 1,
    () => { if (geometry.leftFolded) setFolded('left', false); });
  keyLine(nodes.split, 'y', splitPx, (px) => setSplit(px / height()),
    () => height() * 0.05, () => store.write('split', geometry.split));
  nodes.foldLeft.addEventListener('click', () => setFolded('left', !geometry.leftFolded));
  nodes.foldRight.addEventListener('click', () => setFolded('right', !geometry.rightFolded));
  applyGeometry();
  syncPreviewColumn(); // the boot's own file is no file: the line stands down with it
}
