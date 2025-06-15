import logging
import os
from typing import List, Dict, Any

from sqlalchemy import create_engine, Column, Integer, String, Table, MetaData, select, delete, insert, text, UniqueConstraint
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from person_chart.colored_logging import setup_colored_logging

import logging
import os
from typing import List, Dict, Any

from sqlalchemy import create_engine, Column, Integer, String, Table, MetaData, select, delete, insert, text, UniqueConstraint
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from person_chart.colored_logging import setup_colored_logging

log = setup_colored_logging(level=logging.INFO)

_PSYCOPG2_AVAILABLE = True
try:
    import psycopg2
except ImportError:
    _PSYCOPG2_AVAILABLE = False
    log.warning("psycopg2-binary 未安裝。PostgreSQL 功能將不可用。請運行 'pip install -e .[postgresql]' 來安裝。")


class SubscriptionRepository:
    """
    管理訂閱數據的存儲庫，支持 SQLite 和 PostgreSQL。

    作者: yuan
    建立時間: 2025-06-15 18:13:00
    更新時間: 2025-06-15 18:13:00
    版本號: 0.6.0
    用途說明:
        此類負責管理應用程式的訂閱數據的持久化，支持 SQLite 和 PostgreSQL 兩種數據庫類型。
        它提供了創建數據庫引擎、定義訂閱表結構、獲取所有已保存訂閱、
        添加新訂閱以及移除訂閱的功能，確保訂閱信息在應用程式重啟後能夠被保留。
    """

    def __init__(self, db_type: str, db_path: str = None, db_url: str = None):
        """
        初始化 SubscriptionRepository。

        參數:
            db_type (str): 資料庫類型，'sqlite' 或 'postgresql'。
            db_path (str, optional): SQLite 資料庫文件路徑。
            db_url (str, optional): PostgreSQL 連接 URL。
        """
        self.engine = self._create_engine(db_type, db_path, db_url)
        self.metadata = MetaData()
        self.subscriptions_table = self._define_table()
        self.metadata.create_all(self.engine)
        log.info(f"SubscriptionRepository 初始化完成，使用 {db_type} 資料庫。")

    def _create_engine(self, db_type: str, db_path: str, db_url: str) -> Engine:
        """
        根據配置創建 SQLAlchemy 引擎。
        此私有方法根據指定的數據庫類型（SQLite 或 PostgreSQL）和連接參數，
        創建並返回一個 SQLAlchemy 數據庫引擎實例。
        它會檢查必要的參數和庫是否可用，並在缺失時拋出錯誤。
        """
        if db_type == 'sqlite':
            if not db_path:
                raise ValueError("使用 SQLite 時必須提供 db_path。")
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            return create_engine(f'sqlite:///{db_path}')
        elif db_type == 'postgresql':
            if not _PSYCOPG2_AVAILABLE:
                raise RuntimeError("psycopg2-binary 庫未安裝，無法使用 PostgreSQL。")
            if not db_url:
                raise ValueError("使用 PostgreSQL 時必須提供 db_url。")
            return create_engine(db_url)
        else:
            raise ValueError(f"不支援的數據庫類型: {db_type}。")

    def _define_table(self) -> Table:
        """
        定義 subscriptions 資料表結構。
        此私有方法定義了用於存儲訂閱信息的 SQLAlchemy Table 對象，
        包括 `id`（主鍵）和 `symbol`（交易對符號，唯一且非空）列。
        """
        return Table('subscriptions', self.metadata,
                     Column('id', Integer, primary_key=True, autoincrement=True),
                     Column('symbol', String, nullable=False, unique=True)
                     )

    def get_all_subscriptions(self) -> List[Dict[str, Any]]:
        """
        從資料庫獲取所有已保存的訂閱。
        此方法執行一個 SELECT 語句，從 `subscriptions` 表中檢索所有記錄，
        並將每條記錄轉換為字典格式的列表返回。
        """
        stmt = select(self.subscriptions_table)
        with self.engine.connect() as connection:
            result = connection.execute(stmt)
            return [row._asdict() for row in result.fetchall()]

    def add_subscription(self, symbol: str):
        """
        添加一個新的訂閱到資料庫。如果已存在，則靜默處理。
        此方法將指定的交易對符號插入到 `subscriptions` 表中。
        如果該符號已存在（由於唯一約束），則會捕獲 IntegrityError 並記錄警告，
        表示無需重複添加。其他數據庫錯誤也會被捕獲並記錄。
        """
        stmt = insert(self.subscriptions_table).values(symbol=symbol.upper())
        with self.engine.connect() as connection:
            try:
                connection.execute(stmt)
                connection.commit()
                log.info(f"已將訂閱 {symbol.upper()} 添加到資料庫。")
            except IntegrityError:
                log.warning(f"訂閱 {symbol.upper()} 已存在於資料庫，無需重複添加。")
            except Exception as e:
                log.error(f"添加訂閱 {symbol.upper()} 到資料庫時發生錯誤: {e}。")
                connection.rollback()

    def remove_subscription(self, symbol: str):
        """
        從資料庫移除一個訂閱。
        此方法從 `subscriptions` 表中刪除與指定交易對符號匹配的記錄。
        它會檢查刪除操作是否實際影響了行數，並記錄相應的信息。
        任何數據庫錯誤都會被捕獲並記錄。
        """
        stmt = delete(self.subscriptions_table).where(
            self.subscriptions_table.c.symbol == symbol.upper()
        )
        with self.engine.connect() as connection:
            try:
                result = connection.execute(stmt)
                connection.commit()
                if result.rowcount() > 0:
                    log.info(f"已從資料庫移除訂閱 {symbol.upper()}。")
                else:
                    log.warning(f"試圖移除訂閱 {symbol.upper()}，但在資料庫中未找到。")
            except Exception as e:
                log.error(f"移除訂閱 {symbol.upper()} 時發生錯誤: {e}。")
                connection.rollback()
