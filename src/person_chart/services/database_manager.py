import logging
import os
from typing import List, Dict, Any

from sqlalchemy import create_engine, Column, Integer, String, Table, MetaData, select, delete, insert, text, UniqueConstraint
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

# 檢查 psycopg2 是否可用
_PSYCOPG2_AVAILABLE = True
try:
    import psycopg2
except ImportError:
    _PSYCOPG2_AVAILABLE = False
    logging.warning("psycopg2-binary 未安裝。PostgreSQL 功能將不可用。請運行 'pip install -e .[postgresql]' 來安裝。")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)


class SubscriptionRepository:
    """
    管理訂閱數據的存儲庫，支持 SQLite 和 PostgreSQL。
    用於實現訂閱的持久化。
    """

    def __init__(self, db_type: str, db_path: str = None, db_url: str = None):
        """
        初始化 SubscriptionRepository。

        Parameters:
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
        """根據配置創建 SQLAlchemy 引擎。"""
        if db_type == 'sqlite':
            if not db_path:
                raise ValueError("使用 SQLite 時必須提供 db_path。")
            # 確保目錄存在
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            return create_engine(f'sqlite:///{db_path}')
        elif db_type == 'postgresql':
            if not _PSYCOPG2_AVAILABLE:
                raise RuntimeError("psycopg2-binary 庫未安裝，無法使用 PostgreSQL。")
            if not db_url:
                raise ValueError("使用 PostgreSQL 時必須提供 db_url。")
            return create_engine(db_url)
        else:
            raise ValueError(f"不支持的數據庫類型: {db_type}")

    def _define_table(self) -> Table:
        """定義 subscriptions 資料表結構。"""
        return Table('subscriptions', self.metadata,
                     Column('id', Integer, primary_key=True, autoincrement=True),
                     Column('symbol', String, nullable=False),
                     Column('interval', String, nullable=False, default='1m'),
                     # 增加唯一性約束，防止重複訂閱
                     UniqueConstraint('symbol', 'interval', name='uq_symbol_interval'))

    def get_all_subscriptions(self) -> List[Dict[str, Any]]:
        """
        從資料庫獲取所有已保存的訂閱。

        Returns:
            List[Dict[str, Any]]: 訂閱列表，每個訂閱是一個字典。
        """
        stmt = select(self.subscriptions_table)
        with self.engine.connect() as connection:
            result = connection.execute(stmt)
            return [row._asdict() for row in result.fetchall()]

    def add_subscription(self, symbol: str, interval: str = '1m'):
        """
        添加一個新的訂閱到資料庫。如果已存在，則靜默處理。

        Parameters:
            symbol (str): 交易對符號。
            interval (str): K 線間隔。
        """
        stmt = insert(self.subscriptions_table).values(symbol=symbol.upper(), interval=interval)
        with self.engine.connect() as connection:
            try:
                connection.execute(stmt)
                connection.commit()
                log.info(f"已將訂閱 {symbol.upper()}/{interval} 添加到資料庫。")
            except IntegrityError:
                log.warning(f"訂閱 {symbol.upper()}/{interval} 已存在於資料庫，無需重複添加。")
            except Exception as e:
                log.error(f"添加訂閱 {symbol.upper()} 到資料庫時發生錯誤: {e}")
                connection.rollback()

    def remove_subscription(self, symbol: str, interval: str = '1m'):
        """
        從資料庫移除一個訂閱。

        Parameters:
            symbol (str): 交易對符號。
            interval (str): K 線間隔。
        """
        stmt = delete(self.subscriptions_table).where(
            self.subscriptions_table.c.symbol == symbol.upper(),
            self.subscriptions_table.c.interval == interval
        )
        with self.engine.connect() as connection:
            try:
                result = connection.execute(stmt)
                connection.commit()
                if result.rowcount() > 0:
                    log.info(f"已從資料庫移除訂閱 {symbol.upper()}/{interval}。")
                else:
                    log.warning(f"試圖移除訂閱 {symbol.upper()}/{interval}，但在資料庫中未找到。")
            except Exception as e:
                log.error(f"移除訂閱 {symbol.upper()} 時發生錯誤: {e}")
                connection.rollback()
