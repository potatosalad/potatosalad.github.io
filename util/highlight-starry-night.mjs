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
    if (!hasClass(node, 'highlighter-rouge') || hasAttribute(node, 'data-highlighter')) return

    const languageClass = classes(node).find((name) => name.startsWith('language-'))
    const flag = languageClass?.slice('language-'.length)
    const scope = flag && starryNight.flagToScope(flag)
    const code = findDescendant(node, (candidate) => {
      return candidate.tagName === 'pre' && hasAncestorClass(candidate, node, 'rouge-code')
    })

    if (!scope || !code?.sourceCodeLocation?.startTag || !code.sourceCodeLocation.endTag) return

    const value = textContent(code)
    const highlighted = toHtml(starryNight.highlight(value, scope))
    replacements.push({
      start: code.sourceCodeLocation.startTag.endOffset,
      end: code.sourceCodeLocation.endTag.startOffset,
      value: highlighted
    })
    replacements.push({
      start: node.sourceCodeLocation.startTag.endOffset - 1,
      end: node.sourceCodeLocation.startTag.endOffset - 1,
      value: ' data-highlighter="starry-night"'
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

function findDescendant(node, predicate) {
  for (const child of node.childNodes || []) {
    if (predicate(child)) return child
    const found = findDescendant(child, predicate)
    if (found) return found
  }
}

function hasAncestorClass(node, boundary, className) {
  for (let current = node.parentNode; current && current !== boundary; current = current.parentNode) {
    if (hasClass(current, className)) return true
  }
  return false
}

function classes(node) {
  return attribute(node, 'class')?.split(/\s+/).filter(Boolean) || []
}

function hasClass(node, className) {
  return classes(node).includes(className)
}

function attribute(node, name) {
  return node.attrs?.find((item) => item.name === name)?.value
}

function hasAttribute(node, name) {
  return node.attrs?.some((item) => item.name === name) || false
}

function textContent(node) {
  if (node.nodeName === '#text') return node.value
  return (node.childNodes || []).map(textContent).join('')
}
