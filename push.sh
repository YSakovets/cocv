#!/usr/bin/env bash
# Run from inside the unpacked cocv folder:  bash push.sh YOUR_GITHUB_USERNAME
set -e
USER="${1:?usage: bash push.sh YOUR_GITHUB_USERNAME}"

# 1. Put your GitHub username into the two files that reference the repo URL
sed -i.bak "s#GITHUB_USERNAME#${USER}#g" CITATION.cff README.md && rm -f CITATION.cff.bak README.md.bak

# 2. Make sure everything still passes
python3 -m pip install -e ".[dev]" -q --break-system-packages 2>/dev/null || python3 -m pip install -e ".[dev]" -q
python3 -m pytest -q

# 3. First commit with your personal identity
git init -q
git config user.name "Yevheniia Sakovets"
git config user.email "yevheniia.sakovets@gmail.com"
git add -A
git commit -q -m "CoCV 0.1: methodology, reference implementation, synthetic service, tests"
git branch -M main

# 4. Push to the empty repository you created on GitHub
git remote add origin "https://github.com/${USER}/cocv.git"
git push -u origin main

echo
echo "Pushed. Open https://github.com/${USER}/cocv and check that README renders and Actions is running."
