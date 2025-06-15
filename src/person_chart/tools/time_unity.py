"""
時間單位轉換工具
"""

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
        if unit == 'M': return value * 2592000 # 30天
        if unit == 'y': return value * 31536000 # 365天
    except ValueError:
        return 0
    return 0
