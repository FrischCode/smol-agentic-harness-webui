/* web/assets/js/reading.js — the reading the word stands in: the parser stands the tokens, and the hands
   stand them.

   A word of the record stands in its reading: the tokens the parser stands from the word — the prose and
   its links, the code and its fences — and the face's own hands that stand them: the path that rides a
   link the record holds, the change an edit made and the command a line withholds, stood where the word
   stands for them. The reading stands no fact of its own: it stands the tokens the word holds, and
   nothing else.
   */

import { state } from './state.js';
import { COPY_GLYPH, el, attachedPaths } from './components.js';
import { action, inflightResult, standingBoxes } from './trace.js';
import {
  TOUCHES, argumentPath, argumentSummary, changeBox, changeMark, commandBox, commandMark,
  editChange, fenceLang, filesRow, flashMark, heldCommand, resultBlock
} from './transcript.js';
import { clockSpan, openFile } from './tree.js';
import { runWorks } from './composer.js';

/* --- The reading the word stands in: the parser stands the tokens, and the face's own hands stand them --

   The parser never writes a byte of markup — the token in, and the words it owes — so the face's own
   hands are the only hands that write the word, and a tag the word's words happen to spell stands as
   the words it is. The renderer mirrors the parser's committed tokens one for one: what the parser
   has not yet committed — a place that may be a place, an item that may be a task — has not yet
   reached the face, and a word that has not yet committed stands as the words it is so far, the way
   the stream owes it. A fence that opens stands as the block the face already stands, the block that
   grows; a fence the word dies in holds open to the end of the word, because the face's own hands
   never close what the parser has not closed, and the render that re-asks the reading is the render
   that stands it. The ground the document stands on is the ground the face already stands on: the
   theme's own prose sheet, and no ground of its own. */

// The schemes the face stands as a link: a place over the wire, and nothing else the face will stand
// as a scheme. A place it will not stand — and a place the word names with no place at all — is not a
// link at all: it stands as the words it is.
export const LINKED_SCHEMES = ['http', 'https'];

export function linkScheme(href) {
  const match = /^\s*([a-zA-Z][a-zA-Z0-9+.-]*):/.exec(String(href || ''));
  return match ? match[1].toLowerCase() : '';
}

/** The directory a path stands in, the record's own spelling: the directory a schemeless link beside
 * the file resolves against. */
export function directoryOf(path) {
  const name = String(path || '');
  const cut = Math.max(name.lastIndexOf('\\'), name.lastIndexOf('/'));
  return cut > 0 ? name.slice(0, cut) : '';
}

/** The place a schemeless link names, beside the file it stands with: an absolute place stands as it
 * stands, and a relative place stands in the directory the file stands in, the record's own
 * separator, because the route resolves nothing of its own and answers the place as it stands. */
export function besideFile(fileDir, place) {
  const name = String(place || '').trim();
  if (!name) return '';
  if (/^[a-zA-Z]:[\\/]/.test(name) || /^[\\/]/.test(name)) return name;
  if (!fileDir) return name.replace(/\//g, '\\');
  return fileDir.replace(/[\\/]+$/, '') + '\\' + name.replace(/\//g, '\\');
}

/** The face's own hands that stand the parser's tokens: the token in, the face's elements out. `root`
 * is the ground the word stands on — the bubble's content, or the document the pane stands — and
 * `context` tells the hands where the word stands: the transcript, where a place with no scheme
 * stands as words, or the pane beside a file, where the place resolves against the file's directory
 * and the face's own open stands for it. */
export function documentRenderer(root, context) {
  const smd = window.smd;
  const stack = [{ node: root, kind: 'root' }];
  let openFence = null;

  // The face's own code block, the block the transcript's own words stand in: the name the fence
  // named in the head, the act the block invites, and the pre that carries the words. The words flow
  // into the code element, which is why the code stands on the stack and not the block.
  const fenceBlock = () => {
    const block = el('div', 'sahw-code');
    const head = el('div', 'sahw-code__head');
    const name = el('span', 'sahw-code__name', 'text');
    head.appendChild(name);
    const code = el('code');
    const pre = el('pre', 'sahw-pre sahw-prose-pre sahw-scroll-area');
    pre.appendChild(code);
    block.appendChild(head);
    block.appendChild(pre);
    const rec = { name, code, claim: '' };
    const mark = action(COPY_GLYPH, 'Copy the block to the clipboard', () => {
      navigator.clipboard.writeText(rec.code.textContent).then(
        () => flashMark(mark, '✓'),
        () => flashMark(mark, '✗'),
      );
    }, 'sahw-act sahw-code__copy');
    head.appendChild(mark);
    return { block, code, rec };
  };

  // The place a link carries, stood the way the face stands a place: over the wire to the tab the
  // place owes, beside the file the word stands with to the face's own open, and nowhere else at all
  // — a place the face will not stand as a scheme stands as the words it is.
  const standLink = (a) => {
    const href = String(a._sahwHref || '');
    const scheme = linkScheme(href);
    if (LINKED_SCHEMES.includes(scheme)) {
      a.href = href;
      a.target = '_blank';
      a.rel = 'noopener';
      a.title = href;
      return;
    }
    if (!scheme && href && context.mode === 'pane') {
      const place = besideFile(context.fileDir, href);
      if (place) {
        a.href = '#';
        a.title = place;
        a.addEventListener('click', (event) => {
          event.preventDefault();
          openFile(place);
        });
        return;
      }
    }
    const words = document.createTextNode(a.textContent);
    a.replaceWith(words);
  };

  const renderer = {
    data: null,
    add_token: (data, type) => {
      const current = stack[stack.length - 1];
      if (type === smd.CODE_FENCE || type === smd.CODE_BLOCK) {
        const fence = fenceBlock();
        current.node.appendChild(fence.block);
        stack.push({ node: fence.code, kind: 'fence', rec: fence.rec });
        openFence = fence.rec;
        return;
      }
      let node;
      switch (type) {
        case smd.DOCUMENT: node = root; break;
        case smd.PARAGRAPH: node = el('p'); break;
        case smd.HEADING_1: node = el('h1'); break;
        case smd.HEADING_2: node = el('h2'); break;
        case smd.HEADING_3: node = el('h3'); break;
        case smd.HEADING_4: node = el('h4'); break;
        case smd.HEADING_5: node = el('h5'); break;
        case smd.HEADING_6: node = el('h6'); break;
        case smd.BLOCKQUOTE: node = el('blockquote'); break;
        case smd.RULE: node = el('hr'); break;
        case smd.LIST_UNORDERED: node = el('ul'); break;
        case smd.LIST_ORDERED: node = el('ol'); break;
        case smd.LIST_ITEM: node = el('li'); break;
        case smd.CHECKBOX: {
          const box = el('input');
          box.setAttribute('type', 'checkbox');
          box.setAttribute('disabled', '');
          node = box;
          break;
        }
        case smd.TABLE: node = el('table'); break;
        case smd.TABLE_ROW: node = el('tr'); break;
        case smd.TABLE_CELL: node = el('td'); break;
        case smd.ITALIC_AST:
        case smd.ITALIC_UND: node = el('em'); break;
        case smd.STRONG_AST:
        case smd.STRONG_UND: node = el('strong'); break;
        case smd.STRIKE: node = el('del'); break;
        case smd.CODE_INLINE:
        case smd.EQUATION_INLINE: node = el('code'); break;
        case smd.EQUATION_BLOCK: node = el('pre'); break;
        case smd.LINK:
        case smd.RAW_URL: {
          const a = el('a', 'sahw-doc__link');
          a._sahwHref = '';
          node = a;
          break;
        }
        case smd.IMAGE:
        default:
          // A picture the word names does not stand as a picture — the words the word gave it for —
          // and a token the face does not stand stands as the words it carries: both stand as words.
          node = document.createTextNode('');
      }
      current.node.appendChild(node);
      stack.push({ node, kind: type === smd.LINK || type === smd.RAW_URL ? 'link' : 'el' });
    },
    add_text: (data, text) => {
      const current = stack[stack.length - 1];
      if (current.node.tagName === '#text') current.node.nodeValue += text;
      else current.node.appendChild(document.createTextNode(text));
    },
    set_attr: (data, type, value) => {
      const current = stack[stack.length - 1];
      if (type === smd.Attr.Lang && openFence) {
        // The claim the fence made, stood as the block grows: the head says what the word said the
        // moment the word said it, and the block wears the language it was named with. The grammar
        // follows the content, and the face's own fence already stands it — the end re-asks it.
        const claim = String(value).trim().toLowerCase() || 'text';
        openFence.claim = claim;
        openFence.name.textContent = claim;
        openFence.code.className = 'language-' + claim;
        return;
      }
      if (current.node.tagName === '#text') return;
      if (type === smd.Attr.Href) current.node._sahwHref = String(value);
      else if (type === smd.Attr.Checked) current.node.setAttribute('checked', String(value));
      else if (type === smd.Attr.Start) current.node.setAttribute('start', String(value));
      // the picture's own place: the words the word gave it for stand as words, and the place it
      // points is not stood, because the face will not fetch a byte it was not asked for
    },
    end_token: (data) => {
      const entry = stack.pop();
      if (!entry) return;
      if (entry.kind === 'fence') {
        entry.rec.name.textContent = entry.rec.claim.trim().toLowerCase() || 'text';
        entry.rec.code.className = 'language-' + fenceLang(entry.rec.claim.trim().toLowerCase() || 'text', entry.rec.code.textContent);
        openFence = null;
      } else if (entry.kind === 'link') {
        standLink(entry.node);
      }
    },
  };
  return renderer;
}

/** The reading the word owes, stood the way the face already stands its own word: a fresh parse of
 * the whole word the render holds, ended the way the parser owes an ending, the way the render that
 * re-asks the highlighter stands it. The words the word spells stand as words, because the parser
 * never writes markup and the face's own hands are the only hands that write the word. A window that
 * carries no library stands the word it does not stand, and the reading the face stood before the
 * reading stands whole. */
export function renderWord(root, text, context) {
  const smd = window.smd;
  if (!smd) return false;
  const parser = smd.parser(documentRenderer(root, context || { mode: 'transcript' }));
  smd.parser_write(parser, String(text));
  smd.parser_end(parser);
  return true;
}

export function proseSegments(text) {
  const segments = [];
  const lines = String(text).split('\n');
  let start = 0;
  let lang = null;
  for (let i = 0; i < lines.length; i++) {
    const open = lang === null && /^ {0,3}```(.*)$/.exec(lines[i]);
    if (open) {
      if (i > start) segments.push({ type: 'text', value: lines.slice(start, i).join('\n') });
      lang = (open[1] || '').trim().toLowerCase() || 'text';
      start = i + 1;
    } else if (lang !== null && /^ {0,3}```/.test(lines[i])) {
      const value = lines.slice(start, i).join('\n');
      segments.push({ type: 'code', lang: fenceLang(lang, value), label: lang, value });
      lang = null;
      start = i + 1;
    }
  }
  if (lang !== null) {
    // The fence the word dies in stands to the end of the word: the block is the tail, and the tail
    // is not owed a second time as prose.
    const value = lines.slice(start).join('\n');
    segments.push({ type: 'code', lang: fenceLang(lang, value), label: lang, value });
  } else if (start < lines.length) {
    segments.push({ type: 'text', value: lines.slice(start).join('\n') });
  }
  if (!segments.length) segments.push({ type: 'text', value: String(text) });
  return segments;
}

export function bubble(step, fromModel) {
  const box = el('div', fromModel ? 'sahw-bubble' : 'sahw-bubble sahw-bubble--secondary');
  // The word the turn speaks, read the way the word is read: the reading the library stands, when
  // the window carries it — the theme's own prose sheet, and the face's own hands the only hands
  // that write the word — and when it carries none, the reading the face stood before: prose is
  // text, and a fenced block is the face's own pre.
  const content = el('div', 'sahw-bubble__content sahw-text' + (window.smd ? ' sahw-prose' : ''));
  if (!renderWord(content, step.text, { mode: 'transcript' })) {
    for (const segment of proseSegments(step.text)) {
      if (segment.type === 'text') {
        content.appendChild(document.createTextNode(segment.value));
      } else {
        // The block's own settled ground: the name the fence named, the one act the block invites (its
        // words to the clipboard), and the pre that carries them — the theme's sand read in the theme's
        // own charcoal, so the ground and the words are one pair whatever the theme stands.
        const block = el('div', 'sahw-code');
        const head = el('div', 'sahw-code__head');
        // The name the fence named, and not the grammar the content followed: the head says what the
        // word said, and the block says what the content is.
        head.appendChild(el('span', 'sahw-code__name', segment.label || segment.lang));
        const mark = action(COPY_GLYPH, 'Copy the block to the clipboard', () => {
          navigator.clipboard.writeText(segment.value).then(
            () => flashMark(mark, '✓'),
            () => flashMark(mark, '✗'),
          );
        }, 'sahw-act sahw-code__copy');
        head.appendChild(mark);
        block.appendChild(head);
        const pre = el('pre', 'sahw-pre sahw-prose-pre sahw-scroll-area');
        const code = el('code', `language-${segment.lang}`);
        code.textContent = segment.value;
        pre.appendChild(code);
        block.appendChild(pre);
        content.appendChild(block);
      }
    }
  }
  box.appendChild(content);
  if (window.Prism) window.Prism.highlightAllUnder(box);
  // The operator's attachments, in the face's eyes: every line of this word that names a file the
  // server wrote into the run's estate is shown beside the words that name it — the frame if the path
  // claims a picture, the chip that opens the preview if it claims anything else. The lines are not
  // taken out of the text above — they are what the run was sent with.
  const attached = filesRow(attachedPaths(step.text));
  if (attached) box.appendChild(attached);
  return box;
}

/** A call: the tool's name and one line naming what it was pointed at, with the answers it got under
 * them. A call with no answer yet is the row the clock works for: it says how long the tool has been
 * going, and keeps saying it, until an answer arrives and the row stands at the moment it started. */
export function toolRow(call, results) {
  const row = el('div', 'sahw-tool');
  const line = el('div', 'sahw-tool__line');
  line.appendChild(el('span', 'sahw-tool__name sahw-badge', call.name || 'call'));
  const summary = argumentSummary(call);
  if (summary) line.appendChild(el('span', 'sahw-tool__args', summary));
  // The change earns its act on the line that carries it: a call whose answer says a change landed can
  // be asked for that change, and one whose answer refused it — or that displaced text it never held,
  // as a write does — is asked for nothing it cannot stand. The mark stands at the line's right edge,
  // in front of the timestamp, where the face stands the marks a line wears when it carries more than
  // it shows.
  const change = editChange(call, results);
  // The command earns its act the same way and for the opposite reason: where the change's act is owed
  // by an answer that says a change landed, this one is owed by the line itself, whose own word is not
  // the word the record holds. It stands beside the change's mark, in front of the timestamp.
  const withheld = heldCommand(call);
  // The tail the line's right edge keeps: the marks a line wears when it carries more than it shows,
  // and the timestamp the waiting call wears — pushed to the edge by its own margin, so a short line
  // and a long one say the same thing at the place the reader looks for it.
  const tail = el('div', 'sahw-tool__tail');
  if (change) tail.appendChild(changeMark(call));
  if (withheld) tail.appendChild(commandMark(call));
  const clock = clockSpan(call, results.length === 0 && runWorks());
  if (clock) tail.appendChild(clock);
  if (tail.children.length) line.appendChild(tail);
  row.appendChild(line);
  // The reading the asking stands: under the line it was asked under, over the receipt that earned it.
  if (change && state.changes.has(call.id)) row.appendChild(changeBox(change));
  // …and the command the line withholds stands in the same place, the call's answer being the answer's
  // own business: a command is known the moment the call stands, so a call whose answer is still arriving
  // stands its command exactly as one whose answer has landed does.
  if (withheld && state.commands.has(call.id)) row.appendChild(commandBox(withheld));
  // The file the call touched, when the call is one of the two that touch files: its answer is the
  // line that opens it, and the mark stands at the answer's right edge.
  const touch = TOUCHES[call.name] ? argumentPath(call) : '';
  for (const answer of results) row.appendChild(resultBlock(answer, touch || null));
  // The answer still arriving, in the box its answer will occupy: the same cap, the same file mark,
  // because the file a write is writing is a file this page can show mid-write. The `result` step takes
  // the same box over with the record's content the moment it lands (see `settleStep`), and a call that
  // has an answer has no words on the way — the record's content is already the whole of it.
  //
  // The row is remembered either way, as a row an arriving answer can grow: the frame a fragment brings
  // finds its box here and grows it where it stands, and finds that no box stands yet when the words have
  // only just begun — which is the row's shape changing, and the rebuild's occasion rather than the
  // frame's. A call with an answer has no entry: there is nothing for it to arrive into.
  if (!results.length) {
    const stood = { call, touch: touch || null, box: null, text: '' };
    standingBoxes.add(stood);
    const arriving = inflightResult(call);
    if (arriving) {
      stood.box = resultBlock({ content: arriving.text }, touch || null);
      stood.text = arriving.text;
      row.appendChild(stood.box);
    }
  }
  return row;
}
