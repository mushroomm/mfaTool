# MFA TextGrid 一键工具

这个小工具把你的分步流程整合成一个命令/双击入口：

1. 读取 `audio/` 里的音频或视频文件，用 Whisper 转写。
2. 去除标点和空白，并把每个字用空格分隔，写成同名 `.txt`。
3. 对视频/压缩音频自动生成 MFA 可用的同名 `.wav`，并生成同名初始 `.TextGrid`。
4. 调用 `mfa align` 做强制对齐，原始结果写入 `output/`。
5. 把 MFA 输出的 TextGrid 转成带 `pinyin_phones` 的最终 TextGrid，写入 `result/`。

## 准备工作

请先确保已经安装：

- Python 3.10+
- Montreal Forced Aligner；如果你平时需要 `conda activate mfa` 才能运行 `mfa`，工具会自动尝试 `conda run -n mfa mfa`
- ffmpeg/ffprobe（推荐；视频或压缩音频转 wav 时需要）

Python 依赖可以用下面命令安装：

```bash
python3 -m pip install -r requirements.txt
```

## 点开即用

### macOS

把音频/视频放进 `audio/` 文件夹，然后双击：

```text
run_tool.command
```

### Windows

把音频/视频放进 `audio/` 文件夹，然后双击：

```text
run_tool.bat
```

## 命令行用法

默认直接运行：

```bash
python3 mfa_tool.py
```

常用参数：

```bash
# 覆盖已有 txt/TextGrid/result
python3 mfa_tool.py --force

# 使用更快但精度较低的 Whisper 模型
python3 mfa_tool.py --whisper-model base

# 已经有 txt 了，跳过 Whisper
python3 mfa_tool.py --skip-whisper

# 只把已有 output/ 里的 MFA TextGrid 转到 result/
python3 mfa_tool.py --skip-whisper --skip-mfa

# 自定义路径
python3 mfa_tool.py \
  --audio-dir audio \
  --dictionary pretrained_models/dictionary/mandarin_china_mfa.dict \
  --acoustic-model pretrained_models/acoustic/mandarin_mfa.zip \
  --output-dir output \
  --result-dir result
```


## MFA / conda 环境说明

如果你在普通终端里先运行下面命令后可以使用 MFA：

```bash
conda activate mfa
mfa version
```

但双击工具时报“找不到 mfa 命令”，这是因为双击打开的窗口通常没有自动激活 conda 环境。现在工具会按下面顺序寻找 MFA：

1. 直接找当前 PATH 里的 `mfa`。
2. 如果找不到，默认尝试 `conda run -n mfa mfa`。
3. 如果你的 conda 环境不叫 `mfa`，可以这样指定：

```bash
python3 mfa_tool.py --mfa-conda-env 你的环境名
```

也可以指定 MFA 可执行文件的完整路径：

```bash
python3 mfa_tool.py --mfa-command /Users/你的用户名/miniconda3/envs/mfa/bin/mfa
```

macOS 双击 `run_tool.command` 时，脚本也会尝试加载常见位置的 conda 初始化脚本，让 `conda run -n mfa mfa` 可用。

## 目录说明

- `audio/`：输入音视频，以及中间的 `.txt`、初始 `.TextGrid`。
- `output/`：MFA 的原始对齐 TextGrid。
- `result/`：最终 TextGrid。
- `pretrained_models/`：词典和声学模型，默认使用：
  - `pretrained_models/dictionary/mandarin_china_mfa.dict`
  - `pretrained_models/acoustic/mandarin_mfa.zip`

## 需要你确认/安装的东西

如果运行失败，最常见原因是：

1. 电脑上没有安装 MFA，或者 conda 环境名不是默认的 `mfa`。
2. 没有安装 ffmpeg/ffprobe。
3. 首次运行 Whisper 需要下载模型，网络可能较慢。
4. Whisper 识别出的字不在词典里，MFA 可能报 OOV；这时需要扩充/替换词典。
