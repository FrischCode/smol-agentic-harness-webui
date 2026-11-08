/* web/assets/js/components.js — the shared small parts: the glyphs the face wears where there is no room for a word,
   the helpers that read a path and a step id, the kinds a record's names claim, the one builder markup
   comes through, and the marks the regions wear.

   They answer the same way wherever they are asked, which is the whole reason they stand together: a fork
   drawn with two different characters is two faces, and a path labelled one way in the tree and another in
   the pane is two paths. `el` is how markup comes into being on this page — every piece is built with it
   and filled with text, so no line of the face's words is ever parsed as markup. The kind claims read a
   *name* and nothing else, and say what the name claims rather than what the bytes are; where a name claims
   nothing the answer is the empty word, not a guess. `parseStep` answers a frame the face can read, or
   null: a frame it cannot read is a frame it does not draw.

   Nothing here reaches the page's record, the server, or another region: a piece is a function of its
   arguments. That is what makes it shareable, and it is why this module imports nothing — with
   `web/assets/js/state.js` it is the bottom of the one way the face's imports run.
   */

/* The glyphs the face wears for the acts and the facts that have no room for words. They are named here,
   once, because the same mark stands in more than one region — the fork's on a tree row, in the header's
   badge, on a message's toolbar, and as the word the transcript's marker row is built from — and a face
   that drew the same relationship with two different characters would be two faces. */
export const FORK_GLYPH = '⑂';
export const CUT_GLYPH = '✎';
export const COPY_GLYPH = '⧉';
// The two marks the folder's own acts wear, read from where the page already wears them: the spawn
// directory's head stands `⌂` for the machine's window on a folder, and a tree row and the pane's head stand
// `+` for the act that points the dir at one.
export const EXPLORER_GLYPH = '⌂';
export const BROWSE_GLYPH = '+';
export const DOWNLOAD_GLYPH = '⬇';
export const SELECT_GLYPH = '⌖'; // the mark that selects the file in the machine's own file browser
// The mark one file wears in the pane's listing: one character for every kind, because the pane places
// runs and does not read files — the mark's whole job is that a row says *file* against the folders it
// stands under, and an icon per extension would be a claim about the kind this page never looks at. The
// sheet the preview draws is `FILE_GLYPH`, a picture of one file; this is the character a row of them wears.
export const ROW_FILE_GLYPH = '🗎';
// The mark a folder's row wears in the pane — and the pane's head wears for the act that stands one up —
// beside the arrow a file comes up the box's own disk with.
export const NEW_FOLDER_GLYPH = '🗀';
export const UPLOAD_GLYPH = '⬆';
export const EDIT_GLYPH = '✎'; // the pencil again: the file's own edit, in the machine's editor not the composer's
export const INFO_GLYPH = 'ℹ'; // the mark that holds a turn's own line: the name, the moment, the numbers
export const VIEW_GLYPH = '→'; // the mark that stands where a result is the one that touched a file
export const REASONING_GLYPH = '∴'; // the mark a word that stands thinking wears, in flight and settled
export const CHANGE_GLYPH = '±'; // the mark that stands where a call carries a change this page can read
export const COMMAND_GLYPH = '$'; // the mark a command line wears when the line shows less than the record holds
// The two states a workspace row stands in, worn as its label's mark and offered as its two buttons: the
// same pair of characters saying the same two things in the row's mark, in its buttons, and on the shelf's
// own entry, because a face that drew opening with two different characters would be two faces.
export const UNFOLD_GLYPH = '▾';
export const FOLD_GLYPH = '▸';
export const ARCHIVE_GLYPH = '▣'; // the mark a run wears when shelved: the closed box it stands behind
export const STOP_GLYPH = '■'; // the mark a working run's process is offered: the square that says the motion ends
export const SEND_GLYPH = '➤'; // the mark the send wears: the word leaves the control and goes out
export const QUEUE_GLYPH = '≣'; // the mark a held word wears: the stack a word stands in until its ride

// --- small facts, computed the same way everywhere -----------------------------------------------

/** One element, with a class and text set apart: the only way anything reaches the document. */
export function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

export function badge(text, flavour) {
  return el('span', `sahw-badge sahw-badge--${flavour}`, text);
}

/** The mark a working thing wears instead of a badge: the spinner, busy-named, because the question
 * it answers — is it working, or has it been working — is a question only an animation can say at a
 * glance. The badge it replaces is a still thing, and a still thing on a moving run is a lie the
 * page would have to correct on every refresh. */
export function workingMark() {
  const mark = el('span', 'sahw-working');
  mark.appendChild(el('div', 'sahw-spinner sahw-spinner--sm'));
  mark.title = 'working — the objective is in flight';
  mark.setAttribute('aria-busy', 'true');
  mark.setAttribute('aria-label', 'working');
  return mark;
}

/** The mark a state wears: the spinner while the run works, and nothing otherwise. A run that is not
 * churning owes the row no word about its state — which one is working is the only question the row
 * answers at a glance, and that is the spinner's. What the run is now (settled on its ending, or stopped
 * short of it) is the composer's to say for the run that is open. */
export function stateMark(status, live) {
  if (status === 'live' && live !== 'dead') return workingMark();
  return null;
}

/** Whether a row of the tree is working: no ending at the log's tail, and the machine has not called
 * the process dead. The record's part and the machine's part are the row's own two keys, and the
 * spinner and the stop are the only two things that read both of them. */
export function rowWorking(row) {
  return row.status === 'live' && row.live !== 'dead';
}

/** The name a path ends with, on either separator: the log holds windows paths, the page is one wide. */
export function basename(path) {
  const parts = String(path).split(/[\\/]/).filter(Boolean);
  return parts.length ? parts[parts.length - 1] : String(path);
}

/** The workspace row's label: the folder a run stood in, not the whole path it stood at. */
export function workspaceLabel(path) {
  return basename(path);
}

/** The run row's label when the log owes the page no word: the id without its `r<date>-` head. Within
 * a workspace the clock and the random tail are what tell two runs apart, and the full id rides in the
 * row's title. A run whose log carries the word its objective was sent with wears that word instead —
 * the id is the machine's name for the run, and the word is the operator's. */
export function shortRunId(id) {
  const parts = String(id).split('-');
  return parts.length > 2 ? parts.slice(1).join('-') : String(id);
}

/** The number a step was logged under, told the way a cut names it: `000005-message` is step 5. The digits
 * alone are what the route is posted with and what a reader is shown — the rest of the id only says what
 * kind of line it was — and a step whose id carries no head of digits is a step this page cannot number,
 * answered with the empty string so the affordance it would hang on and the sentence it would be named in
 * both stand down rather than say `undefined`. */
export function stepDigits(id) {
  const head = /^0*(\d+)-/.exec(typeof id === 'string' ? id : '');
  return head ? head[1] : '';
}

/** The folder holding this one, or '' when there is none — a drive root is where the walk stops,
 * and it is named with its separator: the bare drive letter is not a folder, it is whatever folder
 * the shell happens to stand on. */
export function parentOf(path) {
  const trimmed = String(path).replace(/[\\/]+$/, '');
  const head = trimmed.replace(/[\\/][^\\/]*$/, '');
  if (!head || head === trimmed) return '';
  if (/^[A-Za-z]:$/.test(head)) return head + trimmed.slice(head.length, head.length + 1);
  return head;
}

/** The path of `name` inside `dir`, keeping whichever separator `dir` already used. */
export function childOf(dir, name) {
  const trimmed = String(dir).replace(/[\\/]+$/, '');
  return `${trimmed}${trimmed.includes('\\') ? '\\' : '/'}${name}`;
}

/** The step a frame carried, or null when the line is not a JSON object: a frame the page cannot
 * read is a frame the page does not draw, and the next one is on its way. */
export function parseStep(raw) {
  try {
    const step = JSON.parse(raw);
    return step && typeof step === 'object' ? step : null;
  } catch {
    return null;
  }
}

// --- the face's eyes: the files the record names ------------------------------------------------------

/* Two sentences in the record name a file the face can show, and each is rendered as the file's own kind
   asks: a path whose extension claims a picture is a frame pointed at `/img?path=<the absolute path>`, the
   one route that answers a picture's bytes with the mime its extension claims; any other path is the chip
   the files a turn touched already wear, which opens the preview pane on the file's words — or on the
   reader's honest refusal when the file has none to show.

   A `result` step's `images` field is the model's receipt: the bytes travelled, so the picture shows
   *because the model saw it*. The sentence that says a picture did not travel — `— not attached: …`,
   with no field beside it — is the record saying what the model did not see, and it stays words: the
   face does not dress up what never happened. (The field is the model's receipt and names pictures; the
   operator's word carries its files under `files`, and the two never meet.)

   The other is the operator's line, `attached: <path> — read it`, which the server writes into the word
   for every file it has placed in the run's estate, picture or page of words alike. That line is the
   record's sentence and it stays in the text where it stands — the run was told those words — and what
   stands beside the words is the face's rendering of it, so an attachment is visible the moment it is sent
   and afterwards. The line asks for a read of an address and says nothing about the kind of thing there:
   the destination follows the claim the path itself makes, which is how the same sentence serves a
   sunset and a `notes.md`.

   Both name a file and never the bytes, and a file the record named may be gone by the time the row is
   painted: the portability axiom working as intended. The frame's own failure is what the face answers,
   with the gone-mark — the row's sentence stands untouched and the mark says the one thing the record
   cannot, because the record was true when it was written. A chip's file being gone is the preview's own
   sentence, which is what a chip was always liable to. */
export const PICTURE_KINDS = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'];

/* The extensions this box reads as words, spelled the way the picture kinds are spelled. The list is an
   offer and not a wall: the preview's reader answers any file it can decode and refuses the rest in the
   server's own sentence, so a name in this list is only a promise that a tile will stand and a chip will
   open — and the list is generous for exactly that reason. A file claiming none of these and none of the
   picture kinds is the one the picker passes over, because nothing here would offer to show it. */
export const TEXT_KINDS = ['.txt', '.md', '.py', '.js', '.json', '.toml', '.yml', '.yaml', '.sh', '.bat',
  '.log', '.csv', '.html', '.css', '.xml', '.ini'];

// The server's line, read back rather than re-spelled: anchored at both ends, so a sentence that merely
// mentions an attachment is not one, and the path is whatever lay between the two fixed words.
export const REFERENCE_LINE = /^attached: (.+) — read it$/;

/** The extension a path claims, dot and all, lowercased — '' when the name carries none. */
export function extensionOf(path) {
  const name = basename(path);
  const dot = name.lastIndexOf('.');
  return dot < 0 ? '' : name.slice(dot).toLowerCase();
}

/** The kind `path` claims by its extension, when `kinds` answers that extension, and '' when it claims
 * none — the claim a name makes and nothing else, read one way for a picture's kinds and a text file's.
 * The same claim the routes read, spelled the same way, so the page never asks a route for what it would
 * refuse and never paints a frame for a name the route would answer with words. */
export function claimedKind(kinds, path) {
  const extension = extensionOf(path);
  return kinds.includes(extension) ? extension : '';
}

export const pictureKind = (path) => claimedKind(PICTURE_KINDS, path);
export const textKind = (path) => claimedKind(TEXT_KINDS, path);

// The markdown a name claims: the document it is. The code a name claims, by the language the fence
// could name it in the transcript — the selection the page already carries, and no more. The claim
// is read the way the face already reads a name's claim: lowercased, and a name's claim is a name's
// claim.
export const MARKDOWN_KINDS = ['.md', '.markdown'];
export const CODE_KINDS = { '.py': 'python', '.js': 'javascript', '.mjs': 'javascript', '.cjs': 'javascript',
  '.ts': 'typescript', '.tsx': 'typescript', '.sh': 'bash', '.bash': 'bash', '.json': 'json',
  '.json5': 'json5', '.rs': 'rust', '.c': 'c', '.h': 'c', '.cpp': 'cpp', '.cc': 'cpp', '.hpp': 'cpp',
  '.cs': 'csharp', '.go': 'go', '.java': 'java', '.rb': 'ruby', '.lua': 'lua', '.sql': 'sql',
  '.graphql': 'graphql', '.gql': 'graphql', '.yaml': 'yaml', '.yml': 'yaml', '.toml': 'toml',
  '.ini': 'ini', '.cfg': 'ini', '.properties': 'properties', '.hcl': 'hcl', '.tf': 'hcl',
  '.ps1': 'powershell', '.bat': 'batch', '.cmd': 'batch', '.diff': 'diff', '.patch': 'diff',
  '.tex': 'latex', '.http': 'http', '.log': 'log', '.csv': 'csv', '.css': 'css', '.html': 'markup',
  '.htm': 'markup', '.xml': 'markup' };
export const NAME_CLAIMS = { makefile: 'makefile', gnumakefile: 'makefile', '.editorconfig': 'editorconfig',
  dockerfile: 'docker' };

/** The language a name claims as code, or '' when it claims none: the claim the extension makes, or
 * the claim the name makes when the name carries no extension the way a name claims one — `Makefile`
 * and its own company by their own name, `.editorconfig` by its own name, and `Dockerfile` and a
 * name that ends in `.dockerfile` by theirs. */
export function claimedLanguage(path) {
  const name = basename(path).toLowerCase();
  if (NAME_CLAIMS[name]) return NAME_CLAIMS[name];
  if (name.endsWith('.dockerfile')) return 'docker';
  return CODE_KINDS[extensionOf(path)] || '';
}

/** Where one picture's bytes are served from. The path is the record's — a receipt's or a reference
 * line's — and it is absolute, which is why it goes into the query whole: the route resolves nothing
 * against a root of its own and refuses a relative name outright. */
export const imagePath = (path) => `/img?path=${encodeURIComponent(path)}`;

/** The paths a message's words name, one per line: the operator's attachments, read out of the record's
 * own sentences. The lines stay in the text — they are what the run was told — and what comes back here
 * is only what the face has to paint beside them. */
export function attachedPaths(text) {
  const paths = [];
  for (const line of String(text || '').split('\n')) {
    const named = REFERENCE_LINE.exec(line);
    if (named && named[1].trim()) paths.push(named[1]);
  }
  return paths;
}

/** The paths one result's receipt names. A result without the field is a result the model answered
 * without seeing anything, and no sentence about a picture changes that. */
export function receiptPaths(result) {
  if (!Array.isArray(result.images)) return [];
  return result.images.filter((one) => typeof one === 'string' && one.trim());
}

/** The face's word for a picture this row named and this box no longer holds. It says only what the
 * record cannot — the file is gone *now* — and the path rides in the hover, for the reader who wants to
 * go looking for it. */
export const GONE_GLYPH = '⊘';
export const GONE_WORDS = `${GONE_GLYPH} the file this row named is gone`;

export function goneMark(path) {
  const mark = el('span', 'sahw-gone', GONE_WORDS);
  mark.title = String(path);
  return mark;
}
