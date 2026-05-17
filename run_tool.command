#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Double-clicked shells often do not load conda. Make the `conda` command
# available so mfa_tool.py can run `conda run -n mfa mfa` if `mfa` is not on PATH.
if ! command -v conda >/dev/null 2>&1; then
  for conda_sh in \
    "$HOME/miniconda3/etc/profile.d/conda.sh" \
    "$HOME/anaconda3/etc/profile.d/conda.sh" \
    "$HOME/mambaforge/etc/profile.d/conda.sh" \
    "$HOME/miniforge3/etc/profile.d/conda.sh" \
    "/opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh" \
    "/opt/anaconda3/etc/profile.d/conda.sh" \
    "/opt/miniconda3/etc/profile.d/conda.sh"; do
    if [ -f "$conda_sh" ]; then
      # shellcheck disable=SC1090
      source "$conda_sh"
      break
    fi
  done
fi

python3 -m pip install -r requirements.txt
python3 mfa_tool.py "$@"
echo
echo "完成。最终 TextGrid 在 result 文件夹中。"
read -n 1 -s -r -p "按任意键关闭窗口..."
echo
