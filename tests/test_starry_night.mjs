import assert from 'node:assert/strict'
import {mkdtemp, readFile, rm, writeFile} from 'node:fs/promises'
import {tmpdir} from 'node:os'
import {join, resolve} from 'node:path'
import {spawnSync} from 'node:child_process'
import test from 'node:test'

const script = resolve('util/highlight-starry-night.mjs')

test('highlights plain Kramdown just blocks without Rouge', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'starry-night-'))
  const page = join(directory, 'index.html')

  try {
    await writeFile(
      page,
      '<html><body><pre><code class="language-just">default:\n    just test\n</code></pre></body></html>'
    )

    const result = spawnSync(process.execPath, [script, directory], {
      encoding: 'utf8',
      env: process.env
    })
    assert.equal(result.status, 0, result.stderr)

    const html = await readFile(page, 'utf8')
    assert.match(html, /data-highlighter="starry-night"/)
    assert.match(html, /class="pl-/)
    assert.match(html, /class="rouge-code"/)
    assert.doesNotMatch(html, /highlighter-rouge/)
  } finally {
    await rm(directory, {recursive: true, force: true})
  }
})
