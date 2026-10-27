# touliu-script-matrix

v0.1 local CLI. It expands oral-script atoms into a 15-second script matrix and writes a gate report for length, hook collision, and near-duplicate copy.

This repository, [touliu-script-matrix-gate](https://github.com/zcf19980527-dot/touliu-script-matrix-gate), is that v0.1 release. No login, no posting, no cloud API.

```bash
python -m venv .venv && .venv/bin/python -m pip install -e ".[dev]" && .venv/bin/python -m touliu_script_matrix demo
```

Run that from the repository root. The sample atoms are supposed to fail the gate. `demo` still exits 0 after it writes:

- `examples/out/scripts.csv`
- `examples/out/report.md`

`check` uses the same writer and exits 1 when the gate fails, so you can put it in a script.

## Problem

Short commerce voiceovers are built from a few atoms: a hook, a selling point, an audience, a tone, a call to action, and a scene. The cartesian product looks like a large matrix, then you film twenty takes that are one sentence.

Before filming, you want two answers:

1. Does each line fit about 15 seconds (3s hook, 10s pitch, 2s CTA)?
2. Which hooks and full lines are already the same sentence?

`examples/atoms.yaml` is a generic mid-age and older commerce demo (a warm knee brace, 保暖护膝). It includes a one-comma hook pair, a one-word pitch pair, one pitch that is too long, and one pitch that is too short. The report comes back **FAIL** so you can see each gate fire.

## Why this is not Video Duplicate Finder or ClipForge

Video Duplicate Finder compares finished pictures and sound. It is useful after a video exists. It does not know that your unfilmed line is over 15 seconds, or that two hooks differ by a comma.

ClipForge is a clip and assembly tool. This repository stops at the script and the text gate. It does not cut, render, subtitle, or publish video.

## Non-goals / 非目标

- Account login, platform posting, scheduled ads, or multi-account workflows
- Cloud APIs and model rewrites
- Frame, audio, or finished-video duplicate detection
- Editing, subtitle burn-in, or footage download
- Passing the sample gate. The sample is written to fail

## Install and demo

Python 3.10+. From a clone of this repo:

```bash
python -m venv .venv && .venv/bin/python -m pip install -e ".[dev]" && .venv/bin/python -m touliu_script_matrix demo
```

Tests:

```bash
.venv/bin/python -m pytest
```

The console script `touliu-script-matrix` calls the same entry point.

## Commands

| Command | Writes | Exit |
| --- | --- | --- |
| `expand` | `scripts.csv` | 0 |
| `check` | `scripts.csv` and `report.md` | 0 pass, 1 gate fail |
| `demo` | `scripts.csv` and `report.md` | 0 after a successful write, including a FAIL report |

```bash
.venv/bin/python -m touliu_script_matrix expand --atoms examples/atoms.yaml --out examples/out
.venv/bin/python -m touliu_script_matrix check --atoms examples/atoms.yaml --out examples/out
.venv/bin/python -m touliu_script_matrix demo
```

`--limit` overrides the `limit` in the atom file. Paths are relative to the current directory. A missing atom file exits 2.

## Atom file

`examples/atoms.yaml` lists `hooks`, `selling_points`, `audiences`, `tones`, `ctas`, and `scenes`. Expansion order is stable and hooks vary fastest:

`tones × audiences × ctas × selling_points × scenes × hooks`

The sample limit is 60 out of 480 combinations. Those 60 include every hook, every scene, and every selling point, with the first CTA, audience, and tone. Put the lines you need to review at the top of each list.

Names look like `保暖护膝_卖点05_办公室_001`: product, selling-point label, scene label, and a 1-based index.

Each script is three spoken beats:

```text
前3s钩子：天一冷，膝盖就跟针扎一样？
中10s卖点：中老年朋友在办公室久坐，说句实在的，三层锁温，膝盖前后左右都包住，坐着一上午也不僵。
尾2s CTA：点下方，先看尺码再下单。
```

字数 counts the spoken line only. Labels and whitespace are not counted. Spoken Chinese is often around four characters a second, so the default band is 52–96 characters for about 15 seconds. That is a writing budget, not a timed voice render.

## Gates

Fingerprints use the standard library only. Each character shingle is hashed with `hashlib.blake2s` (8 bytes) and voted into a 64-bit SimHash. Jaccard uses the same shingles.

| Gate | Sample rule |
| --- | --- |
| Length | spoken 字数 outside 52–96 |
| Hook collision | two hook texts with Hamming ≤ 16 or Jaccard ≥ 0.45 |
| Hook reuse | one hook id used more than 24 times |
| Similar scripts | `pair_rule: both`, so Hamming ≤ 8 and Jaccard ≥ 0.90 |

`both` keeps a shared scene tag from flagging every pair. `either` flags a pair when one metric is over the line. The report lists thresholds, length failures, hook collisions, reuse, and the closest script pairs.

On this sample the gate fails with 24 length misses (the long 卖点07 and the short 卖点08), one hook collision (`h01` / `h02`), and the near-copy pairs (卖点05 against 卖点06, plus takes that only swap a short scene or a comma). 卖点05 against 卖点09 stays inside the similarity gate. Hook reuse stays under the cap.

## Layout

```text
src/touliu_script_matrix/   package and CLI
examples/atoms.yaml         sample atoms
examples/out/               demo output (generated, not committed)
tests/                      pytest
```

Runtime dependency: PyYAML. `pytest` is the optional `[dev]` extra.

## License

MIT. Copyright (c) 2026 zcf19980527-dot and contributors. See [LICENSE](LICENSE).

---

# touliu-script-matrix（中文）

v0.1 本地命令行。把口播原子展开成 15 秒脚本矩阵，并做字数、钩子碰撞、近复制三道门禁。

本仓库 [touliu-script-matrix-gate](https://github.com/zcf19980527-dot/touliu-script-matrix-gate) 就是这一版。不登录、不发布、不调用云端 API。

在仓库根目录执行：

```bash
python -m venv .venv && .venv/bin/python -m pip install -e ".[dev]" && .venv/bin/python -m touliu_script_matrix demo
```

示例原子故意过不了门禁。`demo` 写完文件后退出码仍是 0：

- `examples/out/scripts.csv`
- `examples/out/report.md`

`check` 同样写这两份文件；门禁失败时退出码为 1。

## 问题

电商口播通常是钩子、卖点、人群、语气、CTA、场景几类原子。笛卡尔积看起来很大，拍出来却可能是同一句话。

开拍前只需要两件事：

1. 每一条是否落在大约 15 秒里（前 3 秒钩子、中 10 秒卖点、尾 2 秒 CTA）。
2. 哪些钩子和整段口播其实已经撞车。

`examples/atoms.yaml` 是通用的中老年电商例子（保暖护膝）。里面放了一对只差一个逗号的钩子、一对几乎相同的卖点、一条过长卖点和一条过短卖点。报告应当是 **FAIL**。

## 为什么不是 Video Duplicate Finder，也不是 ClipForge

Video Duplicate Finder 比较的是已经做好的画面和声音，适合成片之后。它不知道还没拍的口播超了 15 秒，也不知道两个钩子只差一个逗号。

ClipForge 做的是切片和成片拼装。这个仓库停在脚本矩阵和文本门禁，不剪辑、不渲染、不压字幕、不发布。

## 非目标

- 账号登录、平台发布、定时投放、多账号操作
- 云端 API 和大模型改写
- 画面、音频或成片查重
- 剪辑、字幕烧录、素材下载
- 让示例原子通过门禁。示例就是用来失败的

## 安装与一条命令演示

需要 Python 3.10 及以上。克隆后在仓库根目录：

```bash
python -m venv .venv && .venv/bin/python -m pip install -e ".[dev]" && .venv/bin/python -m touliu_script_matrix demo
```

测试：

```bash
.venv/bin/python -m pytest
```

也可以调用控制台命令 `touliu-script-matrix`。

## 命令

| 命令 | 写出 | 退出码 |
| --- | --- | --- |
| `expand` | `scripts.csv` | 0 |
| `check` | `scripts.csv` 和 `report.md` | 通过 0，门禁失败 1 |
| `demo` | `scripts.csv` 和 `report.md` | 成功写文件为 0，报告为 FAIL 也是 0 |

```bash
.venv/bin/python -m touliu_script_matrix expand --atoms examples/atoms.yaml --out examples/out
.venv/bin/python -m touliu_script_matrix check --atoms examples/atoms.yaml --out examples/out
.venv/bin/python -m touliu_script_matrix demo
```

`--limit` 覆盖原子文件里的 `limit`。路径相对当前目录。找不到原子文件时退出码为 2。

## 原子文件

`examples/atoms.yaml` 包含 `hooks`、`selling_points`、`audiences`、`tones`、`ctas`、`scenes`。展开顺序固定，钩子变化最快：

`语气 × 人群 × CTA × 卖点 × 场景 × 钩子`

示例 `limit: 60`，完整组合是 480。这 60 条覆盖全部钩子、场景和卖点，以及文件里的第一个 CTA、人群和语气。要优先检查的句子，写在每一组的前面。

名字形如 `保暖护膝_卖点05_办公室_001`：产品、卖点标签、场景标签、从 1 开始的序号。

每条脚本三拍：

```text
前3s钩子：天一冷，膝盖就跟针扎一样？
中10s卖点：中老年朋友在办公室久坐，说句实在的，三层锁温，膝盖前后左右都包住，坐着一上午也不僵。
尾2s CTA：点下方，先看尺码再下单。
```

字数只算口播正文，不算栏目标签，不计空白。中文口播大约每秒四字，默认带宽 52–96 字，用来近似 15 秒。这是篇幅预算，不是语音合成测时。

## 门禁

指纹只用标准库。字 n-gram 用 `hashlib.blake2s`（8 字节）投成 64 位 SimHash。Jaccard 用同一组 shingle。

| 门禁 | 示例规则 |
| --- | --- |
| 字数 | 口播字数不在 52–96 |
| 钩子碰撞 | 两条钩子 Hamming ≤ 16，或 Jaccard ≥ 0.45 |
| 钩子复用 | 同一个钩子 id 出现超过 24 次 |
| 相似脚本 | `pair_rule: both`，即 Hamming ≤ 8 且 Jaccard ≥ 0.90 |

`both` 避免仅仅因为共用场景标签就把所有脚本对判失败。`either` 是两个指标里有一个越线就判失败。报告里有阈值、字数失败、钩子碰撞、复用和最接近的脚本对。

这份示例会失败：24 条字数越界（过长的卖点07、过短的卖点08）、一对钩子碰撞（`h01` / `h02`），以及近复制脚本对（卖点05 对 卖点06，再加上只换了很短场景或一个逗号的版本）。卖点05 对 卖点09 不会被相似度门禁拦下。钩子复用次数在上限以内。

## 目录

```text
src/touliu_script_matrix/   包和命令行
examples/atoms.yaml         示例原子
examples/out/               demo 输出（生成物，不提交）
tests/                      pytest
```

运行依赖 PyYAML。`pytest` 放在可选的 `[dev]` 里。

## 许可证

MIT。Copyright (c) 2026 zcf19980527-dot 与贡献者。见 [LICENSE](LICENSE)。
