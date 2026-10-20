import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp, mkdir, writeFile, readFile, access, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join, resolve, basename} from 'node:path';
import {collectResources, repairMainBackground, resourceCandidates, mediaBase, themeFor}
  from '../review_manifest.mjs';
import {buildReviewManifest} from '../review_manifest.mjs';

test('review data binds exact backgrounds, cover, logo and intro/loop with URL deduplication', () => {
  const table = {a: {kvImageId: 'kv_a.png', titleImageId: 'title_a.png'},
    b: {kvImageId: 'kv_b.png', titleImageId: 'title_b.png'}};
  const reviews = {a: {backgroundId: 'storybg_a.png', gameMusicName: 'shared'},
    b: {backgroundId: 'storybg_a.png', gameMusicName: 'shared'}};
  const resources = collectResources(table, reviews, {
    shared: {intro: 'audio/i.mp3', loop: 'audio/l.mp3'}});
  assert.equal(resources.length, 7);
  assert.deepEqual(resources.find(x => x.url.endsWith('/audio/l.mp3')).stories, ['a', 'b']);
  assert.ok(resources.some(x => x.url.endsWith('/retrobkgs/storybg_a.png')));
  assert.throws(() => collectResources(table, {}, {}), /Missing story review/);
});

test('curated collab absolute URLs and multipart backgrounds override normal paths', () => {
  const meta = {audio: {loop: 'https://example.com/theme.wav'},
    kvImageId: 'https://example.com/entry.png', titleImageId: 'https://example.com/logo.png',
    backgroundUrls: ['https://example.com/left.png', 'https://example.com/right.png'],
    coverContainsTitle: true};
  const theme = themeFor('collab', meta, {});
  assert.equal(theme.coverUrl, meta.kvImageId);
  assert.deepEqual(theme.backgroundUrls, meta.backgroundUrls);
  const resources = collectResources({collab: meta}, {collab: meta}, {});
  assert.equal(resources.filter(x => x.roles.includes('background')).length, 2);
  assert.ok(resources.some(x => x.url === 'https://example.com/theme.wav'));
});

test('legacy invented main filenames are repaired without overriding explicit art', () => {
  const meta = {type: 'MAIN_STORY', kvImageId: 'kv_evil_time_part1.png'};
  assert.equal(repairMainBackground(meta, {backgroundId: 'storybg_main_0.png'}).backgroundId,
    'storybg_evil_time_part1.png');
  const custom = {backgroundId: 'https://example.com/bg.png'};
  assert.deepEqual(repairMainBackground(meta, custom), custom);
});

test('silent review themes keep their art and do not download first-story music', () => {
  const meta = {kvImageId: 'card.png', titleImageId: 'title.png',
    backgroundId: 'bg.png', musicRole: 'opening-story', gameMusicName: 'story.path',
    audio: {intro: 'https://example.com/first-intro.mp3', loop: 'https://example.com/first-loop.mp3'}};
  const resources = collectResources({event: meta}, {event: meta}, {});
  assert.equal(resources.length, 3);
  assert.ok(resources.every(r => !r.roles.includes('music')));
  meta.musicRole = 'none'; meta.gameMusicName = null; meta.audio = {intro: null, loop: null};
  assert.equal(collectResources({event: meta}, {event: meta}, {}).length, 3);
});

test('missing fork audio can use the same exact file on upstream or PRTS', () => {
  assert.deepEqual(resourceCandidates(mediaBase + 'audio/sound_beta_2/music/act16main/theme.mp3'), [
    mediaBase + 'audio/sound_beta_2/music/act16main/theme.mp3',
    mediaBase.replace('/KakkoiiSaber/', '/akgcc/') + 'audio/sound_beta_2/music/act16main/theme.mp3',
    'https://torappu.prts.wiki/assets/audio/music/act16main/theme.mp3']);
  assert.deepEqual(resourceCandidates('https://example.com/custom.png'), ['https://example.com/custom.png']);
});

test('missing media preserves the previous published manifest', async () => {
  const root = await mkdtemp(join(tmpdir(), 'arkstory-bundle-test-'));
  const folder = join(root, 'data/assets/zh_CN');
  const output = join(root, 'output');
  const fetch = globalThis.fetch;
  try {
    await mkdir(join(folder, 'story_review_info'), {recursive: true});
    await writeFile(join(folder, 'story_meta_table.json'), JSON.stringify({fixture: {
      type: 'MAIN_STORY', kvImageId: 'https://example.com/missing.png'}}));
    await writeFile(join(folder, 'audio_data.json'), '{}');
    await writeFile(join(folder, 'story_review_info/fixture.json'), '{}');
    const previous = '{"version":1,"revision":"previous"}';
    const published = join(root, 'review_manifest.json');
    await writeFile(published, previous);
    globalThis.fetch = async () => new Response(null, {status: 404});
    await assert.rejects(buildReviewManifest({dataDir: join(root, 'data'), output,
      cache: join(root, 'cache')}), /1 missing review resources/);
    assert.equal(await readFile(published, 'utf8'), previous);
    const report = JSON.parse(await readFile(join(output, 'report.json'), 'utf8'));
    assert.equal(report.failures.length, 1);
    assert.deepEqual(report.failures[0].stories, ['fixture']);
  } finally {
    globalThis.fetch = fetch;
    assert.equal(resolve(root).startsWith(resolve(tmpdir())), true);
    assert.ok(basename(root).startsWith('arkstory-bundle-test-'));
    await rm(root, {recursive: true, force: true});
  }
});


test('publishes content-addressed metadata and changes version only when content changes', async () => {
  const root = await mkdtemp(join(tmpdir(), 'arkstory-manifest-success-'));
  const folder = join(root, 'data/assets/zh_CN');
  const output = join(root, 'published/review_payload');
  const originalFetch = globalThis.fetch;
  let media = Buffer.from('cover-one');
  try {
    await mkdir(join(folder, 'story_review_info'), {recursive: true});
    await writeFile(join(folder, 'story_meta_table.json'), JSON.stringify({fixture: {
      type: 'MAIN_STORY', kvImageId: 'https://example.com/cover.png'}}));
    await writeFile(join(folder, 'audio_data.json'), '{}');
    await writeFile(join(folder, 'story_review_info/fixture.json'), '{"name":"First"}');
    globalThis.fetch = async () => new Response(media, {status: 200});
    const options = {dataDir: join(root, 'data'), output, cache: join(root, 'cache'),
      publicBase: 'https://example.com/data'};
    await buildReviewManifest(options);
    const manifestPath = join(root, 'published/review_manifest.json');
    const first = JSON.parse(await readFile(manifestPath, 'utf8'));
    assert.equal(Object.keys(first.resources).length, 4);
    const catalog = Object.values(first.resources).filter(r => r.roles.includes('metadata'));
    assert.equal(catalog.length, 3);
    for (const r of catalog) {
      assert.ok(r.sources[0].startsWith('https://example.com/data/assets/review_payload/files/'));
      await access(join(output, 'files', `${r.sha256}.json`));
    }
    await buildReviewManifest(options);
    assert.equal(JSON.parse(await readFile(manifestPath, 'utf8')).revision, first.revision);
    media = Buffer.from('cover-two');
    await buildReviewManifest({...options, refresh: true});
    const changed = JSON.parse(await readFile(manifestPath, 'utf8'));
    assert.notEqual(changed.revision, first.revision);
    assert.notEqual(changed.resources['https://example.com/cover.png'].sha256,
      first.resources['https://example.com/cover.png'].sha256);
  } finally {
    globalThis.fetch = originalFetch;
    assert.ok(resolve(root).startsWith(resolve(tmpdir())));
    assert.ok(basename(root).startsWith('arkstory-manifest-success-'));
    await rm(root, {recursive: true, force: true});
  }
});
