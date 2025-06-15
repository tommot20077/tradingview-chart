"""
時間單位轉換工具
"""
import logging
from typing import Tuple

from person_chart import config
from person_chart.colored_logging import setup_colored_logging

log = setup_colored_logging(level=logging.INFO)

def interval_to_seconds(interval_str: str) -> int:
    """
    將時間間隔字串 (例如 '1m', '1h') 轉換為秒。

    此函數解析一個表示時間間隔的字串，並將其轉換為對應的秒數。
    支持的單位包括分鐘 (m)、小時 (h)、天 (d)、週 (w)、月 (M) 和年 (y)。
    如果輸入格式無效，則返回 0。

    參數:
        interval_str (str): 時間間隔字串，例如 '1m', '5h', '3d'。

    返回:
        int: 轉換後的秒數。如果輸入無效，則返回 0。
    """
    if not interval_str or len(interval_str) < 2:
        return 0

    unit = interval_str[-1]
    try:
        value = int(interval_str[:-1])
        if unit == 'm': return value * 60
        if unit == 'h': return value * 3600
        if unit == 'd': return value * 86400
        if unit == 'w': return value * 604800
        if unit == 'M': return value * 2592000
        if unit == 'y': return value * 31536000
    except ValueError:
        return 0
    return 0


def find_optimal_source_interval(target_interval: str) -> Tuple[str, int]:
    """
    尋找能夠整除目標區間的最大可用區間。

    參數:
        target_interval (str): 期望的最終區間（例如，'2h'）。

    返回:
        Tuple[str, int]: 包含最佳來源區間字串和整數因子的元組，用於聚合。
    """
    target_seconds = interval_to_seconds(target_interval)
    if target_seconds < 60:
        return '1m', 1

    best_source = '1m'
    best_source_seconds = interval_to_seconds(best_source)

    sorted_intervals = sorted(config.binance_aggregation_intervals, key=interval_to_seconds, reverse=True)

    for interval in sorted_intervals:
        interval_sec = interval_to_seconds(interval)
        if interval_sec > 0 and target_seconds % interval_sec == 0:
            best_source = interval
            best_source_seconds = interval_sec
            break

    factor = int(target_seconds / best_source_seconds)
    return best_source, factor


def convert_interval_to_pandas_freq(interval_str: str) -> str:
    """
    將自定義的時間間隔字串轉換為 Pandas resample 可接受的頻率字串。
    例如: '1m' -> '1T', '1h' -> '1H', '1d' -> '1D', '1M' -> '1M'
    """
    if not interval_str or len(interval_str) < 2:
        return ""

    unit = interval_str[-1]
    value = interval_str[:-1]

    unit_map = {
        'ns': 'ns',  # 納秒
        'us': 'us',  # 微秒
        'ms': 'ms',  # 毫秒
        's': 's',  # 秒
        'm': 'min',  # 分鐘
        'h': 'h',  # 小時
        'd': 'D',  # 天
        'w': 'W',  # 週
        'M': 'ME',  # 月底
        'y': 'YE'  # 年底
    }

    pandas_unit = unit_map.get(unit)
    if not pandas_unit:
        log.error(f"不支援的時間單位 '{unit}' 於間隔 '{interval_str}'")
        return ""

    return f"{value}{pandas_unit}"
