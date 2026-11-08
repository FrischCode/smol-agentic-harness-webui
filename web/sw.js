/* SAHW — the app shell's own service worker: the word the page owes the machine that installs it, and
   the floor a face owes itself when the wire goes down.

   The face serves no-cache from disk per request, and this worker keeps that honest from the inside:
   while the wire stands, every load gets the bytes the server answers with (network first), and the
   cache it keeps is a floor, not a source — the last face the wire answered for, standing when the
   wire does not. Four guarantees stand on that one rule:

   **The record is the server's.** Everything under `/api/` — the tree, the dials, the stream, the
   commands — passes straight through, never stored. A cached answer beside the record is a second
   record, and the stream is a line that is not done until the run says it is.

   **An open tab keeps its own worker.** The worker claims no client it did not load: a new worker
   stands for the loads that come after it, and the tab standing keeps the one that loaded it, so the
   face's update act stays a load — a hard reload stands the new bytes the way it always has.

   **The floor is earned, not shipped.** Nothing is precached: the first load the wire answers for is
   the floor the wire goes down behind. A page never stood on this machine owes nothing when the wire
   is down, and says so (a 503 of its own), rather than standing a shell it never had.

   The worker is at the root, so its scope is the whole page. */

const CACHE = 'sahw-shell';

self.addEventListener('install', (event) => {
  // The install owes nothing: there is no shell to stand in advance of the wire, and a worker that
  // installs by doing nothing is a worker that installs by being there.
  event.waitUntil(self.skipWaiting);
});

self.addEventListener('activate', (event) => {
  // A worker that stands is the worker every load from here on stands under; the caches the workers
  // before it kept are floors the face no longer owes.
  event.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names.filter((name) => name !== CACHE).map((name) => caches.delete(name)));
  })());
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  // Only a same-origin GET is this worker's: another origin, or a write of any kind, is the browser's
  // to make, and a worker that answers for a request it did not choose stands between the page and
  // the wire.
  if (request.method !== 'GET') return;
  const origin = self.location.origin;
  if (!request.url.startsWith(origin)) return;
  // The record's own answers are never the floor's: the wire says what the record is, and the floor
  // says nothing beside it.
  if (request.url.startsWith(`${origin}/api/`)) {
    event.respondWith(fetch(request));
    return;
  }
  // The face's own shell: the wire first, the floor second — a load that the wire answers for stands
  // on the wire's words and lays them down for the one it will not, and a load the wire refuses stands
  // on the last one it answered for, or on the worker's own sentence that it never did.
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    try {
      const answer = await fetch(request);
      if (answer.ok) cache.put(request, answer.clone());
      return answer;
    } catch (error) {
      const kept = await cache.match(request);
      if (kept) return kept;
      return new Response('the wire is down and the shell was never stood: ' + error.message,
        { status: 503, statusText: 'Offline', headers: { 'content-type': 'text/plain' } });
    }
  })());
});
