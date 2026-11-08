/* web/assets/js/wire.js — the one way the face reaches the server: every route it asks, in one module, readable at
   a glance.

   `request` is the only fetch in the face: the body is read as text and parsed, a body that is not a
   document is no document rather than a crash, and a refusal arrives as a throw carrying the server's own
   sentence — so every caller reads a failed act the way it reads a path that is not there, and none of
   them reads a status code. `api` is the door: one member per route, the path built with the escaping the
   path needs, and nothing else. `rawHref` and `exportHref` are the two routes the *browser* follows —
   bytes written to the operator's own machine with the page keeping no part in them — held as functions
   because an id and a path go on an address the way every other route's do. `fileField` is the shape the
   two routes that take files take them in, and the reason a word with nothing attached sends the body it
   always sent.

   It imports nothing: a door has no opinion about the rooms behind it, and the face has one way out.
   */

// --- the server, four calls ---------------------------------------------------------------------

export async function request(url, options) {
  const response = await fetch(url, options);
  const text = await response.text();
  let payload = null;
  try {
    payload = text ? JSON.parse(text) : null;
  } catch {
    payload = null; // a body that is not JSON is an answer this page cannot read, not a crash
  }
  if (!response.ok) {
    const sentence = payload && typeof payload.error === 'string' ? payload.error : null;
    throw new Error(sentence || `the server answered ${response.status} for ${url}`);
  }
  return payload;
}

/* The files, in the body's shape: `[{name, bytes(base64)}]` — the field the spawn route and the message
   route write into the run's estate and answer with a reference line apiece. A picture and a page of words
   ride the same field, because the write path asks nothing of a file but its name and its bytes; what the
   field is called says what it carries, and `files` is the truth about both. Nothing attached sends no
   field at all, so the body a plain word makes is the body it always made; and the line each file leaves
   in the word is the route's to write, never this page's to spell. */
export const fileField = (files) => (files && files.length ? { files } : {});

export const api = {
  runs: () => request('/api/runs'),
  // What the machine carries and what one run stands on: the registry's profiles with the reference the
  // machine launches as, and the pair of dials a run's own record states. Both are read where the fact
  // lives — the tree's SAH folder for the first, the log for the second — so the face never keeps a model
  // list of its own and never settles a dial on its last click.
  models: () => request('/api/models'),
  dials: (runId) => request(`/api/runs/${encodeURIComponent(runId)}/dials`),
  listing: (path) => request(`/api/fs?path=${encodeURIComponent(path)}`),
  file: (path) => request(`/api/file?path=${encodeURIComponent(path)}`),
  spawn: (cwd, task, think, model, files) => request('/api/runs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(Object.assign({ cwd, task }, think ? { think } : {}, model ? { model } : {},
      fileField(files))),
  }),
  // The word to the run that is open. `cut` is the one field that turns a word into a return: the step's
  // digits as the log wrote them, and the route answers it as a follow whose argv carries --resume <cut>.
  // It rides only when an edit stands, so a body with no edit is the follow's body as it always was.
  // `model` is the picker's stand, and it rides a follow for the reason the spawn's rides a spawn: a run
  // that was switched while it rested has no process left for the switch to have moved, so the dial comes
  // true on the objective after it.
  message: (runId, text, think, model, cut, files) => request(`/api/runs/${encodeURIComponent(runId)}/message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(Object.assign({ text }, think ? { think } : {}, model ? { model } : {},
      cut ? { cut } : {}, fileField(files))),
  }),
  // One of the session's two dial lines, spoken at the run's own console: `/model <id>` or `/think <lvl>`,
  // the line the route hands to `channel` untouched and the console records as its own notice. The route's
  // refusal of a run that is mid-turn is a 409, and the sentence it carries is the one the stood-down dial
  // already wears, so the caller reads it from the throw like every other refusal here.
  command: (runId, line) => request(`/api/runs/${encodeURIComponent(runId)}/command`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ line }),
  }),
  // The three acts of plan 08. Two of them answer 200 whether they happened or were refused, so the
  // caller reads `ok` and the reason from the same shape and never from a status code; `/api/open` is
  // the one whose refusals are errors (the folder named is not a folder), and those arrive as throws.
  deleteRun: (runId) => request(`/api/runs/${encodeURIComponent(runId)}/delete`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}',
  }),
  // The batch delete, in either of its two sizes: named with a workspace it is that workspace's runs, and
  // named with nothing at all it is every workspace's — the one body shape the route tells the two apart by,
  // and the reason the whole-tree act sends `{}` rather than a field holding an empty word.
  deleteAll: (cwd) => request('/api/runs/delete-all', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(cwd ? { cwd } : {}),
  }),
  // The stop: end a working run's process and keep its record. A run that is not working answers the 409
  // that names it (nothing to stop) rather than an act that failed — the same shape the delete acts answer
  // in, so the caller reads the state from the throw and never from a half-done act. The act takes nothing,
  // so the request sends nothing: a body a route does not read is the connection's next request, read wrong.
  stop: (runId) => request(`/api/runs/${encodeURIComponent(runId)}/stop`, { method: 'POST' }),
  // The compact's verbs: the run's conversation summarised at its next turn boundary, and the stop that
  // asks the compaction in flight to stand down before the summary lands. The route carries the verb to
  // the queue and answers which verb was carried; the record stands the flight and its two endings — the
  // summary step, the stopped act — and the mark reads them from the log the page already follows.
  compact: (runId) => request(`/api/runs/${encodeURIComponent(runId)}/compact`, { method: 'POST' }),
  compactStop: (runId) => request(`/api/runs/${encodeURIComponent(runId)}/compact-stop`, { method: 'POST' }),
  // The fork: branch this run's conversation into a new run. The step is the digits of the step the
  // carried prefix ends at, and it rides only when one was named — with none the whole conversation is
  // carried, which is what the row-menu act asks for. The answer is the new run's id, as the spawn's is.
  fork: (runId, task, think, model, step) => request(`/api/runs/${encodeURIComponent(runId)}/fork`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(Object.assign({ task }, think ? { think } : {}, model ? { model } : {},
      step ? { step } : {})),
  }),
  // The name: the word this run is called by, worn by its row and found by the filter. It is the face's own
  // word and lives in the run's folder beside the log it never touches, so the act writes a file and not a
  // line of the record. An empty word clears it — the row falls back to what its own record calls the run —
  // and the answer carries the name the row now wears beside what the act did, which is what the row is
  // patched from without a re-list. A word the file could not hold (a name is one line) is the error every
  // route answers, read from the throw like every other refusal here.
  renameRun: (runId, name) => request(`/api/runs/${encodeURIComponent(runId)}/rename`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  }),
  open: (kind, path) => request('/api/open', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ kind, path }),
  }),
  // The four changes the spawn pane can ask a folder to make, and the one thing it can ask of a file's
  // bytes. These are the routes that write, so their refusals are the errors every other route answers —
  // `{"error": ...}` with the 4xx the path earns — and a caller reads the sentence from the throw, the
  // same way it reads a path that is not there. `mkdir` and `rename` carry a name and nothing else: a name
  // is one name and never a path, which is the shape the route checks before it looks at the disk.
  makeFolder: (path, name) => request('/api/fs/mkdir', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path, name }),
  }),
  rename: (path, name) => request('/api/fs/rename', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path, name }),
  }),
  drop: (path) => request('/api/fs/delete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path }),
  }),
  // The upload is the one call whose body is not a document about the act but the thing itself: the picked
  // file, handed to fetch whole and streamed to the disk by the route in chunks. No content type is named,
  // because the route reads no type — the bytes are the file and the name the query carries is the file's
  // own, the one the picker showed the operator.
  upload: (folder, file) => request(
    `/api/fs/upload?path=${encodeURIComponent(folder)}&name=${encodeURIComponent(file.name)}`,
    { method: 'POST', body: file }),
};

/* The raw route, as the address of a file rather than a call: the bytes the pane cannot show are still
   the operator's to keep, and an anchor pointed here is the browser writing them to the operator's own
   machine — no reader, no state, no notice. The same shape `exportHref` stands for, and the same reason
   for holding it as a function: the path goes on the address the way every other route's path does. */
export const rawHref = (path) => `/api/file/raw?path=${encodeURIComponent(path)}`;

/* The export route, as the address of a file rather than a call: the browser writes what it answers to
   the operator's machine, and the page keeps no part in it — no state, no reader, no notice. Held as a
   function because the id has to be put on the address the same way every other route's id is. */
export const exportHref = (runId, format) => `/api/runs/${encodeURIComponent(runId)}/export${format ? `?format=${format}` : ''}`;
