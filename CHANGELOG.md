# 更新日誌

本文件記錄了專案的所有重要變更。

格式基於 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/)，
且本專案遵循 [語義化版本控制](https://semver.org/lang/zh-TW/)。

## [0.1.1] - 2024-12-26

### 新增
- **整合式測試引擎**: 建立統一的測試引擎 (`scripts/test-engine.sh`)，確保本地與 CI 環境測試標準完全一致
- **預設品質檢查**: `./run.sh test` 現在預設包含程式碼品質檢查（linting、格式檢查、型別檢查）
- **智慧模組偵測**: 新增自動偵測可測試模組的功能 (`scripts/detect-modules.sh`)
- **跳過品質檢查選項**: 新增 `--skip-quality-checks` 參數，允許在需要時跳過品質檢查以提升開發速度

### 改進
- **測試架構統一**: 本地測試 (`./run.sh test`) 和 CI 測試現在使用相同的測試引擎
- **型別檢查修復**: 修復了 `metrics.py` 中的 mypy 型別檢查錯誤（`str | None` namespace 參數問題）
- **未到達程式碼清理**: 移除 `logging.py` 中的未到達程式碼，消除 mypy 警告
- **屬性測試穩定性**: 改進 Trade 模型的 Hypothesis 策略，確保交易量始終滿足最小需求
- **文件更新**: 更新 `./run.sh --help` 說明，清楚標示新的品質檢查功能

### 修復
- **PrometheusMetricsRegistry**: 修復 namespace 參數為 None 時的型別錯誤
- **JSON 格式化器**: 修復 logging.py 中的未到達語句警告
- **屬性測試**: 修復 Trade 模型測試中的量交易驗證問題，確保生成的交易量始終符合最小需求
- **CI/本地一致性**: 解決了 CI 中發現但本地測試未捕獲的 mypy 錯誤

### 技術細節
- **測試涵蓋率**: 維持在 86.80%（超過 70% 需求）
- **測試數量**: 所有 635 個測試均通過
- **品質檢查**: linting、格式檢查、型別檢查全部通過
- **架構改進**: 統一的測試引擎確保本地和 CI 環境完全一致

### 使用方式變更
```bash
# 新的預設行為：包含品質檢查
./run.sh test

# 跳過品質檢查以提升速度
./run.sh test --skip-quality-checks

# 最快的開發測試
./run.sh test units --skip-quality-checks --parallel-units=4 --no-cov
```

### 開發者影響
- **向後相容**: 所有現有的測試指令繼續有效
- **CI 一致性**: 本地測試現在與 CI 執行相同的檢查
- **開發效率**: 可選擇跳過品質檢查以獲得更快的反饋循環
- **測試可靠性**: 統一的測試架構減少了環境差異導致的問題

---

### Git 提交參考
- 主要變更: [5cfc6ae](https://github.com/your-repo/commit/5cfc6aef0b738e2140492d83dfe4a0f244db3cda) - feat: 重新架構測試框架並現代化核心系統