#!/usr/bin/env bash
set -euo pipefail

task_dir="datasets/universal-paperclips/prestige"

required_files=(
  "LICENSE"
  "THIRD_PARTY_NOTICES.md"
  "datasets/universal-paperclips/dataset.toml"
  "$task_dir/task.toml"
  "$task_dir/instruction.md"
  "$task_dir/environment/Dockerfile"
  "$task_dir/environment/bin/browser"
  "$task_dir/environment/bin/browser_daemon.py"
  "$task_dir/environment/bin/game_server.py"
  "$task_dir/environment/bin/paperclips_mcp"
  "$task_dir/environment/bin/paperclips_verify.py"
  "$task_dir/environment/bin/start-paperclips"
  "$task_dir/environment/vendor/index2.html"
  "$task_dir/environment/vendor/main.js"
  "$task_dir/environment/vendor/projects.js"
  "$task_dir/tests/test.sh"
  "docs/index.html"
  "docs/leaderboard.json"
  "docs/leaderboard-versions.json"
  "scripts/update_leaderboard.py"
)

for path in "${required_files[@]}"; do
  if [ ! -f "$path" ]; then
    echo "missing required file: $path" >&2
    exit 1
  fi
done

python_files=(
  "$task_dir/environment/bin/browser"
  "$task_dir/environment/bin/browser_daemon.py"
  "$task_dir/environment/bin/game_server.py"
  "$task_dir/environment/bin/paperclips_mcp"
  "$task_dir/environment/bin/paperclips_verify.py"
  "$task_dir/tests/test_verifier.py"
)

for py_file in "${python_files[@]}"; do
  python3 -c "import ast, pathlib, sys; ast.parse(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))" "$py_file"
done

python3 -c "import ast, pathlib; ast.parse(pathlib.Path('scripts/update_leaderboard.py').read_text(encoding='utf-8'))"
python3 -c "import json, pathlib; data=json.loads(pathlib.Path('docs/leaderboard.json').read_text(encoding='utf-8')); assert data['benchmark']['task'] == 'universal-paperclips/prestige'; assert data['benchmark']['current_version'] == 'v1.1.1'; assert isinstance(data['entries'], list)"
python3 -c "import json, pathlib; data=json.loads(pathlib.Path('docs/leaderboard-versions.json').read_text(encoding='utf-8')); assert data.get('current_version') == 'v1.1.1'; assert isinstance(data.get('versions'), list)"

PYTHONDONTWRITEBYTECODE=1 bash scripts/run_verifier_fixtures.sh

actual_sha="$(shasum -a 256 /tmp/paperclips-master.tar.gz 2>/dev/null | awk '{print $1}' || true)"
expected_sha="1875c7fa64e55536af7e53dc91814a5be352afc8bf4a96d03b9db7a7f3c4d343"
if [ -n "$actual_sha" ] && [ "$actual_sha" != "$expected_sha" ]; then
  echo "vendored source archive checksum mismatch" >&2
  exit 1
fi

echo "local validation passed"
