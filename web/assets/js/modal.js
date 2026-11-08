/* web/assets/js/modal.js — the page's one confirmation, and the name it also asks for.

   The dialog stands in the document once and is filled for each act: asked twice, the second ask replaces
   the first rather than stacking a second consent on top of it. It has two shapes, and they are the only
   two the face asks in — a consent, which answers with yes, and a name, which answers with the word. The
   name's rule is the face's copy of the machine's, refused where it is typed with the dialog still open on
   the word, because the face does not spend a request to be told what its own field can see; the route
   refuses the same list, in the same words, for every caller that is not this page. Closing is never a
   confirmation: the act runs from the confirm button and from nowhere else.

   Two acts the dialog owes and cannot do itself — saying a sentence at the head of the pane the act was
   asked from, and taking the standing layer away before the dialog stands — are the panes' act and the
   layer's own, so the entry hands them to `wireModal` at boot rather than the dialog reaching up for them:
   a module that imported the page would be a module the page could not read without. What it does import is
   the shared components it builds its markup from — `web/assets/js/components.js`, a foundation, which is as far up as a
   region reaches and the way every region will.
   */
import { el } from './components.js';

/* --- the page's confirmation, and the name it also asks for -------------------------------------------

   Delete is the one act this page cannot walk back, so it is the one act the page asks about. The dialog
   is the browser's own — `showModal` for the focus, the top layer, and the Escape that cancels it, and the
   face's own sheet for the dimming behind it — and what the page owns is the sentence in it: the act named
   exactly (the run and the workspace it stands in, or the count of the runs about to go) and the two facts
   an operator has to have read before meaning it, that the folders come off the disk and that nothing
   brings them back. Confirming fires the route; cancelling fires nothing, and so does the browser's own
   Escape.

   The same dialog stands a second shape: the one field a new folder's name or a rename's goes into, with
   the same two buttons and the same cancel. It is the confirmation machinery grown an input line and
   nothing else — a second dialog would be a second thing to get right about focus, the dimming, and the
   Escape — and the difference in what it answers is only that an act with a name in it can be refused
   before it is asked, which is what `nameRefusal` is for.

   This is consent and nothing else. The server's liveness guard stands behind it whatever the answer is: a
   modal confirmed over a run whose process is still writing its log is refused there, and the refusal's
   words are said in the tree's head.
*/
export const OFF_DISK = 'The run folders are removed from disk, with their logs and everything beside them.';
export const UNDONE = 'This cannot be undone.';

// The one dialog, standing in the document and filled for each act: asked twice, the second ask replaces
// the first rather than stacking a second consent on top of the first. `field` and `fieldLabel` stand the
// second shape the page asks in — a name, typed — and `asked` is which of the two the dialog is standing
// as: a consent answers with yes, an ask answers with the word.
export const confirmation = { dialog: null, title: null, body: null, confirm: null, onConfirm: null,
                              ask: null, field: null, fieldLabel: null, asked: false };

// The dialog's two outside hands: saying a sentence at the head of the pane the act was asked from, and
// taking the standing layer away before the dialog stands. Both are the panes' act and the layer's own, so
// the entry hands them to `wireModal` when it stands the dialog rather than the dialog reaching up for them
// — a module that imports the page would be a module the page cannot read without. The stubs are what it is
// left with before that wiring: a consent that says nothing when it refuses, and a layer nobody asked it to
// close. The names are the dialog's own; `wireModal` fills them from the page's.
let sayRefusal = () => {};
let closeStanding = () => {};

/** Stand the dialog's two outside hands from the entry that owns them — once, at the boot, before any act
 * can ask. `say(sentence, atPane)` is the face's own word for a sentence at a pane's head, and `closeMenu()`
 * for taking the row's menu away. */
export function wireModal(hands) {
  sayRefusal = hands.say;
  closeStanding = hands.closeMenu;
}

export function buildConfirmation() {
  const dialog = el('dialog', 'sahw-modal');
  const head = el('div', 'sahw-modal__header');
  const title = el('span', 'sahw-modal__title');
  const body = el('div', 'sahw-modal__body');
  // The name line, and it is the face's own field rather than the browser's prompt: the same refusal, the
  // same sheet, the same focus the dialog already holds, and — what a `prompt` could never do — the
  // sentence standing in the pane's note beside the field it belongs to. It is absent unless an act asked
  // a name, so a consent stays exactly the dialog it was.
  const ask = el('label', 'sahw-modal__ask');
  const fieldLabel = el('span', 'sahw-modal__ask-label');
  const field = el('input', 'sahw-modal__input');
  field.type = 'text';
  field.spellcheck = false;
  field.autocomplete = 'off';
  ask.appendChild(fieldLabel);
  ask.appendChild(field);
  const footer = el('div', 'sahw-modal__footer');
  const cancel = el('button', 'sahw-btn sahw-btn--secondary', 'Cancel');
  cancel.type = 'button';
  const confirm = el('button', 'sahw-btn sahw-btn--primary');
  confirm.type = 'button';
  head.appendChild(title);
  footer.appendChild(cancel);
  footer.appendChild(confirm);
  dialog.appendChild(head);
  dialog.appendChild(body);
  dialog.appendChild(ask);
  dialog.appendChild(footer);
  cancel.addEventListener('click', closeConfirmation);
  confirm.addEventListener('click', () => {
    const act = confirmation.onConfirm;
    const named = confirmation.asked;
    // The field is read only by an ask that has one standing: a consent has no word in it, and a page that
    // reached past the shape it is standing in would be reading markup that is not part of the ask.
    const word = named ? String(field.value || '') : '';
    // An ask refuses its own empty and impossible name here, with the dialog still open on the word that
    // was typed: the face does not ask the machine a question it can answer itself, and a name that is a
    // path, a dot, or a device is not worth a round trip to be told so.
    if (named) {
      const refusal = nameRefusal(word);
      if (refusal) {
        sayRefusal(refusal, true);
        return;
      }
    }
    closeConfirmation();
    if (act) act(named ? word.trim() : undefined);
  });
  // `Enter` in the field is the confirm button, which is the only reason the dialog has an `ask` shape at
  // all: the hand that typed the name is the hand that means it.
  field.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter') return;
    event.preventDefault();
    confirm.click();
  });
  // The browser's own cancel — Escape, or whatever else ends the dialog — lands here with nothing
  // captured: closing is not a confirmation, and the act only ever runs from the confirm button.
  dialog.addEventListener('close', () => { confirmation.onConfirm = null; });
  document.body.appendChild(dialog);
  Object.assign(confirmation, { dialog, title, body, confirm, ask, field, fieldLabel });
}

/** Ask the operator's consent, in the act's own words: the dialog with no field, which is the shape a
 * delete stands in. The `onConfirm` takes nothing, because the act it runs was already named in full. */
export function askConfirmation(ask, onConfirm) {
  openConfirmation(ask, false);
  confirmation.onConfirm = onConfirm;
}

/** Ask the operator's name, and run `onName` on the word they gave. The name is the act's whole content,
 * so nothing can be asked of the machine before it exists — and the dialog stays open on a name that is
 * not one, its refusal said in the pane's note, until the word is a name or the hand cancels. */
export function askName(ask, onName) {
  openConfirmation(ask, true);
  confirmation.field.value = ask.value || '';
  confirmation.onConfirm = onName;
  confirmation.field.focus();
  // The name the row wore is typed in whole, and selected: the ordinary edit is to the end of it, and a
  // hand that meant a new name outright should not have to clear the old one first.
  confirmation.field.select();
}

/** Stand the dialog, in whichever of its two shapes is being asked: the words, the button's word, and
 * whether the field is in it. */
export function openConfirmation(ask, named) {
  closeStanding();
  if (confirmation.dialog.open) confirmation.dialog.close();
  confirmation.asked = named;
  confirmation.ask.hidden = !named;
  confirmation.fieldLabel.textContent = ask.field || '';
  confirmation.title.textContent = ask.title;
  confirmation.body.replaceChildren(...ask.lines.map((line) => el('p', 'sahw-modal__line', line)));
  confirmation.confirm.textContent = ask.confirm;
  // The consent the page owes is the delete's, and the button that spends it wears the error color the
  // act's own menu item wears: the name shape's confirm is the one button that is not a delete, and it
  // keeps the page's own solid.
  confirmation.confirm.classList.toggle('sahw-btn--primary--danger', !named);
  confirmation.dialog.showModal();
}

export function closeConfirmation() {
  confirmation.dialog.close();
}

/* The name's own rule, and the face's copy of the machine's: an empty word, a word that is `.` or `..`, a
   word holding a separator or a character this box's file systems will not take, a device name the box
   reserves, and a space or a dot at either end are refused where they are typed. The route refuses the same
   list, in the same words, because the face is not the only caller the guard exists for — but a page that
   asked anyway would be a page that spent a request to be told what it could have seen in its own field,
   so the sentence is kept short enough to read in the pane's note and ended with the rule itself.
*/
export const NAME_BAD_CHARS = '/\\:*?"<>|';
export const NAME_RESERVED = /^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\.|$)/i;
export const NAME_RULE = 'a name is one bare name: no separators, not "." or "..", no character Windows will '
  + 'not take, and no device name it reserves';

/** Why this word is not a name, or the empty string for a word that is. */
export function nameRefusal(value) {
  const name = String(value || '');
  const said = name.trim();
  if (!said) return `a name is required: ${NAME_RULE}`;
  if (name !== said) return `a name does not begin or end with a space: ${NAME_RULE}`;
  if (name === '.' || name === '..') return `"${name}" is where a folder already stands: ${NAME_RULE}`;
  for (const char of name) {
    if (NAME_BAD_CHARS.includes(char) || char.charCodeAt(0) < 32) {
      return `"${name}" is not a name: ${NAME_RULE}`;
    }
  }
  if (/[. ]$/.test(name)) return `"${name}" is not a name: ${NAME_RULE}`;
  if (NAME_RESERVED.test(name)) return `"${name}" is a device this box reserves: ${NAME_RULE}`;
  return '';
}
