/* web/assets/js/tree.js — the pane's filter; the directory's own three acts; the pane's rows and the acts
   each one is owed; the folder's three acts worn by every row of the tree; the tree head's menu.

   The rows stand as the listing holds them — the folder that walks in, the file that opens in the
   preview, the folder's three acts worn by every row, and the head's menu over the whole tree — and the
   acts each row is owed stand beside the row they act on, answered in the pane's own note.

   The tick's mechanism stands beside the rows, because the span a row's time wears is made for the row
   it stands in — so the clock the rows keep stands with them, where the record it is a view of stands
   with the face's own arrangement. The row the tick keeps — `ticking`, emptied and refilled by the
   render that stands it — stands with that render, in the trace room, and the tick imports it the way
   it imports the rows.
   */

import { nodes, store, state, syncPreviewColumn } from './state.js';
import { rawHref, exportHref, api } from './wire.js';
import {
  COPY_GLYPH, EXPLORER_GLYPH, BROWSE_GLYPH, DOWNLOAD_GLYPH, SELECT_GLYPH, ROW_FILE_GLYPH,
  NEW_FOLDER_GLYPH, EDIT_GLYPH, UNFOLD_GLYPH, FOLD_GLYPH, ARCHIVE_GLYPH, STOP_GLYPH, el,
  workingMark, stateMark, rowWorking, basename, workspaceLabel, parentOf, childOf,
  pictureKind, GONE_GLYPH, FORK_GLYPH
} from './components.js';
import { UNDONE, askConfirmation, askName, OFF_DISK } from './modal.js';
import {
  action, nameButton, renderChat, renderHeader, renderTree, runName, ticking
} from './trace.js';
import { rowMenu, toggleNamePop } from './menus.js';
import {
  afterDelete, deleteRunAct, deleteWorkspaceAct, pruneRuns, renderPreview, runAct,
  stopRunAct
} from './transcript.js';
import {
  armFork, browse, closeStream, composer, focusComposer, lockInput, openRun, paintDials,
  renderComposer, resetDials, runWorks
} from './composer.js';

// --- the clock: every row says when, and a row still working says for how long ------------------------

/* A step's `ts` is already on the stream: it is the moment the log took the step, and the row that
   shows the step shows it. The one row the clock is really for is a call whose answer has not arrived:
   the operator's question there is not *when did it start* but *is it working, and has it been working*,
   and that row says how long ago it started instead, and says it again every second.

   The tick rewrites those spans where they stand rather than re-rendering the transcript: the spans are
   the transcript's own render's output, and `ticking` is emptied and refilled by every render of it, so
   what the tick holds is always the rows on the page and nothing else. A run that is not working has no
   such row and no tick; neither does a replay, which is what makes a replayed run stand still. */
export const TICK_MS = 1000;
export let tickTimer = 0;

export const two = (value) => String(value).padStart(2, '0');

/** The moment a step was logged, or null for a step the record never stamped — a step the pane has no
 * time for is a step the pane says nothing about, rather than one it invents a time for. */
export function logged(step) {
  const stamp = typeof step.ts === 'string' ? Date.parse(step.ts) : Number.NaN;
  return Number.isNaN(stamp) ? null : stamp;
}

/** A moment, in the reader's own local time. */
export function clockText(at) {
  const when = new Date(at);
  return `${two(when.getHours())}:${two(when.getMinutes())}:${two(when.getSeconds())}`;
}

/** How long ago, told so that five seconds and ten minutes do not read alike. */
export function elapsedText(since) {
  const seconds = Math.max(0, Math.round((Date.now() - since) / 1000));
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m${two(seconds % 60)}s`;
  return `${Math.floor(minutes / 60)}h${two(minutes % 60)}m`;
}

/** The row's clock. `working` is the call that is still waiting for its answer: its own start is what
 * there is to tell, and it is told as an elapsed time that keeps the span company in the tick. */
export function clockSpan(step, working) {
  const at = logged(step);
  if (at === null) return null;
  const span = el('span', 'sahw-time');
  if (!working) {
    span.textContent = clockText(at);
    span.title = `logged ${new Date(at).toLocaleString()}`;
    return span;
  }
  span.textContent = elapsedText(at);
  const claim = `working since ${clockText(at)}`;
  span.title = claim;
  span.setAttribute('aria-label', claim);
  ticking.push({ span, at });
  return span;
}

/** The spans the last render left working, told what time it is now. */
export function tickClocks() {
  for (const row of ticking) row.span.textContent = elapsedText(row.at);
}

/** One second at a time, and only while something is working — a stopped run is not a clock. */
export function keepClocks() {
  const live = ticking.length > 0 && runWorks();
  if (live && !tickTimer) tickTimer = setInterval(tickClocks, TICK_MS);
  if (!live && tickTimer) {
    clearInterval(tickTimer);
    tickTimer = 0;
  }
}

/* --- the folder's three acts, worn by every row of the tree ---------------------------------------------

   A row stands on a folder: a workspace row on the path its runs were run in, a run row on the workspace its
   run ran in — the tree groups a run under the workspace it ran in, and the run's record folder in the runs
   root is the record's place, which is not the folder any of these acts is asked about. Three acts are owed
   in the row's own menu, and every one of them already stands on the page: the clipboard the row's hover-copy
   writes and the sentence it answers a withholding browser with, `/api/open` the dir's head
   speaks for the folder the pane stands on, and `browse` — the pane's own word for the folder a listing was
   asked for and the next run starts in. Nothing here is a new act; the three are worn at the row.
*/

/** The row's folder, onto the clipboard: the path the row names and nothing else. The clipboard is the
 * browser's own act, and a browser that withholds it is answered the way every refusal on this face is — a
 * sentence at the head of the tree the act was asked from, the act left undone. */
/** Say a sentence in the head of the pane the act was asked from. Two panes keep a note — the tree's holds
 * the record's refusals and the dir's holds the folder's — and an act says which one it owes
 * rather than both saying everything twice. */
export function say(sentence, atPane) {
  if (atPane) {
    state.paneNotice = sentence;
    renderBrowser();
    return;
  }
  state.treeNotice = sentence;
  renderTree();
}

export function copyPathAct(path, atPane) {
  navigator.clipboard.writeText(path).catch(() => {
    say('the clipboard would not take the path; the browser refused', atPane);
  });
}

/** The machine's own window on a folder a row names: the dir's act, aimed at a folder the pane
 * has never listed. `{ok: true}` is the window having been asked for, which is the end of the sentence; a
 * `false`, or a route that answered for no window at all, is this machine's own words about why it did not
 * start, and they stand at the head of the pane the act was asked from. */
export async function openRowWindow(kind, path, atPane) {
  let sentence = '';
  try {
    const answer = await api.open(kind, path);
    if (!answer || !answer.ok) sentence = (answer && answer.reason) || 'the window was not opened';
  } catch (error) {
    sentence = error.message;
  }
  say(sentence, atPane);
}

/** The acts of the folder the row stands on: the path to the clipboard, the machine's window on the
 * folder, and — for the workspace row that owns the folder — the dir pointed at it. The run
 * row keeps the first two: the pointing names the same folder the parent row already points at, and a row
 * does not offer its parent's act twice. Each claim names its act with the path it stands on; the list is
 * read when the menu opens, so the path is the row's own at the moment the menu stands. */
export function folderActItems(path, withPointing = true) {
  const items = [
    {
      label: 'Copy path',
      glyph: COPY_GLYPH,
      claim: `Copy ${path} to the clipboard — the folder the row stands on, ready to paste`,
      onAct: () => copyPathAct(path, false),
    },
    {
      label: 'Open in explorer',
      glyph: EXPLORER_GLYPH,
      claim: `Open the file explorer on ${path}`,
      onAct: () => openRowWindow('explorer', path, false),
    },
  ];
  if (withPointing) {
    items.push({
      label: 'Browse',
      glyph: BROWSE_GLYPH,
      claim: `List ${path} in the dir — the next run starts there`,
      onAct: () => browse(path),
    });
  }
  return items;
}

/** The workspace menu: hide every run of it, the three acts the folder the row stands on owes — its path
 * to the clipboard, the machine's window on it, the dir pointed at it — and take every run of it off
 * disk, last: the act that cannot be walked back stands where a hand that means it finds it, and
 * nowhere earlier. */
export function workspaceMenuItems(workspace) {
  const allHidden = workspace.runs.length > 0
    && workspace.runs.every((row) => state.archived.has(row.id));
  return [
    {
      label: allHidden ? 'Un-archive all' : 'Archive all',
      glyph: ARCHIVE_GLYPH,
      claim: `${allHidden ? 'Show the runs of ' : 'Hide the runs of '}${workspace.path} — `
        + 'their folders and their logs are untouched',
      onAct: () => archiveRuns(workspace.runs.map((row) => row.id), allHidden),
    },
    ...folderActItems(workspace.path),
    {
      label: 'Delete all',
      glyph: GONE_GLYPH,
      claim: `Delete every run of ${workspace.path} from disk`,
      danger: true,
      onAct: () => deleteWorkspaceAct(workspace),
    },
  ];
}

/* --- the tree head's menu: the rows' own acts, spoken to the whole tree ------------------------------------

   The head's `⋮` offers nothing a row does not already offer: it is the batch over all of them at once. The
   two fold items are the workspace row's own buttons aimed at every workspace; the archive item follows the
   state exactly as the workspace item does, reading Un-archive all once every run the tree lists stands
   behind the shelf; and the delete is the one act that cannot be walked back, so it stands behind the page's
   consent, named as the batch it is — the count the per-workspace acts would sum, and every workspace those
   runs stand in.
*/

/** Every run the tree lists, by id, in the tree's own order: the batch the head's acts are aimed at. */
export const everyRunId = () => state.workspaces.flatMap((workspace) => workspace.runs.map((row) => row.id));

/** Open every workspace that holds a run, or close them all: the row buttons' act, spoken once to the whole
 * tree. The shelf is not the expansion — folding asks a run to stand under no row, and a run the shelf is
 * showing keeps standing there, which is why this act leaves the shelf exactly as it found it. */
export function setEveryExpanded(open) {
  for (const workspace of state.workspaces) {
    if (open && !workspace.runs.length) continue; // a workspace with no runs has no runs to unfold
    setExpanded(workspace.path, open);
  }
  renderTree();
}

/** Delete every run of every workspace: one ask of the one route, behind the page's consent. The count is
 * the act named, since a batch of batches has no one id to name, and the workspaces are named with it
 * because the act reaches past any one of them. */
export function deleteEveryRunAct() {
  const held = state.workspaces.filter((workspace) => workspace.runs.length);
  const total = held.reduce((sum, workspace) => sum + workspace.runs.length, 0);
  const said = total === 1 ? '1 run' : `${total} runs`;
  const where = held.length
    ? `${held.length === 1 ? '1 workspace' : `${held.length} workspaces`}: `
      + held.map((workspace) => workspace.path).join(', ')
    : 'no workspace at all';
  askConfirmation({
    title: 'Delete every run of every workspace',
    lines: [`The ${said} of ${where}`, OFF_DISK, UNDONE],
    confirm: `Delete ${said}`,
  }, () => runAct(api.deleteAll(), (answer) => {
    pruneRuns(Array.isArray(answer.deleted) ? answer.deleted : []);
    afterDelete('');
  }));
}

/** The head's two items, in the order the acts give and take: archive, delete. Unfold and fold stand as
 * the head's own marks, where the whole of the tree is their aim; the words here follow the state where a
 * state is behind them, as the rows' words do. */
export function treeHeadMenuItems() {
  const runIds = everyRunId();
  const allHidden = runIds.length > 0 && runIds.every((id) => state.archived.has(id));
  return [
    {
      label: allHidden ? 'Un-archive all' : 'Archive all',
      glyph: ARCHIVE_GLYPH,
      claim: `${allHidden ? 'Show every run of every workspace' : 'Hide every run of every workspace'} — `
        + 'their folders and their logs are untouched',
      onAct: () => archiveRuns(runIds, allHidden),
    },
    {
      label: 'Delete all',
      glyph: GONE_GLYPH,
      claim: 'Delete every run of every workspace from disk',
      danger: true,
      onAct: () => deleteEveryRunAct(),
    },
  ];
}

/** The run menu: the stop (on a run that works), the fork, the archive, the two copy items below it —
 * the run's own hover made pasteable and the folder's path — the folder's clipboard and explorer acts
 * (the pointing the parent workspace row already offers is not repeated here), the two export downloads,
 * and the delete at the end of the list — the one act that cannot be walked back, behind the page's
 * consent. `workspacePath`, the workspace the tree is drawing this run inside, is threaded from the row
 * because the run's own data names its cwd to no one and the record's folder in the runs root is not the
 * folder these acts open. The archive word follows the state, the stop item stands and falls with whether
 * the run is working, and the export item is an anchor — the face's own state moves not. */
export function runMenuItems(rowData, workspacePath) {
  const hidden = state.archived.has(rowData.id);
  const items = [];
  // The rename stands first: the word the run wears is the operator's own to give, and the act that gives
  // it a new word owes the entrance an operator finds by looking — the pen beside its word, and the
  // popover the act stands up on the row's own word when it is chosen.
  items.push({
    label: 'Rename',
    glyph: EDIT_GLYPH,
    claim: `Name the run ${rowData.id} — the word its row wears, asked in the face's own popover`,
    onAct: (event) => renameRunFromMenu(rowData, event),
  });
  // The stop is the one item that follows whether the run works: it names a process to end, and a run
  // that has settled — an ending on the record, or a process the machine calls dead — has no process to
  // end, so the menu does not offer an act it could only refuse. The same reading the spinner wears.
  if (rowWorking(rowData)) {
    items.push({
      label: 'Stop',
      glyph: STOP_GLYPH,
      claim: `End ${rowData.id}'s process — its log keeps what it has, and a word after relaunches it`,
      onAct: () => stopRunAct(rowData.id),
    });
  }
  items.push({
    label: 'Fork',
    glyph: FORK_GLYPH,
    claim: `Branch a new run from ${rowData.id}'s conversation — the whole record is carried and the `
      + 'branch diverges under an objective typed here',
    onAct: () => armFork(rowData.id, ''),
  });
  items.push({
    label: hidden ? 'Un-archive' : 'Archive',
    glyph: ARCHIVE_GLYPH,
    claim: hidden ? `Show ${rowData.id} in the tree again`
      : `Hide ${rowData.id} from the tree — its folder and its log are untouched`,
    onAct: () => archiveRun(rowData.id, hidden),
  });
  items.push({
    label: 'Copy details',
    glyph: COPY_GLYPH,
    claim: `Copy ${rowData.id} and its stamp to the clipboard — the row's own hover, made pasteable`,
    onAct: () => copyDetails(rowData),
  });
  items.push(...folderActItems(workspacePath, false));
  items.push({
    label: 'Export (MD)',
    glyph: DOWNLOAD_GLYPH,
    href: exportHref(rowData.id),
    download: `${rowData.id}.md`,
    claim: `Write ${rowData.id}'s transcript out as a markdown file`,
  });
  items.push({
    label: 'Export (JSON)',
    glyph: DOWNLOAD_GLYPH,
    href: exportHref(rowData.id, 'json'),
    download: `${rowData.id}.json`,
    claim: `Write ${rowData.id}'s record out as json: the log's own lines, one document`,
  });
  items.push({
    label: 'Delete',
    glyph: GONE_GLYPH,
    claim: `Delete ${rowData.id} from disk`,
    danger: true,
    onAct: () => deleteRunAct(rowData.id),
  });
  return items;
}

/** The row's hover, made the clipboard's: the id and the stamp the row's title already says, one
 * string a paste can carry. The clipboard is the browser's own act, and a browser that withholds it
 * is answered the way every refusal is — a sentence in the tree's note, the act undone. */
export function copyDetails(rowData) {
  const details = `${rowData.id} · ${rowData.ts}`;
  navigator.clipboard.writeText(details).catch(() => {
    state.treeNotice = 'the clipboard would not take the details; the browser refused';
    renderTree();
  });
}

/** The menu's Rename: the same popover the row's word would stand up, from the entrance the operator can find
 * by looking — the word the popover opens on is the row's, and the anchor is the row's own word, so the
 * popover stands where the word stands and holds exactly what Enter would commit. The click that stands it
 * is the toggle's own, the way the word's own click was: it stops before the document's "anywhere else"
 * rule reads it, or that rule — the one that takes a popover away on a click outside it — takes the
 * popover this click just stood, in the same event. */
export function renameRunFromMenu(rowData, event) {
  if (event && typeof event.stopPropagation === 'function') event.stopPropagation();
  const row = document.querySelector(`.sahw-row[data-run="${CSS.escape(rowData.id)}"]`);
  const anchor = (row && row.querySelector('.sahw-row__label')) || row;
  if (anchor) toggleNamePop(anchor, rowData);
}


export function workspaceRow(workspace, runs, open) {
  const row = el('button', 'sahw-row');
  row.type = 'button';
  row.title = workspace.path;
  row.setAttribute('aria-expanded', String(open));
  row.appendChild(el('span', 'sahw-row__label',
    `${open ? UNFOLD_GLYPH : FOLD_GLYPH} ${workspaceLabel(workspace.path)}`));
  row.appendChild(el('span', 'sahw-row__count', String(runs.length)));
  // The parent wears the mark while any of its runs works: a closed workspace is otherwise silent,
  // and a silence the machine would correct is not one the row owes the operator.
  if (runs.some(rowWorking)) row.appendChild(workingMark());
  row.addEventListener('click', () => {
    // The shelf's rows are not the expansion's: showing an archived run is not opening its workspace.
    if (state.showArchived) return;
    // The row is the toggle it always was: the same word its two buttons speak, aimed at wherever the row
    // stands now, so the click and the buttons can never hold the set at two different places.
    if (setExpanded(workspace.path, !state.expanded.has(workspace.path))) renderTree();
  });
  const line = el('div', 'sahw-line');
  line.appendChild(row);
  line.appendChild(action(BROWSE_GLYPH, `Point the composer at ${workspace.path}`,
    () => pointComposer(workspace.path)));
  line.appendChild(rowMenu(`Archive or delete the runs of ${workspace.path}`, workspace.path,
    () => workspaceMenuItems(workspace)));
  return line;
}

/** Put one workspace's runs in sight, or out of it — the row's click, the head's two batch marks and the
 * head's menu are all the same word to the one set the face remembers. Answers whether the set moved, so an
 * act that asked for the state the row already stands in redraws nothing. */
export function setExpanded(path, open) {
  if (state.expanded.has(path) === open) return false;
  if (open) state.expanded.add(path);
  else state.expanded.delete(path);
  store.write('expanded', Array.from(state.expanded));
  return true;
}

/** The fact that this run was carried in from another one, as the row wears it: a glyph where the tree is
 * tight and a badge where the header has room. The words are the same ones the log's own `fork` record
 * states — the run it came from and the step its prefix ended at — read here and never computed: a lineage
 * is a later plan, and this is the single fork.
 *
 * With no `fork` key on the row there is nothing to wear, which is the ordinary case: a run that began as
 * its own run says so by wearing nothing. */
export function forkWords(rowData) {
  const fork = rowData.fork;
  if (!fork || !fork.source) return null;
  return {
    badge: `↳ ${fork.source}${fork.step ? ` @ ${fork.step}` : ''}`,
    hover: fork.step ? `forked from ${fork.source} @ step ${fork.step}` : `forked from ${fork.source}`,
  };
}

/** The endpoint a run's row stands: the address the record says its words went to, named beside the model
 * that speaks through it because an address alone names no conversation. The tree carries the address only
 * when a switch moved the run to a different box — the record states one in a `/model` notice and nowhere
 * else — so the hover of a run that never moved keeps exactly the two words plan 06 put there. */
export function endpointWords(rowData) {
  if (!rowData.endpoint) return '';
  return rowData.model ? `${rowData.model} @ ${rowData.endpoint}` : String(rowData.endpoint);
}

/** Why a row the machine's own number answers live for still stands dead, in the hover the row's other
 * facts are read from. The server hands the number under `reborn` on exactly those rows — the orphan whose
 * stamped number has been given to another process while its log wrote nothing — and the row's word stays
 * `dead`, so nothing about the row's mark or the composer's face moves. What the hover adds is the reason,
 * which is the one thing a reader cannot get from `dead` alone: the process behind this run is gone, and
 * whatever answers under its number now is not this run. */
export function rebirthWords(rowData) {
  if (!rowData.reborn || rowData.live !== 'dead') return '';
  return `number ${rowData.reborn} answers live — another process wears it, not this run`;
}

export function runRow(rowData, workspacePath) {
  const row = el('button', 'sahw-row sahw-row--run');
  row.type = 'button';
  row.setAttribute('data-run', rowData.id);
  if (state.run && state.run.id === rowData.id) row.classList.add('sahw-row--active');
  // The endpoint beside the id and the stamp: which box a word went to is the fact a run's row can carry and
  // the row's hover is for, and it is the record's newest word on it — so a run that was switched mid-session
  // reads, at a hover, as the run it became. And where the machine's own number answers live under a row that
  // stands dead, the reason rides the same hover: the row's word is unchanged, and the hover is where a row
  // explains itself.
  row.title = [rowData.id, rowData.ts, endpointWords(rowData), rebirthWords(rowData)]
    .filter(Boolean).join(' · ');
  // The row's word is what the row says: a click on it opens the run, the way a click anywhere on the row
  // does. The rename the word owes stands in the row's menu, where the acts an operator looks for stand —
  // the word itself is the selection, and a selection that doubles as an act is a click the operator
  // meant to open a run with.
  const label = el('span', 'sahw-row__label sahw-row__label--run', runName(rowData));
  row.appendChild(label);
  // The at-a-glance mark of a carried conversation: a glyph, because the sidebar is tight, with the
  // source and the step one hover away — the same division the header's badge and its title keep.
  const carried = forkWords(rowData);
  if (carried) {
    const glyph = el('span', 'sahw-fork', FORK_GLYPH);
    glyph.title = carried.hover;
    row.appendChild(glyph);
  }
  const mark = stateMark(rowData.status, rowData.live);
  if (mark) row.appendChild(mark);
  row.addEventListener('click', () => openRun(rowData));
  const line = el('div', 'sahw-line');
  line.appendChild(row);
  line.appendChild(rowMenu(`Archive, delete, or export run ${rowData.id}`, rowData.id,
    () => runMenuItems(rowData, workspacePath)));
  return line;
}

/** Put a run out of sight, or bring it back. The run's folder, its log and every byte of its record are
 * the runs root's and this function does not reach them; what it changes is which rows the tree shows.
 * `hidden` is the state it is read from — a hidden row is offered the way back — which is why the word the
 * menu wears is chosen where the state is, and the act is one function for both directions. */
export function archiveRun(runId, hidden) {
  archiveRuns([runId], hidden);
}

/** The same verdict, batched: this is what a workspace's Archive all and Un-archive all are. */
export function archiveRuns(runIds, hidden) {
  for (const runId of runIds) {
    if (hidden) state.archived.delete(runId);
    else state.archived.add(runId);
  }
  if (!state.archived.size) state.showArchived = false;
  store.write('archived', Array.from(state.archived));
  renderTree();
}

export function renderBrowser() {
  // The path line is the browser's own address, and while it is the address the folder list answers
  // for, it is also the directory a new run would start in. It is a field, so it is written from the
  // listing rather than from the hand that typed it: what the server answered is what the line shows, and
  // on a refusal the answer it was given is the words that were asked for — which is why a typed path
  // stays in the line while the list below it shows why they were refused, there to be fixed and Entered
  // again. With no listing at all the line is empty and wears its placeholder.
  const path = state.listing ? state.listing.path : '';
  nodes.browserPath.value = path;
  // The toolbar acts on the directory the pane is standing on, so the directory is in the claim, and the
  // sentence the pane owes the operator — a window the machine refused — is read at the pane's head.
  const here = path || 'the directory';
  nameButton(nodes.openTerminal, `Open a terminal in ${here}`);
  nameButton(nodes.openExplorer, `Open the file explorer on ${here}`);
  nameButton(nodes.paneRefresh, `List ${here} again`);
  nameButton(nodes.paneMkdir, `Make a folder in ${here}`);
  nameButton(nodes.paneUpload, `Upload files into ${here}`);
  nodes.browserNote.textContent = state.paneNotice;
  nodes.browser.replaceChildren();
  if (state.listing && state.listing.error) {
    nodes.browser.appendChild(el('div', 'sahw-marker', state.listing.error));
    return;
  }
  if (!state.listing) return;
  // The filter is a hand over the rows already drawn, so it never asks the machine again: the words narrow
  // the listing to the entries whose names hold them, and the line back to nothing restores every one of
  // them. The parent row is not an entry of the folder and stands outside the narrowing — climbing out is
  // never what a word typed into a filter meant.
  const text = state.listingFilter.trim().toLowerCase();
  if (!text) {
    const up = parentOf(state.listing.path);
    if (up) nodes.browser.appendChild(directoryRow(up, '..'));
  }
  for (const entry of state.listing.entries) {
    if (text && !entry.name.toLowerCase().includes(text)) continue;
    // Folders and files are one list in one order — the server's, dirs first — and they differ by what a
    // click on the row is: a folder is walked into, a file is opened in the preview beside it.
    const child = childOf(state.listing.path, entry.name);
    nodes.browser.appendChild(entry.dir ? directoryRow(child, entry.name, entry.name)
      : fileRow(child, entry.name));
  }
  // Words that nothing answers are said, once: an empty listing because of the operator's own filter is
  // read as an empty folder otherwise, and the two deserve different sentences.
  if (text && !nodes.browser.children.length) {
    nodes.browser.appendChild(el('div', 'sahw-marker', `nothing here is named ${state.listingFilter}`));
  }
}

/** One folder's row: the click walks the pane into it, and the `⋮` holds the four acts the folder itself
 * is owed. The parent row is the one row that names no entry of the folder and so owns no acts of its own
 * — its name is two dots, and an act aimed at `..` is an act aimed at whatever folder the pane left. */
export function directoryRow(path, label, name = '') {
  const row = el('button', 'sahw-row');
  row.type = 'button';
  row.title = path;
  row.appendChild(el('span', 'sahw-row__mark', NEW_FOLDER_GLYPH));
  row.appendChild(el('span', 'sahw-row__label', label));
  row.addEventListener('click', () => browse(path));
  const line = el('div', 'sahw-line');
  line.appendChild(row);
  if (name) line.appendChild(rowMenu(`Acts for ${name}`, path, () => paneFolderItems(path, name)));
  return line;
}

/** One file's row, wearing the mark that says it is a file and no more mark than that. The click opens it
 * in the preview — the same act a chip's click is, and the same refusal for the files this pane cannot
 * show — and the `⋮` holds the four things an operator does with a file they have found. */
export function fileRow(path, name) {
  const row = el('button', 'sahw-row sahw-row--file');
  row.type = 'button';
  row.title = path;
  row.appendChild(el('span', 'sahw-row__mark', ROW_FILE_GLYPH));
  row.appendChild(el('span', 'sahw-row__label', name));
  row.addEventListener('click', () => openFile(path));
  const line = el('div', 'sahw-line');
  line.appendChild(row);
  line.appendChild(rowMenu(`Acts for ${name}`, path, () => paneFileItems(path, name)));
  return line;
}

/* --- the pane's filter: a narrowing that is also a way in ----------------------------------------------

   One field, two wants, and the words say which one is meant on every keystroke. While they match rows of
   the listing the pane already holds, the listing narrows to them — the face's own view, asking the machine
   nothing, because the rows are drawn and the operator's next keystroke should cost a re-draw and not a
   round trip. The moment they read as a place instead, `Enter` sends the pane there: the keyboard's version
   of a breadcrumb's click, and the reason the pane's filter and the tree's are not one control over one
   list is that only one of the two lists is a filesystem.

   A word is a place when it carries a drive or a root, when it carries a separator, or when nothing in the
   folder is called that — the third case being the one that makes a mistyped name an address the operator
   meant somewhere else rather than a filter that quietly matched nothing, and it is why the refusal of that
   address is worth reading: the pane says so in its note and stands where it stood.
*/

/** Whether the words in the pane's filter name a place rather than narrow the listing. */
export function readsAsPath(text, entries) {
  if (/^([A-Za-z]:)|[/\\~]/.test(text)) return true;
  return !entries.some((entry) => entry.name.toLowerCase() === text.toLowerCase());
}

/** `Enter` in the filter: the listing when the words are a place, and nothing when they are a narrowing —
 * which is the same division the keystroke makes on the screen, drawn a moment earlier.
 *
 * The refusal of a place that is not a folder is the machine's sentence, and it stands in the pane's note
 * as much as in the listing the failed address left behind: the note is where the pane says its own
 * answers, and the words about a folder that is not one are worth reading before the listing they replaced.
 */
export async function jumpTypedPath() {
  const text = nodes.browserFilter.value.trim();
  if (!text) return;
  if (!readsAsPath(text, state.listing ? state.listing.entries : [])) return;
  await browse(text);
  if (state.listing && state.listing.error) say(state.listing.error, true);
}

/* --- the directory's own three acts ---------------------------------------------------------------

   The pane lists a directory on this machine, and the two windows a person wants from a listing are the
   machine's own: a terminal in it and the file explorer on it. Neither is the page's to draw, so the act
   is the route's — the path is posted and the server hands the folder to the machine — and what the page
   keeps is the sentence the machine answered with, said at the head of the pane the act was asked from.
   **Refresh** is the third act and the only one that stays inside the page: the pane's own listing, asked
   again, which is how a directory the operator changed by hand comes back to the face.

   There is no control here that chooses a directory, and none is coming: the web never hands a page a
   directory's path string, and this one is a path the server spawns runs in. The directory is typed into
   the pane's own line, or it is a `+` from a row or a pane head.
*/

/** List the pane's directory again, as it is now rather than as it was when the pane last asked. */
export function refreshPane() {
  const path = state.spawnDir || (state.listing ? state.listing.path : '');
  if (!path) {
    state.paneNotice = 'nothing to list: the pane is not standing on a directory';
    renderBrowser();
    return;
  }
  browse(path);
}

/** Ask the machine for a window on the pane's directory — a terminal, or the file explorer. */
export async function openPane(kind) {
  const path = state.listing ? state.listing.path : '';
  if (!path) {
    state.paneNotice = 'nothing to open: the pane is not standing on a directory';
    renderBrowser();
    return;
  }
  try {
    const answer = await api.open(kind, path);
    // `{ok: true}` is the window having been asked for; a `false` is this machine's own sentence about
    // why it did not start, and it is the operator's to read.
    state.paneNotice = answer && answer.ok ? '' : ((answer && answer.reason) || 'the window was not opened');
  } catch (error) {
    state.paneNotice = error.message;
  }
  renderBrowser();
}

/* --- the pane's rows, and the acts each one is owed -----------------------------------------------------

   The folder's rows and the file's rows carry the same four-shaped menu a tree row carries, aimed at the
   path the row stands on rather than at a run: the path to the clipboard, the machine's own window, and
   then the two that change what the disk holds. Nothing here is a new act on the machine — the open route's
   kinds, the clipboard act the tree rows already wear, and the four routes the pane owns — and the order is
   the reading's: look, then keep, then change.

   **The refusals are the machine's, in the pane's own note.** The server refuses a folder of that name
   already standing, a folder that is not empty, a workspace the record still counts runs in, and anything
   under the runs root; the page adds nothing to those sentences and subtracts nothing, because the reason a
   folder of runs will not rename is a fact about the record the operator has to read to act on. The one
   refusal the face makes for itself is a name that is not a name (see `nameRefusal`): the page does not ask
   the machine a question it can answer on the spot.
*/

/** A folder row's four items: the two the tree's folder rows already offer, then the two this pane owns.
 * Delete wears the danger mark and stands behind the page's consent, naming the exact path, as the tree's
 * delete does; rename asks the new name in the modal. The list is read as the menu opens, so the path in
 * every claim is the row's own at that moment. */
export function paneFolderItems(path, name) {
  return [
    {
      label: 'Copy path',
      glyph: COPY_GLYPH,
      claim: `Copy ${path} to the clipboard — ready to paste into a word`,
      onAct: () => copyPathAct(path, true),
    },
    {
      label: 'Open in explorer',
      glyph: EXPLORER_GLYPH,
      claim: `Open the file explorer on ${path}`,
      onAct: () => openRowWindow('explorer', path, true),
    },
    {
      label: 'Rename',
      glyph: EDIT_GLYPH,
      claim: `Rename ${name} to a new name in the folder it stands in`,
      onAct: () => renameAct(path, name),
    },
    {
      label: 'Delete',
      glyph: GONE_GLYPH,
      claim: `Delete ${path} from disk — a folder only while it holds nothing`,
      danger: true,
      onAct: () => deletePaneAct(path, 'folder'),
    },
  ];
}

/** A file row's four items. **Open** is the preview's own act on the open route's file kind — the box's
 * default handler takes the file, the same act the preview's own tools wear; **Select in explorer** is that
 * route's select kind, the file's folder standing with the file itself marked; and **Download** is the one
 * item that is an anchor rather than a button, pointed at the raw route with the `download` attribute set
 * to the file's own name — the shape the export items wear, and for the same reason: the browser writes the
 * bytes and this page keeps no part in it. */
export function paneFileItems(path, name) {
  return [
    {
      label: 'Copy path',
      glyph: COPY_GLYPH,
      claim: `Copy ${path} to the clipboard — ready to paste into a word`,
      onAct: () => copyPathAct(path, true),
    },
    {
      label: 'Open',
      glyph: EDIT_GLYPH,
      claim: `Open ${name} in the program this machine owes it`,
      onAct: () => openRowWindow('file', path, true),
    },
    {
      label: 'Select in explorer',
      glyph: SELECT_GLYPH,
      claim: `Stand the file explorer on ${path} with the file itself marked`,
      onAct: () => openRowWindow('select', path, true),
    },
    {
      label: 'Download',
      glyph: DOWNLOAD_GLYPH,
      claim: `Keep ${name} — the file's own bytes, whole`,
      href: rawHref(path),
      download: name,
    },
  ];
}

/** The directory the pane is standing on, or the sentence that says there is none: every act that changes
 * what a folder holds needs the folder, and a pane whose listing was refused is standing nowhere. */
export function paneDirectory() {
  const path = state.listing ? state.listing.path : '';
  if (!path) say('nothing to change: the pane is not standing on a directory', true);
  return path;
}

/** Carry one of the pane's acts through its answer. The mutation routes are the ones that answer a refusal
 * as an error rather than as an act that failed, so the sentence is the throw's and the listing is left
 * exactly as it stood: a refused act changed nothing, and a re-list would be the face pretending it might
 * have. */
export async function runPaneAct(pending, landed) {
  let answer;
  try {
    answer = await pending;
  } catch (error) {
    say(error.message, true);
    return;
  }
  state.paneNotice = '';
  landed(answer);
}

/** The head's New folder: the modal asks the name, and the answer re-lists the folder so the new one stands
 * there, ready to enter. */
export function newFolderAct() {
  const parent = paneDirectory();
  if (!parent) return;
  askName({
    title: 'New folder',
    field: 'Name',
    lines: [`Made in ${parent}`, 'Nothing of that name may stand there already.'],
    confirm: 'Make folder',
  }, (name) => runPaneAct(api.makeFolder(parent, name), () => browse(parent)));
}

/** The row's Rename: the new name, in the same folder and never another one. The name the row wears is
 * typed in ready to be edited, because the ordinary case is the same name with a suffix on it. */
export function renameAct(path, name) {
  askName({
    title: `Rename ${name}`,
    field: 'New name',
    value: name,
    lines: [`The folder or file: ${path}`, 'It keeps the folder it stands in; nothing here moves it.'],
    confirm: 'Rename',
  }, (fresh) => runPaneAct(api.rename(path, fresh), refreshPane));
}

/** The row's Delete: the page's consent first, naming the exact path and what cannot be undone, then the
 * route — and the route's own guard behind that, because consent cannot decide whether the folder holds a
 * run's record or anything else the operator has not looked at. */
export function deletePaneAct(path, kind) {
  askConfirmation({
    title: `Delete this ${kind}`,
    lines: [path,
            kind === 'folder'
              ? 'The folder is removed from disk, and only while it holds nothing.'
              : 'The file is removed from disk.',
            UNDONE],
    confirm: `Delete ${basename(path)}`,
  }, () => runPaneAct(api.drop(path), refreshPane));
}

/** The picker's answer: every file posted whole into the directory the pane stands on, each under its own
 * name. One post per file, in the picker's own order, and every refusal kept — a batch of six where two
 * names were taken is not a success with a footnote, it is two sentences the operator has to read — and the
 * listing is asked again whatever the answers were, because the files that landed are the reason for the
 * look.
 *
 * The input is emptied before anything is sent: a picker still holding last time's files would post them
 * again on the next pick, and a file the operator has already watched arrive posting a 409 under its own
 * name is not information, it is a leak of the page's own state into their act.
 */
export async function uploadPicked() {
  const picked = Array.from(nodes.browserUpload.files || []);
  nodes.browserUpload.value = '';
  if (!picked.length) return;
  const folder = paneDirectory();
  if (!folder) return;
  const refused = [];
  for (const file of picked) {
    try {
      await api.upload(folder, file);
    } catch (error) {
      refused.push(`${file.name}: ${error.message}`);
    }
  }
  browse(folder).then(() => {
    if (refused.length) say(refused.join('  ·  '), true);
  });
}

/** Show one file the run touched. A file the server refuses — binary, gone, a folder — is shown as
 * the sentence it gave, because the operator's next move is a different file, not a different page.
 *
 * Asking for a file is the preview being wanted, so the column unfolds to show it. The width it opens
 * at is the one the operator left it at, which is the whole point of the pane remembering. */
export async function openFile(path) {
  // The head's note belongs to the file it was said about: an editor the machine refused for one file
  // says nothing about the next, so the sentence leaves with the file it stood beside.
  state.fileNotice = '';
  // A picture is not asked of the words route. Its extension says what it is, the frame is pointed at
  // the route that answers those bytes, and a file that is not there wears the same gone-mark a receipt
  // whose file went wears — the pane showing a picture and the transcript showing one are one rule.
  if (pictureKind(path)) {
    state.file = { path, picture: true };
    syncPreviewColumn();
    renderPreview();
    return;
  }
  try {
    state.file = await api.file(path);
  } catch (error) {
    state.file = { path, error: error.message };
  }
  syncPreviewColumn();
  renderPreview();
}

/** The file goes: the pane shows the words that say so, and the column goes with it — line, handle,
 * and the handle's own listeners — because a column that holds nothing holds no line to drag. */
export function closeFile() {
  state.file = null;
  syncPreviewColumn();
  renderPreview();
}

/** The composer's dir becomes this one, the chat stops being the run it was showing and
 * becomes the face a new run starts with, and the composer takes the keyboard.
 *
 * This is what the `+` on a workspace row and the `+` on the browser's head do: point the one control
 * that starts a run at a directory, out in the open the operator can see. The pane says where the next
 * run stands — that is the dir's one word, and it is the pane's — the transcript shows the
 * face a new run starts with rather than the run being watched, and the composer holds the cursor.
 * Nothing is sent and no run is started: the word still has to be typed and sent from the composer
 * itself. */
export function pointComposer(path) {
  if (path) browse(path);
  closeRunView();
  focusComposer();
}

/** The `+` act's second half: the run the chat was showing steps aside, and the chat becomes the face
 * a new run starts with — empty, ready for the word.
 *
 * The run itself is untouched: it keeps its log, its record, and its place in the tree, and a click on
 * the row still opens it. What goes is the view — the steps the pane counted, the stream following the
 * log, the composer's word about the run it was with, and the face's memory of the run it was on. The
 * memory goes with the view on purpose: a reload after a `+` lands where the `+` landed, not back on
 * the run the hand just stepped away from. */
export function closeRunView() {
  if (!state.run) return;
  closeStream();
  state.run = null;
  state.steps = [];
  state.seen = new Set();
  state.notice = '';
  state.steer = '';
  state.follow = '';
  state.edit = null;          // the aim went with the run: the composer is the face a new run starts with
  state.fork = null;          // and so does a fork aimed at one of its steps
  // and a word on the ride goes with the view: the run it promised is closed, and the word stands in
  // the control where the word a new run starts with stands.
  if (state.queued) { if (composer) composer.setDraft(state.queued); state.queued = null; lockInput(false); }
  state.changes = new Set(); // and so does a change the reader had asked to stand: the ids were this log's
  state.commands = new Set(); // and so does a command the reader had asked to stand
  resetDials();                          // the dials are the run's, and this page is standing over none
  paintDials();
  store.write('opened', '');
  renderHeader();
  renderChat();
  renderComposer();
}
