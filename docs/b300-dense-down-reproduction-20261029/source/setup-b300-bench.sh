#!/usr/bin/env bash
set -euo pipefail
sudo apt-get -qq update
sudo apt-get -qq install -y python3.12-dev
mkdir -p /home/nebius/downproj-repro
cd /home/nebius/downproj-repro
python3 -m venv --without-pip venv
curl -fsSL --max-time 60 https://bootstrap.pypa.io/get-pip.py -o get-pip.py
venv/bin/python get-pip.py
venv/bin/python -m pip install --upgrade pip setuptools wheel ninja packaging
venv/bin/python -m pip install torch==2.11.0 --index-url https://download.pytorch.org/whl/cu130
venv/bin/python -m pip install apache-tvm-ffi==0.1.9 numpy
git clone https://github.com/sgl-project/DeepGEMM.git
git -C DeepGEMM checkout b4296edce3cd07e3b6392c8eb390cee9c41a6b70
git -C DeepGEMM submodule update --init --recursive
export PATH="$PWD/venv/bin:/usr/local/cuda/bin:$PATH"
export CUDA_HOME=/usr/local/cuda
export MAX_JOBS=8
venv/bin/python -m pip install --no-build-isolation ./DeepGEMM
venv/bin/python - <<'PY'
import torch
print('Torch',torch.__version__,'CUDA',torch.version.cuda)
print(torch.cuda.get_device_properties(0))
PY
