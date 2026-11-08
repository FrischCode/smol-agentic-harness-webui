/* web/assets/js/scroller.js — the pane's own scroller: the follow, the release, and the reader's place.

   The engine is stood at the head of the boot on the surface the markup stands (createMessageScroller on
   the pane's scroller), and watches the surface rather than being told of it: every redraw of the
   transcript is something it hears. The follow keeps the reader at the word the page is saying until the
   reader stands on a row of their own — the release — and the jump brings the reader back when the page
   says so. What the engine keeps is the reader's place, and the keys the viewport owes a reader who
   stands on it.
   */

import { state } from './state.js';
import { frame } from './composer.js';

/* --- the pane's own scroller: the follow, the release, and the reader's place -------------------------

   The transcript is written at the bottom of a scroll surface, and a reader stands somewhere in it. Four
   things are owed to that arrangement, and this section keeps all four:

   * the **follow**: while the pane stands at its end it stays at its end as rows arrive; and while a row
     the markup names an anchor stands in it the pane holds that row in view instead — which is how a short
     turn reaches the bottom of the pane without the pane inventing spare space: the content is grown by
     exactly the room that turn needs, and by nothing else;
   * the **release**: the operator's own hand — a wheel turned up, a pointer or a touch dragged up, an
     arrow, `PageUp`, `Shift+Space` — takes the pane out of the follow, and coming back to the bottom of it
     puts the follow back on its own;
   * the **jump**: the button the markup stands in the pane. `data-active` is the one word this section
     writes on it and the sheet's is the only paint that reads it; the click and the keyboard that work on
     it are this section's, and the scroll they make is the smooth one the operator asked for unless the
     page was told to move without motion;
   * the **place**: a row above the reader that grows does not move what the reader is reading. The pane
     remembers the first row in view and how far below the top it stands, gives the difference back,
     carries that pair in the reading it publishes, and stands the pane at a place it is told — which is
     where a reader who left the pane mid-history comes back to it, the place stood as the reader's own
     hand would have stood it (`scrollToPlace`).

   The surface is the markup's: a root wearing `sahw-message-scroller`, the viewport that scrolls, the
   content the rows stand in, the rows named by `data-sahw-message-id`, an anchor row wearing
   `data-sahw-scroll-anchor`, and the jump wearing `data-sahw-scroll-to`. Three attributes configure the
   engine — `data-sahw-auto-scroll`, `data-sahw-scroll-position`, `data-sahw-scroll-peek` — and this page's
   root wears none of them, so its defaults stand: follow on, start at the end, no peek. Where the pane
   stands is published twice over: `data-scrollable` on the root and the viewport, holding `start` and `end`
   as the two ends it can name and the reader's place as a third word when the reader stands on a row of
   their own — that row and how far below the top it stands, `place:<row>@<offset>` — and a
   `sahw:message-scroll` event carrying the same reading in its `detail`. Both are spoken only when the
   reading is not the one already spoken, and the face reads them: it keeps the place the reading carries
   for the run the pane stands on, and asks it back as `scrollToPlace` when the page stands on that run
   again (the keeping stands in transcript.js).

   Two parts of the shape this came from stand down, named: the test for a subtree a framework holds (this
   page's DOM is held by nothing but this file), and the document-wide watcher that destroyed an instance
   whose root had left the document — `update` makes that same test on every pass it takes, and this page
   has one pane, standing in its own markup, for the life of the tab.
*/

// One engine per surface, so asking twice for the pane's engine is asking for the one that stands.
export const scrollers = new Map();

/** The engine, stood on one surface: `root` the scroller's root, and `options` saying what the markup
 * would have said with its three attributes. It answers with the handle the page holds — `scrollToEnd`,
 * `scrollToStart`, `scrollToMessage`, `scrollToPlace`, the state as the pane reads it, and `destroy`,
 * which takes every attribute, listener and pixel of padding the engine added back off. */
export function createMessageScroller(root, options = {}) {
  if (!root || !root.matches('.sahw-message-scroller') || !root.isConnected) return null;
  if (scrollers.has(root)) return scrollers.get(root);
  // Everything the engine touches is read back through the root: a surface inside another surface belongs
  // to the inner one, and this engine has no business there.
  const owns = (node) => Boolean(node) && node.closest('.sahw-message-scroller') === root;
  const owned = (selector) => Array.from(root.querySelectorAll(selector)).filter(owns);
  const part = (selector) => owned(selector)[0] || null;
  const viewport = part('.sahw-message-scroller__viewport');
  const content = part('.sahw-message-scroller__content');
  if (!viewport || !content || !viewport.contains(content)) return null;

  const autoScroll = options.autoScroll === undefined
    ? root.getAttribute('data-sahw-auto-scroll') !== 'false'
    : Boolean(options.autoScroll);
  let position = options.scrollPosition || root.getAttribute('data-sahw-scroll-position') || 'end';
  if (!['start', 'end', 'last-anchor'].includes(position)) position = 'end';
  let peek = Number(options.scrollPeek === undefined
    ? (root.getAttribute('data-sahw-scroll-peek') || 0)
    : options.scrollPeek);
  if (!Number.isFinite(peek)) peek = 0;
  peek = Math.max(0, peek);

  // How near an end counts as standing at it — and the same leave for the row whose top the pane holds.
  const edge = 8;
  let destroyed = false;
  let initialized = false;
  let frame = 0;
  let following = null;   // 'end', 'anchor', or null while the operator holds the pane
  let liveAnchor = null;
  let extraPadding = 0;
  let rows = [];
  const observedRows = new Set();
  let snapshot = null;    // the row the reader stands on, and how far below the top it stands
  let lastTop = viewport.scrollTop;
  let lastState = '';
  let scrollTarget = null;  // where a smooth scroll is going, while it is still going
  let pointer = null;
  let touchY = null;
  const savedAttributes = [];
  const listeners = [];
  const paddingWas = content.style.getPropertyValue('padding-bottom');
  const paddingPriority = content.style.getPropertyPriority('padding-bottom');
  const basePadding = parseFloat(getComputedStyle(content).paddingBottom) || 0;
  const anchorWas = viewport.style.getPropertyValue('overflow-anchor');
  const anchorPriority = viewport.style.getPropertyPriority('overflow-anchor');
  // The browser's own anchoring would move these same rows for the same reason, badly; the engine keeps
  // the reader's place itself.
  viewport.style.setProperty('overflow-anchor', 'none');

  /** One attribute, written and remembered: what stood before this section wrote it is what `destroy`
   * puts back — and only while nothing else has written it since. */
  function attribute(node, name, value) {
    let saved = savedAttributes.find((one) => one.node === node && one.name === name);
    if (!saved) {
      saved = { node, name, was: node.getAttribute(name), value: null };
      savedAttributes.push(saved);
    }
    saved.value = value;
    if (value === null) { if (node.hasAttribute(name)) node.removeAttribute(name); }
    else if (node.getAttribute(name) !== value) node.setAttribute(name, value);
  }

  /** The same, but only where the markup said nothing of its own: the page's word outranks the default. */
  function unlessSaid(node, name, value) {
    if (!node.hasAttribute(name)) attribute(node, name, value);
  }

  // The pane is a region a reader scrolls, and the log inside it grows at the end: said once here, so a
  // reader with a screen reader is told the same thing the pane's own shape says.
  unlessSaid(viewport, 'tabindex', '0');
  unlessSaid(viewport, 'role', 'region');
  if (!viewport.hasAttribute('aria-labelledby')) unlessSaid(viewport, 'aria-label', 'Messages');
  unlessSaid(content, 'role', 'log');
  unlessSaid(content, 'aria-relevant', 'additions');

  const queryRows = () => Array.from(content.querySelectorAll('[data-sahw-message-id]'));

  /** The rows, and the resize watch kept to exactly them: a row is the layout change this engine answers,
   * so a row that left is unwatched and a row that arrived is watched. */
  function readRows() {
    rows = queryRows();
    if (!resizeObserver) return;
    observedRows.forEach((row) => {
      if (!rows.includes(row)) {
        resizeObserver.unobserve(row);
        observedRows.delete(row);
      }
    });
    rows.forEach((row) => {
      if (!observedRows.has(row)) {
        resizeObserver.observe(row);
        observedRows.add(row);
      }
    });
  }

  const origin = () => viewport.getBoundingClientRect().top + viewport.clientTop;
  const rowTop = (row) => row.getBoundingClientRect().top - origin() + viewport.scrollTop;
  /** An anchor row is one the markup says so, and the word `false` is a row taking the mark back off. */
  const anchored = (row) => row.hasAttribute('data-sahw-scroll-anchor')
    && row.getAttribute('data-sahw-scroll-anchor') !== 'false';
  const maxTop = () => Math.max(0, viewport.scrollHeight - viewport.clientHeight);

  /** Where a reader of the pane stands, in the words the pane publishes. */
  function collectState(items) {
    const top = origin();
    const bottom = top + viewport.clientHeight;
    let current = null;
    const visible = [];
    (items || rows).forEach((row) => {
      const rect = row.getBoundingClientRect();
      if (!row.getClientRects().length || rect.height <= 0) return;
      const id = row.getAttribute('data-sahw-message-id');
      if (rect.bottom > top && rect.top < bottom) visible.push(id);
      if (anchored(row) && rect.top <= top + peek + edge) current = id;
    });
    const atEnd = maxTop() - viewport.scrollTop <= edge;
    // The reader's place, carried by the reading: the row they stand on and how far below the top of the
    // pane it stands — in whole pixels, because it is a word the face keeps between two standings of the
    // page. Nothing stands where the pane stands at its end or holds no row: the end is the default, and
    // a default the face had to stand back is no place to keep.
    const stood = atEnd ? null : firstInView(items);
    return {
      atStart: viewport.scrollTop <= edge,
      atEnd,
      currentAnchorId: current,
      visibleMessageIds: visible,
      place: stood ? { row: stood.row, offset: Math.round(stood.offset) } : null,
    };
  }

  /** The row the reader stands on — the first that shows any of itself — and how far below the top of the
   * pane it stands. That pair is what a row growing above them is measured against, and what the reading
   * carries of them. */
  function firstInView(items) {
    const top = origin();
    const row = (items || rows).find((one) => {
      const rect = one.getBoundingClientRect();
      return one.getClientRects().length && rect.height > 0
        && rect.bottom > top && rect.top < top + viewport.clientHeight;
    });
    return row
      ? { row: row.getAttribute('data-sahw-message-id'), offset: row.getBoundingClientRect().top - top }
      : null;
  }

  /** Remember the row the reader stands on — the first that shows any of itself — and how far below the
   * viewport's top it stands. That pair is what a row growing above them is measured against. */
  function remember() {
    const seen = firstInView();
    snapshot = seen
      ? { id: seen.row, offset: seen.offset, scrollTop: viewport.scrollTop }
      : null;
    lastTop = viewport.scrollTop;
  }

  /** The jump, by either of its two names: wired by `data-sahw-scroll-to`, painted by its own class. */
  const jumps = () => [...new Set([...owned('[data-sahw-scroll-to]'), ...owned('.sahw-message-scroller__button')])];
  const jumpFor = (node) => node.closest('[data-sahw-scroll-to]') || node.closest('.sahw-message-scroller__button');
  /** A jump the markup already made a control needs no role and no place in the tab order. */
  const controlAlready = (node) => Boolean(node.matches('button') || node.matches('a[href]') || node.matches('input'));
  /** The face's own standing down: the attribute a disabled control wears, on it or on anything it stands in. */
  const standsDown = (node) => Boolean(node.closest('[disabled]') || node.closest('[aria-disabled="true"]'));

  /** Publish the reading: the two `data-scrollable` marks and the reader's place beside them, the jump's
   * `data-active` word, and the event. */
  function publish() {
    const state = collectState();
    const scrollable = `${state.atStart ? '' : 'start'}${!state.atStart && !state.atEnd ? ' ' : ''}${state.atEnd ? '' : 'end'}`;
    const words = state.place ? `${scrollable} place:${state.place.row}@${state.place.offset}` : scrollable;
    [root, viewport].forEach((node) => attribute(node, 'data-scrollable', words || null));
    jumps().forEach((button) => {
      const direction = button.getAttribute('data-sahw-scroll-to') === 'start' ? 'start' : 'end';
      if (button.tagName === 'BUTTON') unlessSaid(button, 'type', 'button');
      if (!button.hasAttribute('aria-labelledby')) {
        unlessSaid(button, 'aria-label',
          direction === 'start' ? 'Scroll to first message' : 'Scroll to latest message');
      }
      if (!controlAlready(button)) {
        unlessSaid(button, 'role', 'button');
        unlessSaid(button, 'tabindex', '0');
      }
      attribute(button, 'data-active', String(direction === 'start' ? !state.atStart : !state.atEnd));
    });
    const key = JSON.stringify(state);
    if (key === lastState) return;
    lastState = key;
    root.dispatchEvent(new CustomEvent('sahw:message-scroll', { bubbles: true, detail: state }));
  }

  /** The spare room the content grows by, so an anchored turn can stand at the end of a pane it does not
   * fill. Nothing to add gives the markup's own padding back, exactly as the markup wrote it. */
  function padding(value) {
    value = Math.max(0, Math.ceil(value));
    if (value === extraPadding) return;
    extraPadding = value;
    if (value) content.style.setProperty('padding-bottom', `${basePadding + value}px`, paddingPriority);
    else if (paddingWas) content.style.setProperty('padding-bottom', paddingWas, paddingPriority);
    else content.style.removeProperty('padding-bottom');
  }

  /** Smooth, unless the operator has asked the page for no motion, in which case every scroll is a jump. */
  function motion(behavior) {
    const still = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    return behavior === 'smooth' && !still ? 'smooth' : 'instant';
  }

  function move(top, behavior) {
    const target = Math.max(0, Math.min(maxTop(), top));
    const how = motion(behavior);
    // Only a scroll still on its way is a scroll to wait for: a scroll that went where it was told the
    // instant it was told is already the pane standing there.
    scrollTarget = how === 'smooth' && Math.abs(target - viewport.scrollTop) > 1 ? target : null;
    viewport.scrollTo({ top: target, behavior: how });
    lastTop = viewport.scrollTop;
  }

  /** Stand the pane still, take the follow away, and remember where the reader stands. */
  function release() {
    if (scrollTarget !== null) viewport.scrollTo({ top: viewport.scrollTop, behavior: 'instant' });
    scrollTarget = null;
    following = null;
    remember();
  }

  /** One pass: the rows as they stand, the follow as the operator left it, the padding a short turn is
   * owed, the reader's place given back, and the reading published. */
  function update() {
    frame = 0;
    if (destroyed) return;
    if (!root.isConnected || !owns(viewport) || !owns(content) || !viewport.contains(content)) {
      destroy();
      return;
    }
    const previousRows = rows;
    readRows();
    if (!viewport.clientHeight) { publish(); return; }
    if (!rows.length) attribute(viewport, 'data-pending-scroll', null);
    const previousIds = new Set(previousRows.map((row) => row.getAttribute('data-sahw-message-id')));
    const lastBefore = previousRows.length
      ? previousRows[previousRows.length - 1].getAttribute('data-sahw-message-id')
      : null;
    const lastSeen = rows.findIndex((row) => row.getAttribute('data-sahw-message-id') === lastBefore);
    // A turn the record anchored, arriving after the last row the pane had already seen, is the turn the
    // reader is being walked to — an anchor re-read above the fold is not.
    let newAnchor = null;
    rows.forEach((row, index) => {
      if (anchored(row) && !previousIds.has(row.getAttribute('data-sahw-message-id')) && index > lastSeen) newAnchor = row;
    });
    if (!initialized && rows.length) {
      initialized = true;
      if (position === 'last-anchor') liveAnchor = rows.filter(anchored).pop() || null;
      following = position === 'start' ? null : (liveAnchor ? 'anchor' : 'end');
      if (position === 'start') move(0);
      attribute(viewport, 'data-pending-scroll', null);
    } else if (autoScroll && following && newAnchor) {
      liveAnchor = newAnchor;
      following = 'anchor';
    }
    if (liveAnchor && (!rows.includes(liveAnchor) || !anchored(liveAnchor))) {
      // The row was rebuilt, not removed: the id it wore is the anchor still, wherever it stands now.
      const anchorId = liveAnchor.getAttribute('data-sahw-message-id');
      liveAnchor = rows.find((row) => row.getAttribute('data-sahw-message-id') === anchorId && anchored(row)) || null;
      if (!liveAnchor) {
        padding(0);
        if (following) following = 'end';
      }
    }
    if (liveAnchor) {
      const target = Math.max(0, rowTop(liveAnchor) - Math.min(peek, viewport.clientHeight));
      // Where the content would end with nothing added for the turn: the last thing that takes up room,
      // plus its own margin, the padding this section may add, and the content's own border. Spare space a
      // `min-height` owes is not room a turn can be given, so the tail's own box is what is measured.
      const tail = Array.from(content.children).filter((node) => node.getClientRects().length).pop();
      const box = getComputedStyle(content);
      const naturalBottom = tail
        ? tail.getBoundingClientRect().bottom - origin() + viewport.scrollTop
          + (parseFloat(getComputedStyle(tail).marginBottom) || 0)
          + basePadding + (parseFloat(box.borderBottomWidth) || 0)
        : 0;
      const naturalEnd = naturalBottom - viewport.clientHeight;
      padding(target - naturalEnd);
      if (following === 'anchor') move(Math.max(target, naturalEnd));
    } else if (following === 'end') move(maxTop());
    if (!following && snapshot && scrollTarget === null) {
      // The reader holds the pane: give the row they stand on back the place they left it, counting a
      // scroll event that has been caused but has not arrived yet.
      const stable = rows.find((row) => row.getAttribute('data-sahw-message-id') === snapshot.id);
      if (stable) {
        const offset = snapshot.offset - (viewport.scrollTop - snapshot.scrollTop);
        const preserved = rowTop(stable) - offset;
        if (Math.abs(preserved - viewport.scrollTop) > 0.5) move(preserved);
      }
    }
    if (!autoScroll) following = null;
    remember();
    publish();
  }

  const schedule = () => { if (!destroyed && !frame) frame = requestAnimationFrame(update); };
  function listen(node, type, handler, opts) {
    node.addEventListener(type, handler, opts);
    listeners.push(() => node.removeEventListener(type, handler, opts));
  }
  const usable = () => !destroyed && root.isConnected && root.contains(viewport)
    && viewport.contains(content) && owns(viewport) && owns(content);

  /** The four acts the page can ask the pane for, each of them the act an operator could take by hand. */
  function scrollToEnd(opts = {}) {
    if (!usable()) return false;
    initialized = true;
    liveAnchor = null;
    padding(0);
    following = autoScroll ? 'end' : null;
    move(maxTop(), opts.behavior);
    readRows();
    remember();
    publish();
    return true;
  }

  function scrollToStart(opts = {}) {
    if (!usable()) return false;
    initialized = true;
    release();
    liveAnchor = null;
    padding(0);
    move(0, opts.behavior);
    readRows();
    remember();
    publish();
    return true;
  }

  /** One row, stood where the caller asks within the viewport: at its top, centered, at the bottom, or
   * wherever it already nearly stands. A row the pane does not hold is answered with the fact. */
  function scrollToMessage(id, opts = {}) {
    if (!usable()) return false;
    readRows();
    const row = rows.find((one) => one.getAttribute('data-sahw-message-id') === id);
    if (!row) return false;
    initialized = true;
    release();
    liveAnchor = null;
    padding(0);
    const top = rowTop(row);
    const height = row.getBoundingClientRect().height;
    const block = opts.block || 'start';
    let target = top;
    if (block === 'center') target -= (viewport.clientHeight - height) / 2;
    else if (block === 'end') target -= viewport.clientHeight - height;
    else if (block === 'nearest') {
      const end = top + height;
      if (top >= viewport.scrollTop && end <= viewport.scrollTop + viewport.clientHeight) target = viewport.scrollTop;
      else if (top < viewport.scrollTop && end > viewport.scrollTop + viewport.clientHeight) target = viewport.scrollTop;
      else if ((top < viewport.scrollTop && height > viewport.clientHeight)
        || (end > viewport.scrollTop + viewport.clientHeight && height <= viewport.clientHeight)) target = end - viewport.clientHeight;
    }
    move(target, opts.behavior);
    remember();
    publish();
    return true;
  }

  /** Stand the reader at a place they stood before: the row the pane is to hold, and how far below the
   * top of the pane that row stands. This is the act the reader's own hand would have stood the pane
   * with, so it takes the follow away and the anchor's padding back, and the engine's own accounting
   * keeps the place against whatever grows above it from here on. The move is without motion, because a
   * restore is the page standing back where the reader stood and not the page walking to it, and it is
   * clamped to the pane's own ends. A row the pane does not hold is answered with the fact that it does
   * not, which is what lets the face keep asking until the replay stands the row. */
  function scrollToPlace(place = {}) {
    if (!usable()) return false;
    const row = String(place.row || '');
    const offset = Number(place.offset);
    readRows();
    const stood = rows.find((one) => one.getAttribute('data-sahw-message-id') === row);
    if (!stood) return false;
    initialized = true;
    release();
    liveAnchor = null;
    padding(0);
    // The row's own top is where a scroll of `rowTop` stands it; a row stood *below* the top of the pane
    // by `offset` pixels therefore stands at a scroll of that much less.
    move(rowTop(stood) - (Number.isFinite(offset) ? offset : 0));
    remember();
    publish();
    return true;
  }

  /** Stand the engine down: the listeners, the watches, the padding it grew, the anchoring it turned off,
   * and every attribute it wrote that nothing has changed since. */
  function destroy() {
    if (destroyed) return;
    destroyed = true;
    if (scrollTarget !== null) viewport.scrollTo({ top: viewport.scrollTop, behavior: 'instant' });
    scrollTarget = null;
    if (frame) cancelAnimationFrame(frame);
    if (mutationObserver) mutationObserver.disconnect();
    if (resizeObserver) resizeObserver.disconnect();
    listeners.forEach((stop) => stop());
    padding(0);
    if (anchorWas) viewport.style.setProperty('overflow-anchor', anchorWas, anchorPriority);
    else viewport.style.removeProperty('overflow-anchor');
    savedAttributes.forEach((saved) => {
      if (saved.node.getAttribute(saved.name) !== saved.value) return;
      if (saved.was === null) saved.node.removeAttribute(saved.name);
      else saved.node.setAttribute(saved.name, saved.was);
    });
    rows = [];
    observedRows.clear();
    snapshot = null;
    scrollers.delete(root);
  }

  const resizeObserver = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(schedule);
  const mutationObserver = typeof MutationObserver === 'undefined' ? null : new MutationObserver(() => {
    if (!usable()) destroy(); else schedule();
  });
  const handle = {
    scrollToEnd,
    scrollToStart,
    scrollToMessage,
    scrollToPlace,
    getState: () => collectState(destroyed ? [] : queryRows()),
    destroy,
  };
  scrollers.set(root, handle);

  /** The pane's own report of where it stands: the follow is kept or released here, and the reading is
   * published from here, because a scroll is the one moment all of it is settled by. */
  listen(viewport, 'scroll', () => {
    const top = viewport.scrollTop;
    const commanded = scrollTarget !== null;
    if (scrollTarget !== null && Math.abs(top - scrollTarget) <= 1) scrollTarget = null;
    // A hand that scrolls up releases where it stops above the end. An up-scroll that lands on the end
    // itself is the browser's clamp of the end-stick: the tail shrank under a pane standing at its end,
    // and the clamp is the stick's own doing answering where the end now stands, not a hand taking the
    // pane, so the follow the stick owed is still owed and the pane keeps standing at the end as rows
    // arrive — the one let-go a stick owes is a hand's, and the stick does not take its own pane away.
    else if (scrollTarget === null && top < lastTop - 1 && maxTop() - top > edge) following = null;
    if (!commanded && autoScroll && !following && top > lastTop && maxTop() - top <= edge) {
      liveAnchor = null;
      padding(0);
      following = 'end';
      move(maxTop());
    }
    remember();
    publish();
  }, { passive: true });
  // The hand that takes the pane out of the follow: a wheel up, a touch or a pen dragged up, a mouse
  // pressed on the pane itself. A drag down is the same hand reaching the other way, and releases too.
  listen(viewport, 'wheel', (event) => { if (owns(event.target) && event.deltaY < 0) release(); }, { passive: true });
  listen(viewport, 'touchstart', (event) => {
    if (owns(event.target) && event.touches.length === 1) touchY = event.touches[0].clientY;
  }, { passive: true });
  listen(viewport, 'touchmove', (event) => {
    if (!owns(event.target) || touchY === null || event.touches.length !== 1) return;
    if (event.touches[0].clientY > touchY) release();
    touchY = event.touches[0].clientY;
  }, { passive: true });
  listen(viewport, 'touchend', () => { touchY = null; }, { passive: true });
  listen(viewport, 'touchcancel', () => { touchY = null; }, { passive: true });
  listen(viewport, 'pointerdown', (event) => {
    if (!owns(event.target)) return;
    pointer = { id: event.pointerId, y: event.clientY, type: event.pointerType };
    if (event.target === viewport && event.pointerType === 'mouse') release();
  }, { passive: true });
  listen(viewport, 'pointermove', (event) => {
    if (!pointer || event.pointerId !== pointer.id || !owns(event.target)) return;
    if (pointer.type !== 'mouse' && event.clientY > pointer.y) release();
    pointer.y = event.clientY;
  }, { passive: true });
  listen(root, 'pointerup', () => { pointer = null; }, { passive: true });
  listen(root, 'pointercancel', () => { pointer = null; }, { passive: true });
  // The viewport's own keys. The pane holds no typing surface — the control the word goes out of stands
  // outside it — so a key is the pane's unless a field or a control is holding the keyboard.
  listen(viewport, 'keydown', (event) => {
    if (!owns(event.target) || event.defaultPrevented || holdsKeyboard(event.target)) return;
    if (event.key === 'End') { event.preventDefault(); scrollToEnd(); }
    else if (event.key === 'Home') { event.preventDefault(); scrollToStart(); }
    else if (event.key === 'ArrowUp' || event.key === 'PageUp' || (event.key === ' ' && event.shiftKey)) release();
  });
  // The jump's two hands: the click, and the key a non-control jump is worked with.
  function control(event) {
    const button = jumpFor(event.target);
    if (!button || !owns(button) || event.defaultPrevented || standsDown(button)) return;
    if (event.type === 'keydown'
      && (controlAlready(button) || (event.key !== 'Enter' && event.key !== ' '))) return;
    event.preventDefault();
    const opts = { behavior: 'smooth' };
    if (button.getAttribute('data-sahw-scroll-to') === 'start') scrollToStart(opts);
    else scrollToEnd(opts);
  }
  listen(root, 'click', control);
  listen(root, 'keydown', control);
  // A picture in a row landing changes the row's height after the fact, and so does the machine's own
  // resize; both are the same layout change as far as the pane is concerned.
  listen(content, 'load', schedule, true);
  listen(content, 'error', schedule, true);
  listen(window, 'resize', schedule);
  // A pane that has not been scrolled yet is not yet stood at its end, and a pane that shows itself
  // before it is stood anywhere is a pane that shows the wrong thing for one frame.
  if (position !== 'start') attribute(viewport, 'data-pending-scroll', '');
  if (mutationObserver) {
    mutationObserver.observe(root, {
      childList: true,
      characterData: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['data-sahw-message-id', 'data-sahw-scroll-anchor', 'class', 'style', 'hidden'],
    });
  }
  if (resizeObserver) {
    resizeObserver.observe(viewport);
    resizeObserver.observe(content);
  }
  update();
  return handle;
}

/** Whether the keyboard belongs to the pane: a form field holding it, or a control — a jump, a row's own
 * mark — that a key works on its own. */
export function holdsKeyboard(node) {
  if (node.closest('input') || node.closest('textarea') || node.closest('select')) return true;
  const editable = node.closest('[contenteditable]');
  if (editable && editable.getAttribute('contenteditable') !== 'false') return true;
  return Boolean(node.closest('button') || node.closest('a[href]') || node.closest('[role="button"]'));
}
