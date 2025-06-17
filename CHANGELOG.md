# 版本更新紀錄

## 0.5.5 - 2025-06-17

### 新增:

- **連線訂閱狀態管理更新**:
  - 現在使用 `/ws/price` 時直接在訊息內部訂閱種類以及間隔即可，加強版支援多種資產以及間隔使用，基礎版只能同時訂閱1種資產的1m數據
  - 加入同一筆 Websocket 連線的取消訂閱功能，當使用者取消訂閱時，會自動取消所有訂閱的資產和間隔。

### 優化:

- 簡化一般版的處理訂閱邏輯以及方法，將冗於的訂閱邏輯移除，並且將訂閱邏輯簡化為只需要在訊息內部訂閱種類以及間隔即可。

### 版本號更新:

- `src/person_chart/enhanced_main.py` 的版本號更新至 `0.6.2`。
- `src/person_chart/main` 的版本號更新至 `0.7.1`。

---

## 0.5.4 - 2025-06-17

### 修復

- **圖表數據顯示跳空問題**:
  - 優化 `src/person_chart/analysis/data_analyzer.py` 中的 K 線聚合邏輯，將 Pandas 的 `groupby` 和 `pd.Grouper` 替換為更高效的
    `resample` 功能，以確保數據連續性並正確處理未完成的 K 線。
  - 在 `query_and_aggregate` 方法中新增了對無效時間窗口（小於 60 秒）的警告。
  - 移除聚合規則中對 `required_cols` 和 `missing_cols` 的檢查，並簡化 `dropna` 邏輯。
- **WebSocket 連接初始化**:
  - 在 `src/person_chart/enhanced_main.py` 中新增 `_initialize_current_kline` 方法，用於在 WebSocket
    連接建立時，從數據庫查詢並初始化當前時間窗口的聚合 K 線狀態，避免數據跳空。
  - `_update_and_get_aggregate` 方法現在使用狀態管理而非緩衝區來更新聚合 K 線，確保實時數據的平滑銜接。
  - 移除了 `active_connections` 中對 `buffer` 的依賴。
- **歷史數據獲取優化**:
  - `src/person_chart/providers/binance_provider.py` 中的 `get_historical_data` 方法現在能智能銜接當前未完成的 K
    線，並優化了數據查詢邏輯，不再區分預聚合數據。
  - 增加了對返回數據列的重命名和 `trade_count` 列的包含。
  - 增加了對 `ValueError` 的捕獲和日誌記錄。
- **配置調整**:
  - `src/person_chart/config.py` 中 `binance_base_interval` 固定為 `'1m'`，不再從環境變數讀取。

---

## 0.5.3 - 2025-06-16

### 重構

- **重新設計結構目錄**:
  - `src/person_chart/colored_logging.py` => `src/person_chart/utils/colored_logging.py`
  - `src/person_chart/tools/time_unity.py` => `src/person_chart/utils/time_unity.py`
  - `src/person_chart/services/database_manager.py` => `src/person_chart/storage/subscription_repo.py`
  - `src/person_chart/providers/abstract_data_provider.py` => `src/person_chart/providers/abstract.py`
  - `src/person_chart/providers/crypto_provider.py` => `src/person_chart/providers/binance_provider.py`
  - `src/person_chart/utils/time_unity.py` 中的 `convert_interval_to_pandas_freq` 函數將月份和年份的 Pandas 頻率從
    `ME`/`YE` 調整為 `MS`/`YS` (月初/年初)。
  - 更新了所有受影響文件的導入路徑。
- **版本號更新**: `src/person_chart/enhanced_main.py` 的版本號更新至 `0.6.1`。

---

## 0.5.2 - 2025-06-16

### 新增

- **K 線聚合資料處理優化**: 優化 K 線聚合邏輯，確保時間戳對齊，並處理緩衝區清空。
- **時間單位轉換工具**: 新增 `find_optimal_source_interval` 和 `convert_interval_to_pandas_freq` 函數，用於更靈活地處理時間間隔。

### 修改

- **配置更新**: 將 `config.aggregation_intervals` 更名為 `config.binance_aggregation_intervals`。
- **日誌級別調整**: 將 `query_direct` 中的日誌級別從 `info` 調整為 `debug`。
- **WebSocket 連接管理**: 優化 WebSocket 廣播邏輯，處理連接斷開和異步任務。
- **Kafka 消費者關閉**: 修正 Kafka 消費者關閉時的參數。
- **訂閱日誌**: 調整訂閱日誌的詳細程度。
- **版本號更新**: 更新 `enhanced_main.py` 的版本號至 1.0.1。

### 移除

- 移除 `src/person_chart/providers/enhanced_crypto_provider.py`
  ，其功能已更改到 `src/person_chart/providers/crypto_provider.py`。

---

## 0.5.1 - 2025-06-15

### 新增

- **K 線聚合資料處理**: 加入 K 線聚合資料處理，由基礎數據 `config.binance_base_interval`
  開始會自動聚合成更大尺度的數據類型，根據聚合的間隔分成常用間隔以及自定義間隔。
    1. 常用間隔為預設的聚合尺度，在查詢時可以直接使用 (定義於 `AGGREGATION_INTERVALS`)。
    2. 自定義間隔則是會再查詢此間隔的最大常用間隔因數，例如 `3d` 則會自動聚合 3 根日線的數據。

### 重構

- **日誌記錄系統**: 新增彩色日誌支持，並其餘模塊更新使用新日誌設置。

### 修改

- **歷史資料查詢**: 現在查詢歷史資料時加入 `limit` 以及 `offset` 作為分頁查詢的參數。
- **使用者訂閱資產間隔設定**: 移除使用者訂閱資產間隔的設定，同一由伺服端管理設定，而用戶現在可以在請求時加入自定義間隔顯示指定間隔的
  K 線圖。

### 移除

- `binance_symbol` 設定。
- 訂閱資料表間隔設定。

---

## V0.5.0 - 2025-06-15

### 新增

- **資料庫記錄功能**: 引入資料庫記錄功能，支援 PostgreSQL 和 SQLite。

### 修改

- 移除對 `requirements.txt` 的依賴，改為使用 `setup.py` 進行依賴管理。

### 移除

- 舊的數據庫相關文件。
- 舊的配置相關文件。
- 舊的測試相關文件。

---

## V0.4.0 - 2025-06-14

### 新增

- **歷史數據查詢功能**: 引入歷史數據查詢功能。
- **Docker Compose 範例**: 新增 `docker-compose` 範例。

### 修改

- 調整了某些配置以支持新的功能。

---

## V0.3.0 - 2025-06-13

### 新增

- **Kafka 消息隊列**: 引入 Kafka 消息隊列功能，支援數據發佈和消費。
- **抽象數據提供者介面**: 新增抽象數據提供者介面，用於統一數據源的行為。

### 修改

- 調整了部分代碼以適應新的架構。

### 移除

- 舊的日誌和數據模型相關代碼。

---

## V0.2.0 - 2025-06-11

### 新增

- **數據庫記錄**: 新增數據庫記錄功能。
- **日誌系統**: 引入新的日誌系統。

### 修改

- 將原有的 `print` 語句替換為 `log` 語句。

---

## V0.1.0 - 2025-06-09

### 新增

- **初始 Websocket 數據流與 InfluxDB3 集成**: 建立初始 Websocket 數據流與 InfluxDB3 的集成。
