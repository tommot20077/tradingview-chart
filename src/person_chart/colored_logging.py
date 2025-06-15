"""
此模組提供彩色日誌功能，用於在控制台輸出不同顏色等級的日誌訊息。
"""

import logging
import sys

# 定義 ANSI 顏色代碼，用於在終端中顯示彩色文本。
COLORS = {
    'RESET': '\033[0m',
    'RED': '\033[31m',
    'GREEN': '\033[32m',
    'YELLOW': '\033[33m',
    'BLUE': '\033[34m',
    'MAGENTA': '\033[35m',
    'CYAN': '\033[36m',
    'WHITE': '\033[37m',
}


class ColoredFormatter(logging.Formatter):
    """
    自定義日誌格式化器，為不同級別的日誌設置不同顏色。

    作者: yuan
    建立時間: 2025-06-15 18:13:00
    更新時間: 2025-06-15 18:13:00
    版本號: 0.6.0
    用途說明:
        此類繼承自 logging.Formatter，並重寫其 format 方法，
        根據日誌記錄的級別（如 DEBUG, INFO, WARNING, ERROR, CRITICAL）
        為日誌訊息添加 ANSI 顏色代碼，使其在控制台輸出時以不同顏色顯示，
        提高日誌的可讀性和區分度。
    """

    LEVEL_COLORS = {
        logging.DEBUG: COLORS['BLUE'],
        logging.INFO: COLORS['GREEN'],
        logging.WARNING: COLORS['YELLOW'],
        logging.ERROR: COLORS['RED'],
        logging.CRITICAL: COLORS['MAGENTA'],
    }

    def format(self, record):
        """
        格式化日誌記錄。
        此方法會保存原始日誌訊息，為日誌級別名稱添加顏色代碼，
        然後調用基類的 format 方法進行實際的格式化，
        最後恢復原始日誌訊息和級別名稱，以避免對後續處理造成影響。
        """
        original_msg = record.msg
        levelname = record.levelname
        levelcolor = self.LEVEL_COLORS.get(record.levelno, COLORS['WHITE'])

        record.levelname = f"{levelcolor}{levelname}{COLORS['RESET']}"

        result = super().format(record)

        record.msg = original_msg
        record.levelname = levelname

        return result


def setup_colored_logging(level=logging.INFO):
    """
    設置彩色日誌系統。
    此函數會獲取根日誌器，設置其日誌級別，並清除所有現有的處理器。
    然後創建一個控制台處理器，設置其日誌級別和自定義的彩色格式化器，
    最後將此處理器添加到根日誌器中，並返回根日誌器實例。
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    if root_logger.handlers:
        root_logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    formatter = ColoredFormatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        '%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)

    return root_logger
