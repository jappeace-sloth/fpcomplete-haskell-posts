// Search over search/pages.json, without the DOM, so tools/test_search.mjs can run it in Node.
// Decision: MiniSearch, indexing the page texts in the browser (1.7 MB, 0.55 MB
// gzipped). Pagefind needs a build step after Jekyll, which the branch-built
// Pages site does not run; a prebuilt Lunr or MiniSearch index needs Node at
// build time and ships next to the texts, which the snippets need anyway.
import MiniSearch from './minisearch-7.2.0.js'

// Identifiers keep primes and underscores (foldl', _unused), and runs of symbol
// characters are terms too, so operators such as >>= and <$> can be looked up.
const TERM = /[\p{L}\p{N}_']+|[!#$%&*+./<=>?@\\^|~:-]{2,}/gu
const IDENTIFIER_CHARACTER = /[\p{L}\p{N}_']/u
const PHRASE = /"([^"]+)"/g
const SNIPPET_BEFORE = 60
const SNIPPET_LENGTH = 240
// Bounds the snippet search on long pages where a common word occurs hundreds of times.
const MAXIMUM_OCCURRENCES_PER_NEEDLE = 100

function tokenize (text) {
  return text.match(TERM) || []
}

// A leading prime is a quotation mark ('SELECT), never part of a Haskell identifier.
function processTerm (term) {
  return term.toLowerCase().replace(/^'+/, '') || null
}

function quotedPhrases (query) {
  return Array.from(query.matchAll(PHRASE), match => match[1].toLowerCase().split(/\s+/).filter(Boolean).join(' '))
    .filter(Boolean)
}

/**
 * A search over pages. run(query) gives results best first as { page, terms, phrases },
 * where terms are the indexed terms that matched and phrases the quoted parts of the query.
 */
export function createSearch (pages) {
  const index = new MiniSearch({
    fields: ['title', 'headings', 'author', 'text'],
    tokenize,
    processTerm,
    searchOptions: {
      combineWith: 'AND',
      boost: { title: 4, headings: 2, author: 2 },
      prefix: term => term.length >= 3,
      fuzzy: term => (term.length >= 6 ? 0.2 : false)
    }
  })
  index.addAll(pages)
  const pagesById = new Map(pages.map(page => [page.id, page]))
  const lowercased = new Map(pages.map(page => [page.id, (page.title + ' ' + page.text).toLowerCase()]))
  return {
    pageCount: pages.length,
    run (query) {
      const phrases = quotedPhrases(query)
      return index.search(query)
        .filter(result => phrases.every(phrase => lowercased.get(result.id).includes(phrase)))
        .map(result => ({ page: pagesById.get(result.id), terms: result.terms, phrases }))
    }
  }
}

function escapeRegExp (text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

// Terms match at the start of a token, so "io" does not light up the middle of "ratio".
function needlePattern (needle) {
  const boundary = IDENTIFIER_CHARACTER.test(needle[0]) ? "(?<![\\p{L}\\p{N}_'])" : '(?<![!#$%&*+./<=>?@\\\\^|~:-])'
  return new RegExp(boundary + escapeRegExp(needle).replace(/ /g, '\\s+'), 'giu')
}

function occurrences (text, needles) {
  const found = []
  needles.forEach((needle, needleIndex) => {
    let count = 0
    for (const match of text.matchAll(needlePattern(needle))) {
      found.push({ start: match.index, end: match.index + match[0].length, needleIndex })
      count += 1
      if (count >= MAXIMUM_OCCURRENCES_PER_NEEDLE) break
    }
  })
  return found.sort((left, right) => left.start - right.start || right.end - left.end)
}

// The occurrence whose snippet window holds the most distinct needles, earliest on a
// tie. A window with a phrase beats any without one: the phrase is what the reader asked for.
function bestOccurrence (found, needleCount, phraseCount) {
  let best = null
  let bestScore = 0
  for (let first = 0; first < found.length; first++) {
    const windowEnd = found[first].start - SNIPPET_BEFORE + SNIPPET_LENGTH
    const seen = new Set()
    for (let other = first; other < found.length && found[other].start < windowEnd; other++) {
      seen.add(found[other].needleIndex)
    }
    const hasPhrase = Array.from(seen).some(needleIndex => needleIndex < phraseCount)
    const score = seen.size + (hasPhrase ? needleCount : 0)
    if (score > bestScore) {
      best = found[first]
      bestScore = score
    }
  }
  return best
}

function snippetWindow (text, best) {
  if (best === null) {
    return { start: 0, end: Math.min(text.length, SNIPPET_LENGTH) }
  }
  let start = Math.max(0, best.start - SNIPPET_BEFORE)
  if (start > 0) {
    const space = text.indexOf(' ', start)
    start = space === -1 || space >= best.start ? best.start : space + 1
  }
  let end = Math.min(text.length, start + SNIPPET_LENGTH)
  if (end < text.length) {
    const space = text.lastIndexOf(' ', end)
    end = space > best.end ? space : Math.max(end, best.end)
  }
  return { start, end }
}

/**
 * A short excerpt of text around the matched terms and quoted phrases.
 * segments, joined, are a slice of text, with the matches marked; before and after
 * say whether text continues past the slice. anchor is the best match as written
 * in the text, or null when nothing matched.
 */
export function snippet (text, terms, phrases = []) {
  const quoted = phrases.filter(Boolean)
  const needles = quoted.concat(terms.filter(Boolean))
  const found = occurrences(text, needles)
  const best = bestOccurrence(found, needles.length, quoted.length)
  const { start, end } = snippetWindow(text, best)
  const segments = []
  let position = start
  for (const occurrence of found) {
    if (occurrence.start < position || occurrence.end > end) continue
    if (occurrence.start > position) segments.push({ text: text.slice(position, occurrence.start), marked: false })
    segments.push({ text: text.slice(occurrence.start, occurrence.end), marked: true })
    position = occurrence.end
  }
  if (position < end) segments.push({ text: text.slice(position, end), marked: false })
  return {
    segments,
    before: start > 0,
    after: end < text.length,
    anchor: best === null ? null : text.slice(best.start, best.end)
  }
}
