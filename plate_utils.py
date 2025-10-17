import time


def calculate_runtime(func, *args, **kwargs):
    """ 计算运行时间 """
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()
    run_time = end_time - start_time

    return run_time, result
