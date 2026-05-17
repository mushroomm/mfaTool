#!/usr/bin/env python3
"""Generate a merged TextGrid with Hanzi, IPA, and pinyin tiers.

默认用 `AI52.TextGrid` 作为唯一输入，输出 `2.textgrid`。
如果输入文件里第二层还叫 `phones`，脚本也会自动识别为 IPA。
脚本内置了本批文本的汉字到拼音标签表，所以不需要 `1.textgrid`。
如果你确实有单独的拼音 TextGrid，也可以用 `--pinyin-input` 覆盖内置拼音表。
注意：脚本不会修改输入文件。

这个脚本只做“合并/对齐”：
- 保留 `words` 层原来的时间戳；
- 保留 `ipa_phones` 层原来的时间戳；
- 读取原有 `pinyin_phones` 层的拼音标签，但把拼音标签重新贴到 IPA 的时间边界上。

例如：`科 - kʰ o˥˥ - k e1`
- `kʰ` 和 `k` 的时间戳一致；
- `o˥˥` 和 `e1` 的时间戳一致。
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

INTERVAL_RE = re.compile(
    r"intervals \[(\d+)\]:\n"
    r"\s+xmin = ([0-9.]+) \n"
    r"\s+xmax = ([0-9.]+) \n"
    r"\s+text = \"([^\"]*)\""
)


PINYIN_LABELS_BY_TOKEN = {
    '1': ('1',),
    '2': ('2',),
    '7': ('7',),
    '9': ('9',),
    '一': ('y', 'i1'),
    '上': ('sh', 'ang4'),
    '下': ('x', 'ia4'),
    '不': ('b', 'u4'),
    '与': ('y', 'u3'),
    '业': ('y', 'e4'),
    '严': ('y', 'an2'),
    '个': ('g', 'e4'),
    '中': ('zh', 'ong1'),
    '为': ('w', 'ei4'),
    '丽': ('l', 'i4'),
    '举': ('j', 'u3'),
    '也': ('y', 'e3'),
    '了': ('l', 'e5'),
    '事': ('sh', 'i4'),
    '于': ('y', 'u2'),
    '互': ('h', 'u4'),
    '五': ('w', 'u3'),
    '交': ('j', 'iao1'),
    '产': ('ch', 'an3'),
    '人': ('r', 'en2'),
    '今': ('j', 'in1'),
    '他': ('t', 'a1'),
    '付': ('f', 'u4'),
    '代': ('d', 'ai4'),
    '以': ('y', 'i3'),
    '们': ('m', 'en5'),
    '件': ('j', 'ian4'),
    '价': ('j', 'ia4'),
    '企': ('q', 'i3'),
    '优': ('y', 'ou1'),
    '伙': ('h', 'uo3'),
    '会': ('h', 'ui4'),
    '伟': ('w', 'ei3'),
    '伤': ('sh', 'ang1'),
    '伴': ('b', 'an4'),
    '但': ('d', 'an4'),
    '作': ('z', 'uo4'),
    '保': ('b', 'ao3'),
    '信': ('x', 'in4'),
    '修': ('x', 'iu1'),
    '倒': ('d', 'ao4'),
    '做': ('z', 'uo4'),
    '健': ('j', 'ian4'),
    '傅': ('f', 'u4'),
    '充': ('ch', 'ong1'),
    '先': ('x', 'ian1'),
    '入': ('r', 'u4'),
    '全': ('q', 'uan2'),
    '公': ('g', 'ong1'),
    '关': ('g', 'uan1'),
    '具': ('j', 'u4'),
    '内': ('n', 'ei4'),
    '写': ('x', 'ie3'),
    '冬': ('d', 'ong1'),
    '准': ('zh', 'un3'),
    '出': ('ch', 'u1'),
    '击': ('j', 'i1'),
    '分': ('f', 'en1'),
    '切': ('q', 'ie4'),
    '列': ('l', 'ie4'),
    '初': ('ch', 'u1'),
    '利': ('l', 'i4'),
    '到': ('d', 'ao4'),
    '制': ('zh', 'i4'),
    '刻': ('k', 'e4'),
    '力': ('l', 'i4'),
    '加': ('j', 'ia1'),
    '务': ('w', 'u4'),
    '动': ('d', 'ong4'),
    '劳': ('l', 'ao2'),
    '勾': ('g', 'ou1'),
    '包': ('b', 'ao1'),
    '北': ('b', 'ei3'),
    '区': ('q', 'u1'),
    '医': ('y', 'i1'),
    '十': ('sh', 'i2'),
    '华': ('h', 'ua2'),
    '卖': ('m', 'ai4'),
    '即': ('j', 'i2'),
    '历': ('l', 'i4'),
    '厉': ('l', 'i4'),
    '去': ('q', 'u4'),
    '参': ('c', 'an1'),
    '及': ('j', 'i2'),
    '双': ('sh', 'uang1'),
    '发': ('f', 'a1'),
    '取': ('q', 'u3'),
    '受': ('sh', 'ou4'),
    '变': ('b', 'ian4'),
    '口': ('k', 'ou3'),
    '只': ('zh', 'i3'),
    '可': ('k', 'e3'),
    '史': ('sh', 'i3'),
    '号': ('h', 'ao4'),
    '司': ('s', 'i1'),
    '各': ('g', 'e4'),
    '合': ('h', 'e2'),
    '后': ('h', 'ou4'),
    '启': ('q', 'i3'),
    '员': ('y', 'uan2'),
    '味': ('w', 'ei4'),
    '命': ('m', 'ing4'),
    '和': ('h', 'e2'),
    '品': ('p', 'in3'),
    '哥': ('g', 'e1'),
    '善': ('sh', 'an4'),
    '嚼': ('j', 'ue2'),
    '回': ('h', 'ui2'),
    '国': ('g', 'uo2'),
    '图': ('t', 'u2'),
    '在': ('z', 'ai4'),
    '场': ('ch', 'ang3'),
    '垂': ('ch', 'ui2'),
    '域': ('y', 'u4'),
    '墨': ('m', 'o4'),
    '处': ('ch', 'u4'),
    '备': ('b', 'ei4'),
    '复': ('f', 'u4'),
    '外': ('w', 'ai4'),
    '多': ('d', 'uo1'),
    '够': ('g', 'ou4'),
    '大': ('d', 'a4'),
    '天': ('t', 'ian1'),
    '好': ('h', 'ao3'),
    '嫌': ('x', 'ian2'),
    '学': ('x', 'ue2'),
    '安': ('an1',),
    '定': ('d', 'ing4'),
    '宝': ('b', 'ao3'),
    '实': ('sh', 'i2'),
    '审': ('sh', 'en3'),
    '家': ('j', 'ia1'),
    '容': ('r', 'ong2'),
    '察': ('ch', 'a2'),
    '寡': ('g', 'ua3'),
    '寸': ('c', 'un4'),
    '对': ('d', 'ui4'),
    '导': ('d', 'ao3'),
    '将': ('j', 'iang1'),
    '小': ('x', 'iao3'),
    '就': ('j', 'iu4'),
    '尺': ('ch', 'i3'),
    '局': ('j', 'u2'),
    '工': ('g', 'ong1'),
    '巨': ('j', 'u4'),
    '差': ('ch', 'a4'),
    '市': ('sh', 'i4'),
    '师': ('sh', 'i1'),
    '带': ('d', 'ai4'),
    '平': ('p', 'ing2'),
    '年': ('n', 'ian2'),
    '广': ('g', 'uang3'),
    '店': ('d', 'ian4'),
    '府': ('f', 'u3'),
    '建': ('j', 'ian4'),
    '开': ('k', 'ai1'),
    '式': ('sh', 'i4'),
    '强': ('q', 'iang2'),
    '录': ('l', 'u4'),
    '很': ('h', 'en3'),
    '得': ('d', 'e2'),
    '心': ('x', 'in1'),
    '快': ('k', 'uai4'),
    '忽': ('h', 'u1'),
    '怀': ('h', 'uai2'),
    '息': ('x', 'i1'),
    '恰': ('q', 'ia4'),
    '悲': ('b', 'ei1'),
    '惑': ('h', 'uo4'),
    '惠': ('h', 'ui4'),
    '成': ('ch', 'eng2'),
    '或': ('h', 'uo4'),
    '户': ('h', 'u4'),
    '手': ('sh', 'ou3'),
    '才': ('c', 'ai2'),
    '打': ('d', 'a3'),
    '扭': ('n', 'iu3'),
    '把': ('b', 'a3'),
    '投': ('t', 'ou2'),
    '报': ('b', 'ao4'),
    '抵': ('d', 'i3'),
    '拥': ('y', 'ong1'),
    '持': ('ch', 'i2'),
    '据': ('j', 'u4'),
    '捷': ('j', 'ie2'),
    '接': ('j', 'ie1'),
    '推': ('t', 'ui1'),
    '措': ('c', 'uo4'),
    '提': ('t', 'i2'),
    '揭': ('j', 'ie1'),
    '搏': ('b', 'o2'),
    '摔': ('sh', 'uai1'),
    '播': ('b', 'o1'),
    '支': ('zh', 'i1'),
    '改': ('g', 'ai3'),
    '放': ('f', 'ang4'),
    '政': ('zh', 'eng4'),
    '故': ('g', 'u4'),
    '效': ('x', 'iao4'),
    '教': ('j', 'iao4'),
    '数': ('sh', 'u4'),
    '整': ('zh', 'eng3'),
    '文': ('w', 'en2'),
    '新': ('x', 'in1'),
    '方': ('f', 'ang1'),
    '无': ('w', 'u2'),
    '日': ('r', 'i4'),
    '旧': ('j', 'iu4'),
    '时': ('sh', 'i2'),
    '明': ('m', 'ing2'),
    '春': ('ch', 'un1'),
    '是': ('sh', 'i4'),
    '普': ('p', 'u3'),
    '暖': ('n', 'uan3'),
    '更': ('g', 'eng4'),
    '最': ('z', 'ui4'),
    '有': ('y', 'ou3'),
    '期': ('q', 'i1'),
    '未': ('w', 'ei4'),
    '术': ('sh', 'u4'),
    '朵': ('d', 'uo3'),
    '机': ('j', 'i1'),
    '杂': ('z', 'a2'),
    '权': ('q', 'uan2'),
    '条': ('t', 'iao2'),
    '来': ('l', 'ai2'),
    '果': ('g', 'uo3'),
    '查': ('ch', 'a2'),
    '标': ('b', 'iao1'),
    '校': ('x', 'iao4'),
    '案': ('an4',),
    '模': ('m', 'o2'),
    '款': ('k', 'uan3'),
    '歌': ('g', 'e1'),
    '正': ('zh', 'eng4'),
    '步': ('b', 'u4'),
    '比': ('b', 'i3'),
    '民': ('m', 'in2'),
    '水': ('sh', 'ui3'),
    '求': ('q', 'iu2'),
    '沙': ('sh', 'a1'),
    '法': ('f', 'a3'),
    '活': ('h', 'uo2'),
    '润': ('r', 'un4'),
    '满': ('m', 'an3'),
    '炭': ('t', 'an4'),
    '点': ('d', 'ian3'),
    '然': ('r', 'an2'),
    '煤': ('m', 'ei2'),
    '熟': ('sh', 'u2'),
    '牙': ('y', 'a2'),
    '特': ('t', 'e4'),
    '率': ('l', 'v4'),
    '现': ('x', 'ian4'),
    '珠': ('zh', 'u1'),
    '班': ('b', 'an1'),
    '球': ('q', 'iu2'),
    '瓜': ('g', 'ua1'),
    '生': ('sh', 'eng1'),
    '用': ('y', 'ong4'),
    '甩': ('sh', 'uai3'),
    '画': ('h', 'ua4'),
    '留': ('l', 'iu2'),
    '疑': ('y', 'i2'),
    '的': ('d', 'e5'),
    '益': ('y', 'i4'),
    '监': ('j', 'ian1'),
    '盒': ('h', 'e2'),
    '盛': ('sh', 'eng4'),
    '直': ('zh', 'i2'),
    '相': ('x', 'iang1'),
    '知': ('zh', 'i1'),
    '社': ('sh', 'e4'),
    '种': ('zh', 'ong3'),
    '科': ('k', 'e1'),
    '称': ('ch', 'eng1'),
    '程': ('ch', 'eng2'),
    '立': ('l', 'i4'),
    '站': ('zh', 'an4'),
    '等': ('d', 'eng3'),
    '策': ('c', 'e4'),
    '算': ('s', 'uan4'),
    '篮': ('l', 'an2'),
    '系': ('x', 'i4'),
    '紫': ('z', 'i3'),
    '级': ('j', 'i2'),
    '纳': ('n', 'a4'),
    '练': ('l', 'ian4'),
    '绩': ('j', 'i1'),
    '缺': ('q', 'ue1'),
    '网': ('w', 'ang3'),
    '罪': ('z', 'ui4'),
    '美': ('m', 'ei3'),
    '老': ('l', 'ao3'),
    '者': ('zh', 'e3'),
    '聊': ('l', 'iao2'),
    '联': ('l', 'ian2'),
    '能': ('n', 'eng2'),
    '脱': ('t', 'uo1'),
    '自': ('z', 'i4'),
    '至': ('zh', 'i4'),
    '色': ('s', 'e4'),
    '艺': ('y', 'i4'),
    '节': ('j', 'ie2'),
    '花': ('h', 'ua1'),
    '获': ('h', 'uo4'),
    '菜': ('c', 'ai4'),
    '萄': ('t', 'ao2'),
    '落': ('l', 'uo4'),
    '葡': ('p', 'u2'),
    '血': ('x', 'ue4'),
    '行': ('x', 'ing2'),
    '表': ('b', 'iao3'),
    '西': ('x', 'i1'),
    '要': ('y', 'ao4'),
    '观': ('g', 'uan1'),
    '规': ('g', 'ui1'),
    '视': ('sh', 'i4'),
    '解': ('j', 'ie3'),
    '言': ('y', 'an2'),
    '警': ('j', 'ing3'),
    '计': ('j', 'i4'),
    '认': ('r', 'en4'),
    '让': ('r', 'ang4'),
    '训': ('x', 'un4'),
    '记': ('j', 'i4'),
    '讲': ('j', 'iang3'),
    '许': ('x', 'u3'),
    '论': ('l', 'un4'),
    '证': ('zh', 'eng4'),
    '识': ('sh', 'i2'),
    '诉': ('s', 'u4'),
    '语': ('y', 'u3'),
    '诱': ('y', 'ou4'),
    '读': ('d', 'u2'),
    '课': ('k', 'e4'),
    '调': ('d', 'iao4'),
    '象': ('x', 'iang4'),
    '负': ('f', 'u4'),
    '财': ('c', 'ai2'),
    '质': ('zh', 'i4'),
    '购': ('g', 'ou4'),
    '资': ('z', 'i1'),
    '赛': ('s', 'ai4'),
    '起': ('q', 'i3'),
    '足': ('z', 'u2'),
    '跑': ('p', 'ao3'),
    '跳': ('t', 'iao4'),
    '轮': ('l', 'un2'),
    '辩': ('b', 'ian4'),
    '达': ('d', 'a2'),
    '迅': ('x', 'un4'),
    '迎': ('y', 'ing2'),
    '还': ('h', 'ai2'),
    '这': ('zh', 'e4'),
    '进': ('j', 'in4'),
    '违': ('w', 'ei2'),
    '述': ('sh', 'u4'),
    '追': ('zh', 'ui1'),
    '送': ('s', 'ong4'),
    '通': ('t', 'ong1'),
    '速': ('s', 'u4'),
    '造': ('z', 'ao4'),
    '道': ('d', 'ao4'),
    '那': ('n', 'a4'),
    '部': ('b', 'u4'),
    '郭': ('g', 'uo1'),
    '里': ('l', 'i3'),
    '重': ('zh', 'ong4'),
    '长': ('zh', 'ang3'),
    '门': ('m', 'en2'),
    '问': ('w', 'en4'),
    '间': ('j', 'ian1'),
    '阅': ('y', 'ue4'),
    '际': ('j', 'i4'),
    '院': ('y', 'uan4'),
    '障': ('zh', 'ang4'),
    '雅': ('y', 'a3'),
    '需': ('x', 'u1'),
    '面': ('m', 'ian4'),
    '项': ('x', 'iang4'),
    '预': ('y', 'u4'),
    '题': ('t', 'i2'),
    '风': ('f', 'eng1'),
    '首': ('sh', 'ou3'),
    '高': ('g', 'ao1'),
    '黄': ('h', 'uang2'),
}


def tier_block(text: str, *names: str) -> str:
    """Return the full TextGrid item block for the first matching IntervalTier name."""
    for name in names:
        match = re.search(
            r"    item \[\d+\]:\n"
            r"        class = \"IntervalTier\" \n"
            rf"        name = \"{re.escape(name)}\".*?"
            r"(?=\n    item \[\d+\]:|\Z)",
            text,
            re.S,
        )
        if match:
            return match.group(0)
    wanted = " or ".join(names)
    available = ", ".join(re.findall(r'name = "([^"]+)"', text)) or "none"
    raise ValueError(f"Missing tier: {wanted}. Available tiers: {available}")


def parse_intervals(block: str) -> list[dict[str, object]]:
    """Parse intervals and keep both original timestamp strings and float values."""
    intervals = []
    for interval_no, xmin, xmax, label in INTERVAL_RE.findall(block):
        intervals.append(
            {
                "i": int(interval_no),
                "xmin": xmin,
                "xmax": xmax,
                "text": label,
                "fxmin": float(xmin),
                "fxmax": float(xmax),
            }
        )
    return intervals


def intervals_inside(
    intervals: list[dict[str, object]],
    xmin: float,
    xmax: float,
    *,
    eps: float = 1e-6,
) -> list[dict[str, object]]:
    """Return non-empty intervals fully inside a word interval."""
    return [
        interval
        for interval in intervals
        if interval["text"]
        and float(interval["fxmin"]) >= xmin - eps
        and float(interval["fxmax"]) <= xmax + eps
    ]


def aligned_pinyin_intervals(
    words: list[dict[str, object]],
    ipa: list[dict[str, object]],
    old_pinyin: list[dict[str, object]],
) -> list[tuple[str, str, str]]:
    """Move pinyin labels onto IPA timestamps without changing word/IPA timings."""
    new_pinyin: list[tuple[str, str, str]] = []

    for word in words:
        word_xmin = float(word["fxmin"])
        word_xmax = float(word["fxmax"])
        word_label = str(word["text"])

        if not word_label:
            new_pinyin.append((str(word["xmin"]), str(word["xmax"]), ""))
            continue

        ipa_parts = intervals_inside(ipa, word_xmin, word_xmax)
        pinyin_parts = intervals_inside(old_pinyin, word_xmin, word_xmax)
        pinyin_labels = [str(part["text"]) for part in pinyin_parts]

        if not pinyin_labels:
            # Keep the tier continuous even if a word has no pinyin label.
            new_pinyin.append((str(word["xmin"]), str(word["xmax"]), ""))
        elif not ipa_parts:
            # Non-pronunciation tokens such as digits: keep word-level timestamps.
            new_pinyin.append((str(word["xmin"]), str(word["xmax"]), " ".join(pinyin_labels)))
        elif len(pinyin_labels) == 1:
            # One pinyin label covers all IPA phones for this word.
            new_pinyin.append(
                (str(ipa_parts[0]["xmin"]), str(ipa_parts[-1]["xmax"]), pinyin_labels[0])
            )
        elif len(ipa_parts) == 1:
            # Orthographic zero-initial y/w plus final can map to a single IPA segment.
            new_pinyin.append(
                (str(ipa_parts[0]["xmin"]), str(ipa_parts[0]["xmax"]), " ".join(pinyin_labels))
            )
        else:
            # Initial uses the first IPA phone timestamp; final covers the remaining IPA span.
            # If there are more than two pinyin labels, leading labels map one-to-one and
            # the final label covers all remaining IPA phones.
            leading_count = min(len(pinyin_labels) - 1, len(ipa_parts) - 1)
            for index in range(leading_count):
                new_pinyin.append(
                    (
                        str(ipa_parts[index]["xmin"]),
                        str(ipa_parts[index]["xmax"]),
                        pinyin_labels[index],
                    )
                )
            new_pinyin.append(
                (
                    str(ipa_parts[leading_count]["xmin"]),
                    str(ipa_parts[-1]["xmax"]),
                    " ".join(pinyin_labels[leading_count:]),
                )
            )

    return new_pinyin


def normalize_item(block: str, item_no: int, name: str | None = None) -> str:
    """Set the TextGrid item number and optionally normalize the tier name."""
    block = re.sub(r"^    item \[\d+\]:", f"    item [{item_no}]:", block, count=1, flags=re.M)
    if name is not None:
        block = re.sub(r'name = "[^"]+"', f'name = "{name}"', block, count=1)
    return block


def format_tier(item_no: int, name: str, xmax: str, intervals: list[tuple[str, str, str]]) -> str:
    """Format intervals as a Praat IntervalTier."""
    lines = [
        f"    item [{item_no}]:",
        '        class = "IntervalTier" ',
        f'        name = "{name}" ',
        "        xmin = 0 ",
        f"        xmax = {xmax} ",
        f"        intervals: size = {len(intervals)} ",
    ]
    for index, (xmin, interval_xmax, label) in enumerate(intervals, 1):
        lines.extend(
            [
                f"        intervals [{index}]:",
                f"            xmin = {xmin} ",
                f"            xmax = {interval_xmax} ",
                f'            text = "{label}" ',
            ]
        )
    return "\n".join(lines)


def pinyin_intervals_from_words(words: list[dict[str, object]]) -> list[dict[str, object]]:
    """Build pinyin-label intervals from the built-in token mapping."""
    intervals: list[dict[str, object]] = []
    for word in words:
        word_label = str(word["text"])
        if not word_label:
            continue
        labels = PINYIN_LABELS_BY_TOKEN.get(word_label)
        if labels is None:
            raise ValueError(
                f"No built-in pinyin labels for token {word_label!r}. "
                "Pass --pinyin-input PATH with a pinyin_phones tier to provide labels."
            )
        xmin = float(word["fxmin"])
        xmax = float(word["fxmax"])
        step = (xmax - xmin) / len(labels)
        for index, label in enumerate(labels):
            part_xmin = xmin + step * index
            part_xmax = xmax if index == len(labels) - 1 else xmin + step * (index + 1)
            intervals.append(
                {
                    "i": len(intervals) + 1,
                    "xmin": f"{part_xmin:.6f}".rstrip("0").rstrip("."),
                    "xmax": f"{part_xmax:.6f}".rstrip("0").rstrip("."),
                    "text": label,
                    "fxmin": part_xmin,
                    "fxmax": part_xmax,
                }
            )
    return intervals


def generate(input_path: Path, output_path: Path, pinyin_input_path: Path | None = None) -> None:
    """Generate the merged TextGrid file."""
    text = input_path.read_text(encoding="utf-8")

    words_block = tier_block(text, "words")
    ipa_block = tier_block(text, "ipa_phones", "phones")

    words = parse_intervals(words_block)
    ipa = parse_intervals(ipa_block)

    if pinyin_input_path is None:
        try:
            old_pinyin = parse_intervals(tier_block(text, "pinyin_phones"))
        except ValueError:
            old_pinyin = pinyin_intervals_from_words(words)
    else:
        pinyin_text = pinyin_input_path.read_text(encoding="utf-8")
        old_pinyin = parse_intervals(tier_block(pinyin_text, "pinyin_phones", "phones"))
    new_pinyin = aligned_pinyin_intervals(words, ipa, old_pinyin)

    header = text.split("    item [1]:", 1)[0]
    header = re.sub(r"size = \d+ ", "size = 3 ", header, count=1)
    xmax_match = re.search(r"xmax = ([0-9.]+) ", header)
    if not xmax_match:
        raise ValueError("Missing TextGrid xmax in header")
    xmax = xmax_match.group(1)

    output = (
        header
        + normalize_item(words_block, 1, "words").rstrip()
        + "\n"
        + normalize_item(ipa_block, 2, "ipa_phones").rstrip()
        + "\n"
        + format_tier(3, "pinyin_phones", xmax, new_pinyin)
        + "\n"
    )
    output_path.write_text(output, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a TextGrid whose pinyin tier uses the same timestamps as the IPA tier."
    )
    parser.add_argument("input", nargs="?", default="AI52.TextGrid", help="Input IPA TextGrid path")
    parser.add_argument("output", nargs="?", default="2.textgrid", help="Output TextGrid path")
    parser.add_argument(
        "--pinyin-input",
        help=(
            "Optional TextGrid path to read pinyin labels from. If omitted, the script "
            "first looks for pinyin_phones in the input file, then falls back to "
            "the built-in token-to-pinyin table."
        ),
    )
    args = parser.parse_args()

    generate(
        Path(args.input),
        Path(args.output),
        Path(args.pinyin_input) if args.pinyin_input else None,
    )


if __name__ == "__main__":
    main()
