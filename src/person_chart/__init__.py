import logging

# 配置包級別的日誌記錄器
logging.getLogger(__name__).addHandler(logging.NullHandler())

# 導出核心配置，方便外部調用
from .config import config
