"""缓存系统模块"""
import time
from config import CACHE_TTL, CACHE_MAX_SIZE, CACHE_EXPIRED, cache_lock

# 缓存字典
_stats_cache = {}
_stats_cache_time = {}
_tags_cache = {}
_tags_cache_time = {}


def get_cached(cache, cache_time, user_id):
    """获取缓存值，如果过期或不存在返回 CACHE_EXPIRED。"""
    with cache_lock:
        ts = cache_time.get(user_id)
        if ts is None:
            return CACHE_EXPIRED
        if time.time() - ts > CACHE_TTL:
            return CACHE_EXPIRED
        return cache.get(user_id)


def set_cached(cache, cache_time, user_id, value):
    """设置缓存，超限时清除最旧的条目。"""
    with cache_lock:
        cache[user_id] = value
        cache_time[user_id] = time.time()
        if len(cache) > CACHE_MAX_SIZE:
            oldest = sorted(cache_time, key=lambda k: cache_time[k])[:len(cache)//2]
            for k in oldest:
                cache.pop(k, None)
                cache_time.pop(k, None)


def invalidate_stats(user_id):
    """清除用户统计缓存"""
    with cache_lock:
        _stats_cache.pop(user_id, None)
        _stats_cache_time.pop(user_id, None)


def invalidate_tags(user_id):
    """清除用户标签缓存"""
    with cache_lock:
        _tags_cache.pop(user_id, None)
        _tags_cache_time.pop(user_id, None)
