import assert from 'node:assert/strict'
import {mkdtemp, readFile, rm, writeFile} from 'node:fs/promises'
import {tmpdir} from 'node:os'
import {join, resolve} from 'node:path'
import {spawnSync} from 'node:child_process'
import test from 'node:test'

const script = resolve('util/highlight-starry-night.mjs')

test('highlights plain Kramdown just blocks without Rouge', async () => {
  const html = await processBlock('just', 'default:\n    just test\n')
  assert.match(html, /data-highlighter="starry-night"/)
  assert.match(html, /class="pl-/)
  assert.match(html, /class="rouge-code"/)
  assert.doesNotMatch(html, /highlighter-rouge/)
})

test('renders text and plaintext blocks as unhighlighted Starry Night code blocks', async () => {
  for (const flag of ['text', 'plaintext']) {
    const html = await processBlock(flag, '<not markup>\n')
    assert.match(html, /data-highlighter="starry-night"/)
    assert.match(html, /data-label-text="Text"/)
    assert.match(html, /&lt;not markup&gt;/)
    assert.doesNotMatch(html, /class="pl-/)
  }
})

async function processBlock(flag, value) {
  const directory = await mkdtemp(join(tmpdir(), 'starry-night-'))
  const page = join(directory, 'index.html')

  try {
    const encoded = value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
    await writeFile(page, `<html><body><pre><code class="language-${flag}">${encoded}</code></pre></body></html>`)

    const result = spawnSync(process.execPath, [script, directory], {
      encoding: 'utf8',
      env: process.env
    })
    assert.equal(result.status, 0, result.stderr)
    return await readFile(page, 'utf8')
  } finally {
    await rm(directory, {recursive: true, force: true})
  }
}
