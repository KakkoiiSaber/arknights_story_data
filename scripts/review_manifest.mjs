import {readFile, writeFile, mkdir, rename, stat} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {resolve, join} from 'node:path';
import {fileURLToPath} from 'node:url';

export const dataBase = 'https://raw.githubusercontent.com/KakkoiiSaber/arknights_story_data/main/assets/';
export const mediaBase = 'https://raw.githubusercontent.com/KakkoiiSaber/arkdata/main/assets/torappu/dynamicassets/';
const paths = {cover: mediaBase + 'arts/ui/mixstory/kvs/',
  logo: mediaBase + 'arts/ui/mixstory/titles/',
  background: mediaBase + 'arts/ui/mixstory/retrobkgs/', music: mediaBase};
const hash = bytes => createHash('sha256').update(bytes).digest('hex');

export function themeFor(id, meta, themes) {
  if (meta.audio && meta.kvImageId && meta.titleImageId &&
      (meta.backgroundUrls?.length || meta.backgroundId)) return {
    coverUrl: new URL(meta.kvImageId, paths.cover).href,
    titleUrl: new URL(meta.titleImageId, paths.logo).href,
    backgroundUrls: (meta.backgroundUrls ?? [meta.backgroundId]).map(p => new URL(p, paths.background).href),
    musicIntroUrl: meta.audio.intro, musicLoopUrl: meta.audio.loop,
    musicLoopSongId: meta.audio.loopSongId,
    coverContainsTitle: meta.coverContainsTitle,
  };
  return themes[id];
}

export function repairMainBackground(meta, review) {
  // Shared bg_mainLine_N IDs and legacy storybg_main_N are not mixstory files.
  // Actual mixstory filenames
  // share the verified cover suffix; don't override curated absolute URLs.
  if (meta.type === 'MAIN_STORY' && /^(?:storybg_main_|bg_mainLine_)\d+\.png$/.test(review.backgroundId ?? '') &&
      /^kv_[^/]+\.png$/.test(meta.kvImageId ?? ''))
    return {...review, backgroundId: meta.kvImageId.replace(/^kv_/, 'storybg_')};
  return review;
}

export function collectResources(table, reviews, audio, themes = {}) {
  const resources = new Map();
  const add = (value, role, story) => {
    if (!value) return;
    const url = new URL(value, paths[role]).href;
    const item = resources.get(url) ?? {url, roles: new Set(), stories: new Set()};
    item.roles.add(role); item.stories.add(story); resources.set(url, item);
  };
  const track = (value, id) => {
    add(value?.intro, 'music', id); add(value?.loop, 'music', id);
    if (value?.loop && value.loopSongId)
      resources.get(new URL(value.loop, paths.music).href).sirenSongId = String(value.loopSongId);
  };
  track(audio['sys.ON_MUSIC.bg_void'], '__home');
  for (const [id, meta] of Object.entries(table)) {
    const home = themeFor(id, meta, themes);
    add(home?.coverUrl ?? meta.kvImageId, 'cover', id);
    if (meta.type !== 'MAIN_STORY' && !(home?.coverContainsTitle ?? meta.coverContainsTitle))
      add(home?.titleUrl ?? meta.titleImageId, 'logo', id);
    const review = reviews[id];
    if (!review) throw Error(`Missing story review: ${id}`);
    const theme = themeFor(id, review, themes);
    for (const bg of theme?.backgroundUrls ?? [review.backgroundId]) add(bg, 'background', id);
    add(theme?.titleUrl ?? meta.titleImageId ?? review.titleImageId, 'logo', id);
    if (!['none', 'opening-story'].includes(review.musicRole) &&
        !review.gameMusicName?.startsWith('story.')) {
      if (theme) track({intro: theme.musicIntroUrl, loop: theme.musicLoopUrl, loopSongId: theme.musicLoopSongId}, id);
      else track(audio[review.gameMusicName], id);
    }
  }
  return [...resources.values()].map(x => ({...x, roles: [...x.roles], stories: [...x.stories]}));
}

export function resourceCandidates(url) {
  const candidates = [url];
  if (url.startsWith(mediaBase)) {
    candidates.push(url.replace('/KakkoiiSaber/arkdata/', '/akgcc/arkdata/'));
    if (url.includes('/audio/sound_beta_2/music/'))
      candidates.push('https://torappu.prts.wiki/assets/audio/music/' + url.split('/audio/sound_beta_2/music/')[1]);
  }
  return candidates;
}

async function parallel(items, concurrency, action) {
  let cursor = 0;
  await Promise.all(Array.from({length: concurrency}, async () => {
    while (cursor < items.length) await action(items[cursor++]);
  }));
}

export async function buildReviewManifest({dataDir, locales = ['zh_CN'],
  output = 'assets/review_payload', cache = '.cache/review-resources', refresh = false,
  publicBase = 'https://raw.githubusercontent.com/KakkoiiSaber/arknights_story_data/main'}) {
  await mkdir(output, {recursive: true}); await mkdir(cache, {recursive: true});
  const filesDir = join(output, 'files'); await mkdir(filesDir, {recursive: true});
  const themes = {}; // Published complement fields in story review are authoritative.
  const urls = {}, records = [], resources = new Map();
  const store = async (url, bytes, extension, source = url) => {
    const digest = hash(bytes), name = digest + extension;
    const path = `assets/review_payload/files/${name}`;
    if (extension === '.json') {
      await writeFile(join(filesDir, name), bytes);
      urls[url] = path;
    }
    records.push({url, source, path, bytes: bytes.length, sha256: digest});
  };
  const getJson = async (locale, file) => {
    const bytes = await readFile(join(dataDir, 'assets', locale, file));
    return JSON.parse(bytes.toString('utf8'));
  };
  let stories = 0;
  for (const locale of locales) {
    const [table, audio] = await Promise.all([
      getJson(locale, 'story_meta_table.json'), getJson(locale, 'audio_data.json')]);
    const reviews = {};
    await parallel(Object.entries(table), 8, async ([id, meta]) => {
      const file = `story_review_info/${id}.json`;
      reviews[id] = repairMainBackground(meta, await getJson(locale, file));
      await store(dataBase + locale + '/' + file, Buffer.from(JSON.stringify(reviews[id])), '.json');
    });
    await store(dataBase + locale + '/story_meta_table.json', Buffer.from(JSON.stringify(table)), '.json');
    await store(dataBase + locale + '/audio_data.json', Buffer.from(JSON.stringify(audio)), '.json');
    const items = collectResources(table, reviews, audio, locale === 'zh_CN' ? themes : {});
    for (const item of items) resources.set(item.url, item);
    stories += Object.keys(table).length;
  }
  let completed = 0;
  const failures = [];
  await parallel([...resources.values()], 8, async item => {
    try {
      const cacheFile = join(cache, hash(item.url));
      let bytes, source = item.url;
      try { if (!refresh) bytes = await readFile(cacheFile); } catch { /* uncached */ }
      if (!bytes?.length) {
        let lastError;
        const candidates = resourceCandidates(item.url);
        if (item.sirenSongId) {
          const song = await (await fetch(`https://monster-siren.hypergryph.com/api/song/${item.sirenSongId}`,
            {signal: AbortSignal.timeout(15000)})).json();
          if (song.data?.sourceUrl) candidates.unshift(song.data.sourceUrl);
        }
        for (const candidate of candidates) {
          for (let attempt = 0; attempt < 2; attempt++) {
            try {
              const response = await fetch(candidate, {
                headers: {Referer: 'https://prts.wiki/'}, signal: AbortSignal.timeout(60000)});
              if (!response.ok) {
                await response.body?.cancel();
                if (response.status === 404) break;
                throw Error(`HTTP ${response.status}`);
              }
              const type = response.headers.get('content-type') ?? '';
              if (type.includes('text/html')) throw Error('HTML returned instead of media');
              bytes = Buffer.from(await response.arrayBuffer());
              if (!bytes.length) throw Error('Empty resource');
              source = candidate; break;
            } catch (e) { lastError = e; }
          }
          if (bytes?.length) break;
        }
        if (!bytes?.length) throw lastError ?? Error('All resource paths returned 404');
        await writeFile(cacheFile + '.part', bytes);
        await rename(cacheFile + '.part', cacheFile);
        await writeFile(cacheFile + '.source', source);
      } else {
        try { source = await readFile(cacheFile + '.source', 'utf8'); } catch { /* old cache */ }
      }
      const extension = /\.(png|webp|jpe?g|mp3|wav|ogg|m4a)$/i.exec(new URL(item.url).pathname)?.[0];
      if (!extension) throw Error('Unrecognized media extension');
      await store(item.url, bytes, extension.toLowerCase(), source);
    } catch (error) { failures.push({...item, error: String(error)}); }
    completed++;
    if (completed % 40 === 0) console.log(`Review assets: ${completed}/${resources.size}`);
  });
  const unique = new Map(records.map(x => [x.path, x]));
  const report = {version: 1, locales, stories, resources: resources.size,
    files: unique.size, bytes: [...unique.values()].reduce((s, x) => s + x.bytes, 0),
    failures, records: records.sort((a, b) => a.url.localeCompare(b.url))};
  await writeFile(join(output, 'report.json'), JSON.stringify(report, null, 2));
  if (failures.length) throw Error(`${failures.length} missing review resources; see ${output}/report.json`);
  const live = new Set(Object.values(urls).map(path => path.split('/').at(-1)));
  // Retain prior content-addressed JSON snapshots: a CDN may still serve an
  // older manifest after a newer Git commit is published.
  const media = Object.fromEntries(records.map(record => [record.url, {
    sha256: record.sha256, bytes: record.bytes,
    extension: record.path.substring(record.path.lastIndexOf('.')),
    sources: resources.has(record.url) ? [...new Set([record.source, ...resourceCandidates(record.url)])] : [`${publicBase}/${record.path}`],
    roles: resources.get(record.url)?.roles ?? ['metadata'], stories: resources.get(record.url)?.stories ?? [record.url.match(/story_review_info\/([^/]+)\.json/)?.[1] ?? '__home'],
    ...(resources.get(record.url)?.sirenSongId ? {sirenSongId: resources.get(record.url).sirenSongId} : {}),
  }]));
  const revision = hash(JSON.stringify(Object.entries(media).sort(([a], [b]) => a.localeCompare(b)).map(([url, resource]) => [url, {...resource, sources: resource.sirenSongId ? [] : resource.sources}])));
  await writeFile(join(output, '..', 'review_manifest.json'), JSON.stringify({version: 1, revision, resources: media}));
  // Publish a remote manifest and content-addressed catalog; App packages carry neither.

  const packagedBytes = [...unique.values()].filter(x => live.has(x.path.split('/').at(-1)))
    .reduce((sum, x) => sum + x.bytes, 0);
  console.log(`Prepared ${stories} stories, ${(report.bytes / 1048576).toFixed(1)} MiB of downloadable resources; published catalog ${(packagedBytes / 1048576).toFixed(2)} MiB`);
  return report;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const option = key => process.argv.find(x => x.startsWith(`--${key}=`))?.split('=').slice(1).join('=');
  const dataDir = option('data-dir') ?? '.';
  await stat(dataDir); // CI explicitly checks out the desired data branch first.
  await buildReviewManifest({dataDir, locales: (option('locales') ?? 'zh_CN').split(','),
    refresh: process.argv.includes('--refresh'), publicBase: option('public-base') ?? 'https://raw.githubusercontent.com/KakkoiiSaber/arknights_story_data/main'});
}
