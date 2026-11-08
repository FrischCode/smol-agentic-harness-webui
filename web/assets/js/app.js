/* SAHW — the entry: the boot, the event wiring, and the keyboard — the wiring that stands the regions up,
   in the face's own markup, names, and sheet. Nothing of a component kit is loaded to make any of it
   stand, and no other file of the face is loaded but the ones this one imports.

   The page owns no facts. The tree, the transcript, the folders and the files all come from the
   server, and what the face does with them is: ask for one, put what came back into the region that
   shows it, and remember which one that was. Two rules keep that honest.

   **Server text is never markup.** A path, a message, an error sentence — each reaches the page
   through `el()`/`textContent`, never through a string of HTML parsed into the document. A run's
   transcript is model output, and model output that the page parses as markup is a second protocol
   nobody designed and nobody secured, so no line of the face assigns `innerHTML`.

   **A region is one function of `state`.** Each `render*` reads the state and replaces its region's
   children wholesale; nothing is initialised after the fact, because the hands that answer a region
   either stand on the document (a chip's close, a menu's close-on-anywhere) or on markup that never
   leaves the page (the pane's engine, the composer). The transcript is the one region that cannot afford
   this per arriving frame — a live run's trace arrives at sixty frames a second — and the frames it owes
   stand in the trace's own module, where the frame's work is proportional to what arrived.

   **The face's own arrangement is the face's.** The one thing the face owns rather than mirrors is
   geometry: how wide each column is, which of them is folded away, where the sidebar's split stands,
   which run was open last, which runs the operator has put out of sight. None of it is in the runs
   root and nothing else reads it, so it lives in localStorage under `sahw.` — one key per concern,
   because a face that cannot read back one thing it wrote should lose that one thing and not the
   rest. It stands in the record's own file (web/assets/js/state.js), beside the record it is a view
   of, and it stays a view: archiving a run hides it from the tree and touches no byte of its folder,
   and a remembered run that has stopped listing is simply forgotten.

   **The face is modules, and its imports run one way.** `web/assets/js/state.js` is the record the page
   keeps — the regions, the memory, the one object, and the face's own arrangement; `web/assets/js/wire.js`
   is the one way the face reaches the server; `web/assets/js/components.js` is what every region shares —
   the glyphs, the paths, the kind claims, the marks; `web/assets/js/modal.js` is the consent the page asks
   before an act it cannot walk back. The regions of the face stand beside them, each in its own module:
   `trace.js` the words as they arrive; `menus.js` the rows' menu and the layers it floats on;
   `scroller.js` the pane's own scroller; `transcript.js` the log's steps and the acts on the record;
   `reading.js` the parser and the hands that stand the tokens; `tree.js` the pane's rows and the tick that
   keeps them; `composer.js` the composer's own hands and the run's own console. The foundations import
   nothing, a region imports the foundations and the public hands of the modules it calls — never another
   module's interior, and nothing that reaches up for the entry, which stands the boot and the wiring the
   regions owe — and this entry imports the modules and wires them: so the record, the wire and the
   components are readable without reading the page, and a region's work carries the region instead of the
   whole file. What the modules give back to the global scope is nothing at all.

   **The probes stand on the DOM.** Modules privatize what a single global scope used to lend, so a
   battery that reached for a face function by name would find nothing — and none is given one. Where a
   probe genuinely needs an act it cannot reach through the document, this entry stands one named hook for
   it and names every function on it; the audit of the standing batteries found no probe that needs it, so
   the hook has no name to stand yet, and the rule stands here until one does.
*/

import { nodes, store, DEFAULT_LEVEL, LEVEL_NONE, state, wireGeometry } from './state.js';
import { rawHref, exportHref, api } from './wire.js';
import {
  CUT_GLYPH, COPY_GLYPH, EXPLORER_GLYPH, BROWSE_GLYPH, DOWNLOAD_GLYPH, SELECT_GLYPH,
  ROW_FILE_GLYPH, NEW_FOLDER_GLYPH, SEND_GLYPH, QUEUE_GLYPH, EDIT_GLYPH, INFO_GLYPH,
  VIEW_GLYPH, REASONING_GLYPH, CHANGE_GLYPH, COMMAND_GLYPH, UNFOLD_GLYPH, FOLD_GLYPH,
  ARCHIVE_GLYPH, STOP_GLYPH, el, badge, workingMark, stateMark, rowWorking, basename,
  workspaceLabel, shortRunId, stepDigits, parentOf, childOf, parseStep, extensionOf,
  claimedKind, pictureKind, textKind, MARKDOWN_KINDS, claimedLanguage, imagePath,
  attachedPaths, receiptPaths, GONE_GLYPH, goneMark, FORK_GLYPH
} from './components.js';
import {
  UNDONE, confirmation, buildConfirmation, wireModal, askConfirmation, askName, OFF_DISK
} from './modal.js';
import { renderChat, renderHeader, renderTree } from './trace.js';
import {
  closeMenu, filterMark, toggleFilterPop, toggleMenu, wireMenus
} from './menus.js';
import { createMessageScroller } from './scroller.js';
import { wireChipHands, wirePlace } from './transcript.js';
import {
  jumpTypedPath, newFolderAct, openPane, pointComposer, refreshPane, renderBrowser, say,
  setEveryExpanded, treeHeadMenuItems, uploadPicked
} from './tree.js';
import {
  browse, browseTypedPath, openRun, readMachine, refreshTree, rememberedRun,
  renderAttachments, renderComposer, wireComposerClear, wireComposerHands, wireDials,
  wireHands, wireVisibility
} from './composer.js';

// --- the page, up ----------------------------------------------------------------------------------

/** Load the tree, open the run the face remembers (or the newest, for a face that remembers nothing),
 * and point the browser where the operator is most likely to spawn next.
 *
 * That is the opened run's workspace: the page just showed that run, and the run an operator starts
 * next usually stands in the same tree, so the browser opens where the work is rather than where a
 * path sorts first — the first workspace the tree names is the alphabetical first, which is a fact
 * about the machine, not about the operator. Failing a run at all, the first workspace the tree
 * names; failing even that, the drive root the server itself stands on.
 *
 * The face's own shape is put back before any of this: a column that opened at another width, or a
 * sidebar whose split the operator set last sitting, is the face forgetting the operator, and it is the
 * one thing on the page that does not come from the server.
 */
async function boot() {
  // The app shell's own worker, stood before anything else the page stands: the word the machine that
  // installs the face stands on (the install owes a worker the page registered), and the floor the face
  // keeps when the wire goes down. The registration is the worker's own business — a face that cannot
  // register it, a wire that is not a secure context, still stands on the wire, and the absence is the
  // worker's own sentence in the console, not the face's failure.
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(
      (error) => console.info('the app shell keeps to the wire: ' + error.message));
  }
  wireGeometry();
  // The pane's engine, stood before any row exists: it watches the surface the markup stands, so every
  // redraw of the transcript is something it hears rather than something it is told. It is stood at the
  // head of the boot because a pane that has not been stood at its end yet owes the reader no picture of
  // itself until it has been — that one frame is what the pending mark the engine writes hides.
  createMessageScroller(nodes.scroller);
  // The chips' hands, on the document: every chip the panes build is answered by them, whoever built it.
  wireChipHands();
  // The dialog's two outside hands, stood before the dialog is built: the sentence a refused act owes the
  // head of the pane it was asked from, and the row's menu taken away before the consent stands.
  wireModal({ say, closeMenu });
  buildConfirmation();
  wireMenus();
  wireVisibility();
  wireComposerClear();
  // The composer's own hands: the send's `Enter` and click, the dials' two triggers, and the marks that
  // stand in the row's corner. They stand before any region is drawn, because the composer is markup and
  // every draw of it reads the state these hands write.
  wireComposerHands();
  // The two dials: their own event answers to the operator's hand on them, and a hand that reaches for one
  // that stands down is answered where the event is captured, before the control hears it.
  wireDials();
  // The pane's own reading, kept as the reader's place: the hand stands before the first run opens, because
  // the boot's own reading of a pane that has not been stood yet is the one the keeping answers to first.
  wirePlace();
  // The hands and their tray: the tray is drawn from `state.attachments` like every other region, which
  // at this moment is nothing at all — an empty tray, and a composer at rest wearing no attachments.
  wireHands();
  renderAttachments();
  // The `+` the two pane heads share: the composer is pointed at the directory the Dir pane stands on,
  // so the act reached for out of either half of the sidebar lands on the same word.
  const pointHere = () => pointComposer(
    state.spawnDir || (state.listing ? state.listing.path : ''));
  nodes.spawnGo.addEventListener('click', pointHere);
  nodes.treeSpawnGo.addEventListener('click', pointHere);
  nodes.openTerminal.addEventListener('click', () => openPane('terminal'));
  nodes.openExplorer.addEventListener('click', () => openPane('explorer'));
  nodes.paneRefresh.addEventListener('click', refreshPane);
  // The two acts that change what the directory holds: a folder, asked by the modal the delete already
  // stands in, and files, handed over by the picker the mark stands over. Both answer into the pane's own
  // note and both leave the listing to the listing's own asking — `browse`, which is the only hand that
  // writes the pane's address.
  nodes.paneMkdir.addEventListener('click', newFolderAct);
  nodes.browserUpload.addEventListener('change', uploadPicked);
  // The pane's filter, on the one field the head's mark stands: the mark is the hand that opens the
  // field's popover, every keystroke narrows the rows already drawn — the machine is asked nothing,
  // because the rows are here and the operator's next character costs a re-draw — `Enter` is the way in
  // when the words read as a place rather than a narrowing, and the mark wears the word while it stands.
  nodes.browserFilterToggle.addEventListener('click', () => toggleFilterPop(nodes.browserFilterToggle));
  nodes.browserFilter.addEventListener('input', () => {
    state.listingFilter = nodes.browserFilter.value;
    filterMark(nodes.browserFilterToggle, nodes.browserFilter.value.trim() !== '');
    renderBrowser();
  });
  nodes.browserFilter.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') jumpTypedPath();
  });
  // The head's own two batch marks, aimed at every workspace at once: the act the rows used to wear beside
  // their acts, in the one place that aims at everything. Each mark stands dimmed while the tree already
  // stands in the state it names, the way the rows' marks did — the face does not offer an act it is
  // already doing — and that dimming is read where the tree is drawn, below.
  nodes.treeUnfold.addEventListener('click', () => setEveryExpanded(true));
  nodes.treeFold.addEventListener('click', () => setEveryExpanded(false));
  // The tree's own filter, on the one field its mark stands, narrowing the rows it holds and nothing
  // else: the pane's filter over the directory never reads it and it never reads the pane's, because the
  // two lists answer two questions and a word that crossed them would be one control claiming both
  // folders and runs hold it.
  nodes.treeFilterToggle.addEventListener('click', () => toggleFilterPop(nodes.treeFilterToggle));
  nodes.treeFilter.addEventListener('input', () => {
    state.treeFilter = nodes.treeFilter.value;
    filterMark(nodes.treeFilterToggle, nodes.treeFilter.value.trim() !== '');
    renderTree();
  });
  // The tree's own batch acts the head keeps behind its menu, over every workspace at once. The affordance
  // is the head's own markup and the layer is the rows' own machinery, its items read as it opens so their
  // words follow the state; the label it stands under names what the acts are aimed at, the way a row's
  // menu names its row.
  nodes.treeMenu.addEventListener('click', () => toggleMenu(nodes.treeMenu, 'every workspace',
    treeHeadMenuItems));
  // The path line's one act, and it is the keyboard's: `Enter` lists what was typed exactly as a click on
  // a row lists what was clicked. No button stands beside the line to do it — the pane's head keeps its
  // three acts and the `+`, and the line is the fourth hand, not a fourth button.
  nodes.browserPath.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') browseTypedPath();
  });
  try {
    await refreshTree();
  } catch (error) {
    // The centre is where a sentence about the page going wrong belongs: the tree that would have
    // shown runs stays empty, and the reason is the one thing worth reading in its place.
    state.notice = error.message;
    renderTree();
  }
  // The picker before the runs: the machine's registry is what the two dials may be moved to, and a run
  // opened below settles its own stand on top of it. Read after the tree only because the tree is what the
  // pane is empty without; neither answer depends on the other.
  await readMachine();
  const opened = rememberedRun();
  const first = opened ? opened.workspace
    : (state.workspaces.length ? state.workspaces[0].path : '/');
  await browse(first);
  if (state.listing && state.listing.error && first !== '/') await browse('/');
  if (opened) openRun(opened.row, opened.workspace);
  else {
    renderHeader();
    renderChat();
    renderComposer();
  }
}

boot();
