# Runner 


## Initial Setup
```bash
brew install miniconda
git clone https://github.com/facebookresearch/testgeneval gitrepo
cd gitrepo && git checkout 67ea3ff37643b3078413d6e4fadaae00ce8d9e5d && cd ..
cp *.patch gitrepo/. && cd gitrepo && git apply *.patch && rm *.patch && cd ..

conda run -n testgeneval python -m pip install --upgrade "datasets>=2.19.0"
conda env create -f environment-mac.yaml
conda activate testgeneval
```

- environment variables
```bash
export PYTHONPATH="$PWD/gitrepo:$PYTHONPATH"
export SWEBENCH_DOCKER_FORK_DIR="$PWD/gitrepo"
```

### Test
```bash
PYTHONPATH="$PWD/gitrepo:$PYTHONPATH" \
SWEBENCH_DOCKER_FORK_DIR="$PWD/gitrepo" \
conda run -n testgeneval python test.py
```


## To run the server
- Navigate to src/runner then run:
```bash
PYTHONPATH="$PWD/gitrepo:$PYTHONPATH" \
SWEBENCH_DOCKER_FORK_DIR="$PWD/gitrepo" \
conda run -n testgeneval python server.py
```