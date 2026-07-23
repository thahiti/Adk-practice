# ADK Orchestration Lab — 자주 쓰는 실행 단축
#
# adk eval 은 에이전트 경로·eval 파일·config 를 모두 인자로 요구하고
# 자동 탐색을 하지 않으므로, 긴 명령을 여기에 한 번만 적어 둔다.
#
# 사용법:
#   make eval        # react 모드 (.env 기본값)
#   make eval-plan   # plan_execute 모드로 override
#   make eval-ci     # 4회 평균 통계 실행 (pytest 경로)
#
# 모델 백엔드와 키는 .env 에서 읽는다 (MODEL_BACKEND=openai, OPENAI_API_KEY=...).

AGENT   := agents/orchestration_lab
SETS    := $(AGENT)/test_files/single_hop.test.json $(AGENT)/test_files/multi_hop.test.json
CONFIG  := $(AGENT)/test_files/test_config.json

.PHONY: eval eval-plan eval-ci

eval:
	uv run adk eval $(AGENT) $(SETS) --config_file_path $(CONFIG) --print_detailed_results

eval-plan:
	ORCHESTRATION_MODE=plan_execute $(MAKE) eval

eval-ci:
	uv run pytest -m requires_model -v
