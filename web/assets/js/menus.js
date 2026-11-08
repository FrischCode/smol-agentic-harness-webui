/* web/assets/js/menus.js — the rows' menu, and the layers it and the confirmation float on; the heads'
   filter popovers and their layers; the run row's name popover and its layer.

   One module, because the three surfaces share the one floating-layer discipline: a layer is stood where
   the surface stands, answered by the document's own answers while it stands (a click away, the key that
   closes it), and taken away by the hand that takes the menu away — `closeMenu`, which the entry hands to
   the dialog at the boot, the way the dialog takes every hand it does not stand itself. The module owes
   the entry no hand of its own: it stands its own answers on the document at the boot (wireMenus), before
   any row can ask.
   */

import { nodes, state } from './state.js';
import { api } from './wire.js';
import { el } from './components.js';
import { nameButton, renderTree } from './trace.js';
import { runAct } from './transcript.js';

/* --- the rows' menu, and the layers it and the confirmation float on ---------------------------------

   Each row of the tree ends in a `⋮` that opens the acts owed to it: a workspace's runs can all be put out
   of sight or all taken off disk, and one run can be put out of sight, taken off disk, or written out as a
   markdown file. Added to either list are the three acts of the folder the row stands on, spoken by
   `folderActItems`. The shape is the context menu the face's own sheet carries — a label naming the row, one
   item per act, the
   destructive one marked — and the moment it stands is the page's: a second click on the affordance closes
   it, a click anywhere else closes it, `Esc` closes it and hands the keyboard back to the row that opened
   it, and a rebuild of the tree closes it because the row it hung from may not be there any more. Up and
   down walk the items and the items are ordinary buttons, so Enter is a click and the whole menu is usable
   without a pointer.

   That ownership is also why the layer is hung off the document rather than left beside its row: the tree
   scrolls, and anything inside the scroller is cut by it, so a menu on the last row would arrive in
   halves. The fixed position, the placement under the affordance and the keeping of it on screen are the
   geometry DAUB has no opinion on; the panel, the items and the danger treatment are DAUB's, and the layer
   floats at DAUB's own popover height.

   The items are read when the menu opens, not when the row was rendered, because the words follow the
   state: the archive item says Un-archive of a run that is archived, and the workspace's says Un-archive
   all once every run of it is out of sight.
*/
export const MENU_GLYPH = '⋮';
export const MENU_ID = 'sahw-row-menu';
export const MENU_ITEM = '.sahw-context-menu__item';

// The one menu standing, as {node, anchor}: the affordance it was opened from is what a second click
// closes, and what `Esc` returns the keyboard to.
export let standingMenu = null;

/** The `⋮` at the end of a row, already knowing the items it opens. */
export function rowMenu(claim, label, itemsFor) {
  const button = nameButton(el('button', 'sahw-act', MENU_GLYPH), claim);
  button.type = 'button';
  button.setAttribute('aria-haspopup', 'menu');
  button.setAttribute('aria-expanded', 'false');
  button.addEventListener('click', () => toggleMenu(button, label, itemsFor));
  return button;
}

/** Open this row's menu, or close the one it already opened: the affordance is a toggle. */
export function toggleMenu(anchor, label, itemsFor, shift = 0) {
  const closing = standingMenu && standingMenu.anchor === anchor;
  closeMenu();
  closeNamePop();          // one layer at a time: opening a menu takes the row's name popover away
  if (closing) return;
  const node = el('div', 'sahw-context-menu sahw-menu');
  node.id = MENU_ID;
  node.setAttribute('role', 'menu');
  if (label) node.appendChild(el('div', 'sahw-context-menu__label', label));
  for (const item of itemsFor()) node.appendChild(menuItem(item));
  node.addEventListener('keydown', (event) => walkMenu(node, event));
  document.body.appendChild(node);
  anchor.setAttribute('aria-expanded', 'true');
  anchor.setAttribute('aria-controls', MENU_ID);
  standingMenu = { node, anchor };
  placeMenu(node, anchor, shift);
  const first = node.querySelector(MENU_ITEM);
  if (first) first.focus();
}

/** Take the menu away. The tree rebuilds its rows with `aria-expanded` back at false, so a row that has
 * gone out of the tree takes the attribute with it and this costs nothing. */
export function closeMenu() {
  if (!standingMenu) return;
  const { node, anchor } = standingMenu;
  standingMenu = null;
  node.remove();
  anchor.setAttribute('aria-expanded', 'false');
  anchor.removeAttribute('aria-controls');
}

/* --- the heads' filter popovers, the layers the two marks stand --------------------------------------

   The head owes the filter's mark and its estate, and the mark stands the field: the field lives in a
   popover hung off the page, opened by the hand and closed by the page, the rows' menus' own discipline —
   a second click on the same mark closes it, a click anywhere else closes it, `Esc` closes it and hands
   the keyboard back to the mark — and one popover at a time, opening one taking the other away. The
   popovers do not speak: each holds the text that narrows the rows of its own head, and a closing keeps
   the text it was opened with, because the narrowing is the operator's view over the rows the page
   already drew, not the popover's. While a word stands, the mark wears the filtered state, so a view
   standing behind a closed popover is still visible where it was made.
*/
export let standingFilter = null;

/** The mark's own state: the word standing in the field the mark stands, worn as the mark's underline. */
export function filterMark(anchor, on) {
  anchor.classList.toggle('sahw-act--filtered', Boolean(on));
}

/** Open this mark's popover, or close the one it already opened: the affordance is a toggle. */
export function toggleFilterPop(anchor) {
  const closing = standingFilter && standingFilter.anchor === anchor;
  closeFilterPop();
  closeNamePop();          // one layer at a time: opening a filter takes the row's name popover away
  if (closing) return;
  const node = anchor === nodes.treeFilterToggle ? nodes.treeFilterPop : nodes.browserFilterPop;
  const input = anchor === nodes.treeFilterToggle ? nodes.treeFilter : nodes.browserFilter;
  node.removeAttribute('hidden');
  anchor.setAttribute('aria-expanded', 'true');
  anchor.setAttribute('aria-controls', node.id);
  standingFilter = { node, anchor, input };
  placeMenu(node, anchor);
  input.select();
  input.focus();
}

/** Take the popover away, keeping its text: the narrowing is the operator's view, and the mark's filtered
 * state is where a closed popover says its word still stands. */
export function closeFilterPop() {
  if (!standingFilter) return;
  const { node, anchor } = standingFilter;
  standingFilter = null;
  node.setAttribute('hidden', '');
  anchor.setAttribute('aria-expanded', 'false');
  anchor.removeAttribute('aria-controls');
}

/* --- the run row's name popover, the layer the row's own word stands ------------------------------------

   The reuse the act was asked for, to the letter: the layer the heads' filter popovers stand in, placed by
   the same hand, and going away the same way the rows' menus and those popovers go away — a second click on
   the label it opened from closes it without an act, a click anywhere else cancels it, `Esc` cancels it and
   hands the keyboard back to the word, and one popover at a time: opening this takes the menu and the two
   filters away, and opening any of those takes this one away.

   Unlike a filter this holds nothing between one opening and the next. The field is filled from the row each
   time it stands — the word that stands, empty when nothing does — so what it holds is always exactly the
   word Enter would commit, and Enter is the whole act: the word goes to the route, the answer patches the
   row's `name` in what the page holds, and the tree draws the row under its new word. A cancel spends
   nothing: no request left the page, the row keeps the word it wore, and so does the record on disk.
*/
// The one name popover standing, as {node, anchor, input, runId}: the label it was opened from is what a
// second click closes and what `Esc` returns the keyboard to.
export let standingName = null;

/** Stand the name's popover under the row's own word, prefilled with the word that stands there. */
export function toggleNamePop(anchor, rowData) {
  const closing = standingName && standingName.anchor === anchor;
  closeNamePop();
  if (closing) return;
  // One layer at a time, the menu's and the filters' own rule: what the hand can reach is one thing to
  // answer for, and the row's word is no exception to it.
  closeMenu();
  closeFilterPop();
  const node = el('div', 'sahw-filter-pop sahw-rename-pop');
  const input = el('input', 'sahw-pane__filter sahw-rename__field');
  input.type = 'text';
  input.spellcheck = false;
  input.autocomplete = 'off';
  const claim = `the run's name — Enter confirms, a click away or Esc cancels`;
  input.title = claim;
  input.setAttribute('aria-label', claim);
  // The word that stands now, and nothing else: an un-named run opens on an empty field rather than on the
  // id's tail, which is no word to edit and would commit as one.
  input.value = rowData.name || '';
  input.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter') return;
    event.preventDefault();
    confirmNamePop();
  });
  node.appendChild(input);
  document.body.appendChild(node);
  standingName = { node, anchor, input, runId: rowData.id };
  placeMenu(node, anchor);
  // The word is typed in whole and selected: the ordinary edit is at the end of it, and a hand that means a
  // new word outright should not have to clear the old one first.
  input.focus();
  input.select();
}

/** Take the popover away. Cancelling is all this ever does on its own — the act runs from Enter, and a page
 * that acted on the way out would be an act the operator never meant. */
export function closeNamePop() {
  if (!standingName) return;
  const { node } = standingName;
  standingName = null;
  node.remove();
}

/** Enter: the word goes out, and the row is re-worn from the answer. The popover goes first — the layer and
 * the act it stands for are not the same moment, and a refusal has its own sentence to be read at the head
 * of the tree the word was asked from. */
export function confirmNamePop() {
  if (!standingName) return;
  const { input, runId } = standingName;
  closeNamePop();
  runAct(api.renameRun(runId, input.value), (answer) => patchRowName(runId, answer));
}

/** Wear the answer. The route hands back the name the row now has, read through the one rule the row builder
 * reads, so the page patches its own row and owes the tree no re-list — and holds no word of its own about
 * what a cleared run is called: an answer with nothing in it means the row is worn by nothing but the id's
 * tail, which is the fallback the face already stands. */
export function patchRowName(runId, answer) {
  const named = answer && answer.name ? String(answer.name) : '';
  for (const workspace of state.workspaces) {
    const row = workspace.runs.find((one) => one.id === runId);
    if (!row) continue;
    if (named) row.name = named;
    else delete row.name;
    break;
  }
  renderTree();
}

/** One item: a real button, or — for the export — the anchor the browser downloads from, which carries no
 * act at all beyond closing the menu out of the way. */
export function menuItem(item) {
  const node = el(item.href ? 'a' : 'button', 'sahw-context-menu__item');
  if (item.glyph) {
    // The mark the act wears beside its word: the row's own act, aimed at everything at once, keeps
    // the mark the row wears. The word stands in its own span, so the word alone is what a reader —
    // a hand or a check — asks for the item.
    node.appendChild(el('span', 'sahw-menu-glyph', item.glyph));
    node.appendChild(el('span', 'sahw-menu-label', item.label));
  } else {
    node.textContent = item.label;
  }
  if (item.href) {
    node.setAttribute('href', item.href);
    node.setAttribute('download', item.download || '');
  } else {
    node.type = 'button';
  }
  if (item.claim) node.title = item.claim;
  node.setAttribute('role', 'menuitem');
  node.setAttribute('tabindex', '-1');
  if (item.danger) node.classList.add('sahw-context-menu__item--danger');
  node.addEventListener('click', (event) => {
    closeMenu();
    if (item.onAct) item.onAct(event);
  });
  return node;
}

/** Up and down through a menu's items, from wherever in the menu the keyboard stands. */
export function walkMenu(node, event) {
  const step = event.key === 'ArrowDown' ? 1 : event.key === 'ArrowUp' ? -1 : 0;
  if (!step) return;
  const items = node.querySelectorAll(MENU_ITEM);
  if (!items.length) return;
  event.preventDefault();
  const at = items.indexOf(event.target);
  items[at < 0 ? 0 : (at + step + items.length) % items.length].focus();
}

/** Hang the menu under the affordance it belongs to, and keep the whole of it on the screen. A shift,
 * when the caller owes one, takes the menu's left hand off the anchor's right end before the
 * keep-on-screen math reads it. */
export function placeMenu(node, anchor, shift = 0) {
  const from = anchor.getBoundingClientRect();
  const box = node.getBoundingClientRect();
  node.style.left = `${Math.max(0, Math.min(from.right - box.width - shift, window.innerWidth - box.width))}px`;
  node.style.top = `${Math.max(0, Math.min(from.bottom + 4, window.innerHeight - box.height))}px`;
}

/** The two ways a menu goes away that its own affordance does not cause: a click anywhere else in the
 * document, and `Esc` wherever the keyboard happens to be. */
export function wireMenus() {
  document.addEventListener('click', (event) => {
    if (standingMenu && event.target !== standingMenu.anchor
      && !standingMenu.node.contains(event.target)) closeMenu();
    if (standingFilter && event.target !== standingFilter.anchor
      && !standingFilter.node.contains(event.target)) closeFilterPop();
    // The name's cancel is the same nothing the filters' is: the popover goes, no request was made, and the
    // row keeps the word it wore. Its own label is no "anywhere else" — that click is the toggle's own.
    if (standingName && event.target !== standingName.anchor
      && !standingName.node.contains(event.target)) closeNamePop();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    if (standingMenu) {
      const back = standingMenu.anchor;
      closeMenu();
      back.focus();
    }
    if (standingFilter) {
      const back = standingFilter.anchor;
      closeFilterPop();
      back.focus();
    }
    // `Esc` cancels the name the same way and hands the keyboard back to the word it came from — the cancel
    // the operator asked for, and the one act this key never becomes.
    if (standingName) {
      const back = standingName.anchor;
      closeNamePop();
      back.focus();
    }
  });
}
