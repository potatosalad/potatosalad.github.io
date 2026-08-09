#!/usr/bin/env node

import {readFile, readdir, writeFile} from 'node:fs/promises'
import {dirname, join, resolve} from 'node:path'
import {fileURLToPath, pathToFileURL} from 'node:url'

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const modulesRoot = process.env.STARRY_NIGHT_NODE_MODULES || join(projectRoot, 'node_modules')

const [{all, createStarryNight}, {toHtml}, {parse}] = await Promise.all([
  import(pathToFileURL(join(modulesRoot, '@wooorm/starry-night/index.js')).href),
  import(pathToFileURL(join(modulesRoot, 'hast-util-to-html/index.js')).href),
  import(pathToFileURL(join(modulesRoot, 'parse5/dist/index.js')).href)
])

const destination = resolve(process.argv[2] || join(projectRoot, '_site'))
const starryNight = await createStarryNight(all)
let highlightedBlocks = 0

for (const path of await htmlFiles(destination)) {
  const source = await readFile(path, 'utf8')
  const transformed = highlightDocument(source)
  if (transformed !== source) await writeFile(path, transformed)
}

console.log(`Starry Night highlighted ${highlightedBlocks} code blocks in ${destination}`)

async function htmlFiles(directory) {
  const paths = []
  for (const entry of await readdir(directory, {withFileTypes: true})) {
    const path = join(directory, entry.name)
    if (entry.isDirectory()) paths.push(...await htmlFiles(path))
    else if (entry.isFile() && entry.name.endsWith('.html')) paths.push(path)
  }
  return paths
}

function highlightDocument(source) {
  const document = parse(source, {sourceCodeLocationInfo: true})
  const replacements = []

  visit(document, (node) => {
    if (node.tagName !== 'code' || node.parentNode?.tagName !== 'pre') return

    const languageClass = classes(node).find((name) => name.startsWith('language-'))
    const flag = languageClass?.slice('language-'.length)
    const plainText = flag === 'text' || flag === 'plaintext' || flag === 'txt'
    const scope = flag && starryNight.flagToScope(flag)
    const pre = node.parentNode

    if ((!scope && !plainText) || !pre.sourceCodeLocation) return

    const value = textContent(node)
    const highlighted = scope ? toHtml(starryNight.highlight(value, scope)) : escapeHtml(value)
    const lineCount = Math.max(1, value.endsWith('\n') ? value.split('\n').length - 1 : value.split('\n').length)
    const lineNumbers = Array.from({length: lineCount}, (_, index) => index + 1).join('\n')
    const safeFlag = escapeAttribute(flag)
    const label = escapeHtml(languageLabel(flag))
    const replacement = `<div class="language-${safeFlag} highlighter-starry-night" data-highlighter="starry-night"><div class="code-header">
        <span data-label-text="${label}"><i class="fas fa-code fa-fw small"></i></span>
      <button aria-label="copy" data-title-succeed="Copied!"><i class="far fa-clipboard"></i></button></div><div class="highlight"><code><table class="rouge-table"><tbody><tr><td class="rouge-gutter gl"><pre class="lineno">${lineNumbers}\n</pre></td><td class="rouge-code"><pre>${highlighted}</pre></td></tr></tbody></table></code></div></div>`

    replacements.push({
      start: pre.sourceCodeLocation.startOffset,
      end: pre.sourceCodeLocation.endOffset,
      value: replacement
    })
    highlightedBlocks += 1
  })

  replacements.sort((left, right) => right.start - left.start)
  for (const replacement of replacements) {
    source = source.slice(0, replacement.start) + replacement.value + source.slice(replacement.end)
  }
  return source
}

function visit(node, callback) {
  callback(node)
  for (const child of node.childNodes || []) visit(child, callback)
}

function languageLabel(flag) {
  const aliases = {
    bash: 'Shell',
    c: 'C',
    cpp: 'C++',
    css: 'CSS',
    html: 'HTML',
    js: 'JavaScript',
    json: 'JSON',
    md: 'Markdown',
    plaintext: 'Text',
    sh: 'Shell',
    text: 'Text',
    ts: 'TypeScript',
    xml: 'XML'
  }
  return aliases[flag] || flag.charAt(0).toUpperCase() + flag.slice(1)
}

function escapeAttribute(value) {
  return escapeHtml(value).replaceAll('`', '&#96;')
}

function escapeHtml(value) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('"', '&quot;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
}

function classes(node) {
  return attribute(node, 'class')?.split(/\s+/).filter(Boolean) || []
}

function attribute(node, name) {
  return node.attrs?.find((item) => item.name === name)?.value
}

function textContent(node) {
  if (node.nodeName === '#text') return node.value
  return (node.childNodes || []).map(textContent).join('')
}
