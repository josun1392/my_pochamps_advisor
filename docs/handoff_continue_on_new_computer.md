# Continue This Project On Another Computer

Use this when moving `pokemon-copilot` work to another machine.

## Repository

- GitHub repository: https://github.com/josun1392/my_pochamps_advisor
- Main working branch: `master`

## Setup On The New Computer

```powershell
git clone https://github.com/josun1392/my_pochamps_advisor.git
cd my_pochamps_advisor
uv sync --dev
cd tools/smogon_bridge
npm install
cd ../..
```

Create local environment secrets manually. The original local file is intentionally not tracked:

```powershell
New-Item -ItemType Directory -Force config
notepad config\.env
```

Add the Gemini or Vertex AI settings you use locally. Do not commit `config/.env`.

## Quick Verification

```powershell
uv run pytest
uv run python scripts/verify_champions_roster.py
uv run python scripts/verify_damage_engine.py
```

If parity checks are needed:

```powershell
uv run python scripts/verify_parity_bridge.py
uv run pytest tests/test_parity_bridge.py -v
```

## Prompt For Codex

```text
이 저장소는 `pokemon-copilot` 프로젝트입니다. 나는 다른 컴퓨터에서 작업을 이어가고 있습니다.

현재 목표:
- 기존 구조와 테스트 스타일을 유지하면서 작업을 이어가 주세요.
- 먼저 `README.md`, `docs/PROGRESS.md`, `docs/handoff_next_session_prompt_v1.9.md`, 그리고 최근 git log를 읽고 현재 상태를 파악해 주세요.
- `config/.env`는 로컬 전용 비밀 파일이라 GitHub에 없습니다. Gemini/Vertex AI 관련 값이 필요하면 내가 직접 넣을 수 있게 필요한 변수명만 알려주세요.
- 변경 전에는 `git status -sb`로 작업트리를 확인하고, 변경 후에는 가능한 범위에서 `uv run pytest` 또는 관련 단일 테스트를 실행해 주세요.
- 런타임 로그나 캐시 파일은 꼭 필요한 경우가 아니면 기능 변경 커밋에 섞지 말아 주세요.

프로젝트 실행/검증 기본 명령:
- `uv sync --dev`
- `uv run pytest`
- `uv run python scripts/verify_damage_engine.py`
- Smogon bridge가 필요하면 `cd tools/smogon_bridge; npm install; cd ../..` 후 `uv run python scripts/verify_parity_bridge.py`

이제 현재 저장소 상태를 읽고, 다음으로 해야 할 작업을 제안한 뒤 바로 진행해 주세요.
```
