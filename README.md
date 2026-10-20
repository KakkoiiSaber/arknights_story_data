# Arknights story data

## 联动活动主题补充

`assets/stage_table_complement.json` 是主题资源补充的维护入口。
`src/review.py` 会将其合并进生成的 `story_meta_table.json`、
`story_review_info/*.json` 和 `audio_data.json`。有补充信息的活动会绕过剧情缓存，
因此更新 complement 不需要手动删除整个缓存。`servers` 限制适用语言；
本次 8 个联动条目的中文图片只应用于 `zh_CN`。

| 活动 | 封面来源 | 说明 |
| --- | --- | --- |
| 源石尘行动 | 复刻原始活动入口图 | 主界面背景、Logo 使用复刻同主题素材 |
| 水晶箭行动 | 原始活动入口图 | 标题头图使用原始活动入口横幅 |
| 无忧梦呓 | 原始活动入口图 | 保留原有 `storybg_ave_mujica.png`、`music_bg_avemujica` |
| 月行水上 | 原始活动入口图 | 背景为主界面静态底图，不包含分层动画 |
| 落叶逐火 | 复刻原始活动入口图 | 未找到剧情回顾专用缩略图；背景由左右两幅拼接 |
| 泰拉饭 | 原始活动入口图 | 未找到剧情回顾专用缩略图；配乐为官方《雀跃的炉火》音源 |
| 泡影苍霆 | 原始活动入口图 | 未找到剧情回顾专用缩略图 |
| 好久不见 | 官方活动宣传图的 PRTS 存档 | 未找到剧情回顾专用缩略图；配乐为首篇剧情实际使用的 path 音乐，未确认为独立活动主页 BGM |

封面展示统一选用活动原图，由消费端等比裁切铺满卡片。
源石尘行动、水晶箭行动、无忧梦呓、月行水上的原版剧情回顾缩略图已找到，
作为备选存放在对应条目的 `storyReviewImageUrl` 中，不用于当前首页展示。

剧情回顾封面实际位于 `arts/ui/storyreview/hubs/activity/`，并非普通活动使用的
`arts/ui/mixstory/kvs/`。部分联动不在资源仓库当前的剧情回顾目录中，所以不能通过
猜测 `kv_*` 文件名补齐。`coverSource` 区分 `story-review-entry`、`activity-entry`
与 `official-promotion`，具体来源见各条目的 `themeSources` / `themeNotes`。

字段约定：

- `kvImageId`、`titleImageId`、`backgroundId`：保留旧版文件名用法，也允许完整 HTTPS URL。
  消费端须通过 URI resolve 解析，不能直接拼接资源根路径。
- `backgroundUrls` / `backgroundAspectRatio`：横向拼接背景的有序图片及整体宽高比。
- `coverContainsTitle`：封面自带标题，消费端不要再次叠加 Logo。
- `titleIsBanner`：标题头图为完整入口横幅，并非透明 Logo。
- `gameMusicId`：游戏 `musics` 表中真实存在的 ID；不会为缺少 ID 的活动捏造标识。
- `gameMusicName`：没有音乐 ID 时，可以指定游戏 `bgmBanks` 中真实存在的 bank 名。
- `audio`：已验证可访问的 intro/loop URL 覆盖。生成时先解析真实 ID/bank，
  再替换媒体地址，保留 bank 名。没有剧情回顾主题音乐时使用 `musicRole: none` 与空音轨；不借用首篇剧情音乐。
- `musicRole`：`activity-theme` 为已配置的活动主题音乐，`none` 表示介绍页静音；旧版 `opening-story` 不再用于回顾页。

部分地址来自 ArknightsAssets/ArknightsAssets2，部分来自旧版 ArknightsAssets 仓库。
不要将它们改成当前 arkdata 根路径加文件名：文件实际不在同一目录。

仅刷新已生成文件中的主题字段、保留所有章节与简介：

```sh
python src/utils/refresh_complement.py --audio-data assets_origin/zh_CN/gamedata/excel/audio_data.json
python -m unittest discover -s tests -v
```

`--audio-data` 必须使用游戏原始音频映射表，不能传入本仓库生成的同名文件。
完整每日更新流程仍由 `.github/workflows/update.yml` 调用 `src/review.py`。


## App 首页与主题资源更新清单

Update Data Action 会在生成 review 数据后运行 `node scripts/review_manifest.mjs --refresh`，发布 `assets/review_manifest.json` 和 `assets/review_payload/files/*.json`。清单版本由元数据、素材 SHA-256 与分组生成；App 每次启动检查该版本，只下载本地缺少或校验值变更的文件。素材保持原始 CDN 来源，不提交图片和音频二进制文件。

JSON 快照使用内容寻址并保留旧版，以兼容 CDN 中尚未过期的旧清单。`audio.loopSongId` 可为塞壬音源指定曲目 ID，生成器和 App 会获取最新地址，签名变化不会误判为音频内容更新。

本地生成与测试：

```sh
node --test scripts/tests/review_manifest.test.mjs
node scripts/review_manifest.mjs --public-base=https://raw.githubusercontent.com/KakkoiiSaber/arknights_story_data/dev
```

`--refresh` 强制校验远端媒体的新内容；`--locales=zh_CN,en_US,ja_JP,ko_KR` 可扩展语言。缺失素材时生成失败，保留上一版可用清单，Action 不发布不完整的数据更新。
