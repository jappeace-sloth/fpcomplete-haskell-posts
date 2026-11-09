import { createSearch, snippet } from './search-core.js'

const form = document.getElementById('search-form')
const input = document.getElementById('search-input')
const status = document.getElementById('search-status')
const results = document.getElementById('search-results')

async function loadPages (url) {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`${url} answered HTTP ${response.status}`)
  }
  return response.json()
}

// A text fragment scrolls the opened page to the match, in browsers that support them.
function resultLink (base, page, anchor) {
  const fragment = anchor === null ? '' : '#:~:text=' + encodeURIComponent(anchor).replace(/-/g, '%2D')
  return base + page.path + fragment
}

function snippetParagraph (excerpt) {
  const paragraph = document.createElement('p')
  paragraph.className = 'search-snippet'
  if (excerpt.before) paragraph.append('… ')
  for (const segment of excerpt.segments) {
    if (segment.marked) {
      const mark = document.createElement('mark')
      mark.textContent = segment.text
      paragraph.append(mark)
    } else {
      paragraph.append(segment.text)
    }
  }
  if (excerpt.after) paragraph.append(' …')
  return paragraph
}

function resultItem (base, result) {
  const excerpt = snippet(result.page.text, result.terms, result.phrases)
  const item = document.createElement('li')
  const title = document.createElement('a')
  title.className = 'search-result-title'
  title.href = resultLink(base, result.page, excerpt.anchor)
  title.textContent = result.page.title
  const meta = document.createElement('div')
  meta.className = 'post-meta'
  meta.textContent = [result.page.byline, result.page.section].filter(Boolean).join(' · ')
  item.append(title, meta, snippetParagraph(excerpt))
  return item
}

function render (search, base, query) {
  results.replaceChildren()
  if (query.trim() === '') {
    status.textContent = `Type to search ${search.pageCount} pages.`
    return
  }
  const found = search.run(query)
  status.textContent = found.length === 0
    ? 'No page matches.'
    : `${found.length} ${found.length === 1 ? 'page matches' : 'pages match'}.`
  results.append(...found.map(result => resultItem(base, result)))
}

function rememberQuery (query) {
  const url = new URL(window.location.href)
  if (query.trim() === '') {
    url.searchParams.delete('q')
  } else {
    url.searchParams.set('q', query)
  }
  window.history.replaceState(null, '', url)
}

async function main () {
  input.value = new URLSearchParams(window.location.search).get('q') || ''
  let pages
  try {
    pages = await loadPages(form.dataset.pages)
  } catch (problem) {
    status.textContent = `The search index did not load: ${problem.message}`
    throw problem
  }
  const search = createSearch(pages)
  const update = () => {
    render(search, form.dataset.base, input.value)
    rememberQuery(input.value)
  }
  input.addEventListener('input', update)
  form.addEventListener('submit', event => {
    event.preventDefault()
    update()
  })
  update()
}

main()
