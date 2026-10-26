# Complete source inventory

All 127 original file contents were compared between both archives. Binary assets were hashed; text files were decoded, Python modules parsed and JSON files validated. Original ZIPs remain unchanged.

| Original path | Bytes | Current disposition |
|---|---:|---|
| `.dockerignore` | 257 | Updated or replaced with the integrated implementation. |
| `.gitignore` | 217 | Updated or replaced with the integrated implementation. |
| `README.md` | 10700 | Updated or replaced with the integrated implementation. |
| `agents/__init__.py` | 0 | Retained package marker. |
| `agents/data_prep_agent/Dockerfile` | 377 | Updated or replaced with the integrated implementation. |
| `agents/data_prep_agent/README.md` | 6827 | Updated or replaced with the integrated implementation. |
| `agents/data_prep_agent/__init__.py` | 0 | Retained package marker. |
| `agents/data_prep_agent/agent.py` | 7681 | Updated or replaced with the integrated implementation. |
| `agents/data_prep_agent/code_generator.py` | 10966 | Updated or replaced with the integrated implementation. |
| `agents/data_prep_agent/container_entrypoint.py` | 3179 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `agents/data_prep_agent/notebook_runner.py` | 9379 | Updated or replaced with the integrated implementation. |
| `agents/data_prep_agent/operations.py` | 19012 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `agents/data_prep_agent/planner.py` | 9623 | Updated or replaced with the integrated implementation. |
| `agents/data_prep_agent/profiler.py` | 1231 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `agents/data_prep_agent/requirements.txt` | 92 | Updated or replaced with the integrated implementation. |
| `agents/eda_agent/Dockerfile` | 0 | Updated or replaced with the integrated implementation. |
| `agents/eda_agent/README.md` | 5809 | Updated or replaced with the integrated implementation. |
| `agents/eda_agent/__init__.py` | 0 | Retained package marker. |
| `agents/eda_agent/artifact_tools.py` | 964 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `agents/eda_agent/categorical_relationship_tools.py` | 5622 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `agents/eda_agent/chart_planning_tools.py` | 10634 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `agents/eda_agent/chart_rendering_tools.py` | 5379 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `agents/eda_agent/column_tools.py` | 8117 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `agents/eda_agent/csv_tools.py` | 4062 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `agents/eda_agent/distribution_tools.py` | 4561 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `agents/eda_agent/eda_tools.py` | 9508 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `agents/eda_agent/main.py` | 0 | Updated or replaced with the integrated implementation. |
| `agents/eda_agent/plotting_tools.py` | 26988 | Updated or replaced with the integrated implementation. |
| `agents/eda_agent/relationship_tools.py` | 8252 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `agents/eda_agent/requirements.txt` | 0 | Updated or replaced with the integrated implementation. |
| `agents/eda_agent/target_tools.py` | 6785 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `agents/eda_agent/time_tools.py` | 5878 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `agents/eval_report_agent/Dockerfile` | 0 | Updated or replaced with the integrated implementation. |
| `agents/eval_report_agent/README.md` | 7771 | Updated or replaced with the integrated implementation. |
| `agents/eval_report_agent/main.py` | 0 | Updated or replaced with the integrated implementation. |
| `agents/eval_report_agent/requirements.txt` | 0 | Updated or replaced with the integrated implementation. |
| `agents/feature_ml_agent/Dockerfile` | 0 | Updated or replaced with the integrated implementation. |
| `agents/feature_ml_agent/README.md` | 8698 | Updated or replaced with the integrated implementation. |
| `agents/feature_ml_agent/main.py` | 0 | Updated or replaced with the integrated implementation. |
| `agents/feature_ml_agent/requirements.txt` | 0 | Updated or replaced with the integrated implementation. |
| `agents/modeling/__init__.py` | 0 | Retained package marker. |
| `agents/modeling/evaluator.py` | 3311 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `agents/modeling/registry.py` | 1505 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `agents/modeling/trainer.py` | 7366 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `api/Dockerfile` | 0 | Updated or replaced with the integrated implementation. |
| `api/main.py` | 10549 | Updated or replaced with the integrated implementation. |
| `configs/modeling_plan.json` | 712 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `data/sample_orders.csv` | 137 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `frontend/.gitignore` | 253 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `frontend/README.md` | 1027 | Updated or replaced with the integrated implementation. |
| `frontend/eslint.config.js` | 568 | Updated or replaced with the integrated implementation. |
| `frontend/index.html` | 360 | Updated or replaced with the integrated implementation. |
| `frontend/package-lock.json` | 87078 | Updated or replaced with the integrated implementation. |
| `frontend/package.json` | 699 | Updated or replaced with the integrated implementation. |
| `frontend/public/favicon.svg` | 9522 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `frontend/public/icons.svg` | 5031 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `frontend/src/.env.example` | 39 | Replaced by the connected React studio and its shared API client. |
| `frontend/src/App.css` | 2891 | Replaced by the connected React studio and its shared API client. |
| `frontend/src/App.jsx` | 1351 | Replaced by the connected React studio and its shared API client. |
| `frontend/src/assets/hero.png` | 13057 | Replaced by the connected React studio and its shared API client. |
| `frontend/src/assets/react.svg` | 4126 | Replaced by the connected React studio and its shared API client. |
| `frontend/src/assets/vite.svg` | 8709 | Replaced by the connected React studio and its shared API client. |
| `frontend/src/components/agents/AgentDossier.jsx` | 1564 | Replaced by the connected React studio and its shared API client. |
| `frontend/src/components/agents/AgentNode.jsx` | 1225 | Replaced by the connected React studio and its shared API client. |
| `frontend/src/components/agents/ExecutionLogs.jsx` | 0 | Replaced by the connected React studio and its shared API client. |
| `frontend/src/components/agents/OrbitGraph.css` | 5412 | Replaced by the connected React studio and its shared API client. |
| `frontend/src/components/agents/OrbitGraph.jsx` | 1927 | Replaced by the connected React studio and its shared API client. |
| `frontend/src/components/common/StatusBadge.jsx` | 0 | Replaced by the connected React studio and its shared API client. |
| `frontend/src/components/dataset/DatasetForm.css` | 5321 | Replaced by the connected React studio and its shared API client. |
| `frontend/src/components/dataset/DatasetPreview.jsx` | 1844 | Replaced by the connected React studio and its shared API client. |
| `frontend/src/components/dataset/DatasetUpload.jsx` | 2693 | Replaced by the connected React studio and its shared API client. |
| `frontend/src/components/dataset/ProblemInput.jsx` | 1540 | Replaced by the connected React studio and its shared API client. |
| `frontend/src/components/layout/AppLayout.css` | 252 | Replaced by the connected React studio and its shared API client. |
| `frontend/src/components/layout/AppLayout.jsx` | 308 | Replaced by the connected React studio and its shared API client. |
| `frontend/src/components/layout/Sidebar.css` | 1246 | Replaced by the connected React studio and its shared API client. |
| `frontend/src/components/layout/Sidebar.jsx` | 1531 | Replaced by the connected React studio and its shared API client. |
| `frontend/src/constants/agentConfig.js` | 970 | Replaced by the connected React studio and its shared API client. |
| `frontend/src/constants/datasetConfig.js` | 559 | Replaced by the connected React studio and its shared API client. |
| `frontend/src/data/mockPipeline.js` | 2057 | Replaced by the connected React studio and its shared API client. |
| `frontend/src/index.css` | 2169 | Replaced by the connected React studio and its shared API client. |
| `frontend/src/main.jsx` | 377 | Updated or replaced with the integrated implementation. |
| `frontend/src/pages/ExperimentsPage.jsx` | 343 | Replaced by the connected React studio and its shared API client. |
| `frontend/src/pages/HistoryPage.jsx` | 332 | Replaced by the connected React studio and its shared API client. |
| `frontend/src/pages/LivePipelinePage.jsx` | 1872 | Replaced by the connected React studio and its shared API client. |
| `frontend/src/pages/NewRunPage.jsx` | 6365 | Replaced by the connected React studio and its shared API client. |
| `frontend/src/pages/SettingsPage.jsx` | 335 | Replaced by the connected React studio and its shared API client. |
| `frontend/src/services/apiClient.js` | 1055 | Replaced by the connected React studio and its shared API client. |
| `frontend/src/services/pipelineService.js` | 743 | Replaced by the connected React studio and its shared API client. |
| `frontend/src/services/runService.js` | 1174 | Replaced by the connected React studio and its shared API client. |
| `frontend/src/styles/global.css` | 1161 | Replaced by the connected React studio and its shared API client. |
| `frontend/src/styles/tokens.css` | 597 | Replaced by the connected React studio and its shared API client. |
| `frontend/vite.config.js` | 161 | Updated or replaced with the integrated implementation. |
| `requirements.txt` | 319 | Updated or replaced with the integrated implementation. |
| `scripts/__init__.py` | 0 | Retained package marker. |
| `scripts/check_artifacts.py` | 4462 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `scripts/check_categorical_comparisons.py` | 1910 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `scripts/check_chart_planning.py` | 4031 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `scripts/check_column_interpretation.py` | 2402 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `scripts/check_correlations.py` | 1478 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `scripts/check_csv_loading.py` | 2024 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `scripts/check_dataset_input.py` | 1266 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `scripts/check_dataset_overview.py` | 1936 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `scripts/check_dataset_split.py` | 1893 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `scripts/check_eda_schema.py` | 458 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `scripts/check_eda_summary.py` | 4844 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `scripts/check_evaluation.py` | 2909 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `scripts/check_group_comparisons.py` | 1502 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `scripts/check_modeling_plan.py` | 1430 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `scripts/check_modelling_input.py` | 1022 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `scripts/check_numeric_distributions.py` | 2265 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `scripts/check_preprocessing.py` | 2550 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `scripts/check_target_analysis.py` | 3576 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `scripts/check_time_analysis.py` | 2394 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `scripts/check_training.py` | 5642 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `shared/__init__.py` | 0 | Retained package marker. |
| `shared/artifacts.py` | 4209 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `shared/data_validation.py` | 3373 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `shared/dataset_split.py` | 2150 | Updated or replaced with the integrated implementation. |
| `shared/dataset_validation.py` | 3330 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `shared/eda_schemas.py` | 11416 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `shared/evaluation.py` | 1286 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `shared/modeling.py` | 3638 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `shared/modeling_plan.py` | 2350 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `shared/preprocessing.py` | 2095 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `shared/schemas.py` | 812 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |
| `shared/state.py` | 907 | Updated or replaced with the integrated implementation. |
| `shared/storage.py` | 232 | Retained supporting source/asset; EDA and compatibility utilities remain in use. |

Disposition: 58 retained, 35 updated, 34 replaced by the new frontend.

New implementation files are described in [architecture](ARCHITECTURE.md), [API contracts](API.md) and [synopsis alignment](SYNOPSIS_ALIGNMENT.md).
