// The search logic of docs/assets/js/search-core.js, plus a smoke test of the generated docs/search/pages.json.
// usage: nix-shell -p nodejs --run 'node --test tools/test_search.mjs'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { createSearch, snippet } from '../docs/assets/js/search-core.js'

function pagesWithTexts (...texts) {
  return texts.map((text, id) => ({ id, path: `page-${id}/`, title: `Page ${id}`, headings: '', author: '', byline: '', section: '', text }))
}

function foundIds (texts, query) {
  return createSearch(pagesWithTexts(...texts)).run(query).map(result => result.page.id).sort()
}

function markedTexts (excerpt) {
  return excerpt.segments.filter(segment => segment.marked).map(segment => segment.text)
}

test('a quoted phrase only matches pages that contain it in that order', () => {
  const texts = ['async exceptions are hard', 'exceptions that are async']
  assert.deepEqual(foundIds(texts, '"async exceptions"'), [0])
  assert.deepEqual(foundIds(texts, 'async exceptions'), [0, 1])
})

test('every word of the query has to match', () => {
  assert.deepEqual(foundIds(['bracket and mask', 'bracket alone'], 'bracket mask'), [0])
})

test('operators are searchable', () => {
  assert.deepEqual(foundIds(['use <$> here', 'use fmap here'], '<$>'), [0])
})

test('a word in single quotes is found without its quote mark', () => {
  assert.deepEqual(foundIds(["it is 'pure in a sense", 'nothing here'], 'pure'), [0])
})

test('the snippet goes where most of the words are, and marks them', () => {
  const excerpt = snippet('alpha ' + 'filler '.repeat(60) + 'beta and gamma end', ['alpha', 'beta', 'gamma'])
  assert.deepEqual(markedTexts(excerpt), ['beta', 'gamma'])
  assert.equal(excerpt.anchor, 'beta')
  assert.ok(excerpt.before)
})

test('the snippet prefers the quoted phrase over more loose words', () => {
  const excerpt = snippet('beta gamma delta ' + 'filler '.repeat(60) + 'alpha beta end', ['alpha', 'beta', 'gamma', 'delta'], ['alpha beta'])
  assert.equal(excerpt.anchor, 'alpha beta')
  assert.deepEqual(markedTexts(excerpt), ['alpha beta'])
})

test('a term only lights up at the start of a word', () => {
  assert.deepEqual(markedTexts(snippet('the ratio of IO actions', ['io'])), ['IO'])
})

test('the published index finds the bracket post', () => {
  const pages = JSON.parse(readFileSync(new URL('../docs/search/pages.json', import.meta.url), 'utf8'))
  const top = createSearch(pages).run('bracket').slice(0, 5).map(result => result.page.path)
  assert.ok(top.includes('blog/tale-of-two-brackets/'), `top results were ${top}`)
})
