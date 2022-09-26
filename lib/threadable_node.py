from concurrent import futures
from typing import Union, List
import threading


def threaded(fn):
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()
        return thread
    return wrapper
def sync_parallel_run(node_obj,cmd_list: List[Union[str, list]],) -> List[str]:
    
    
    results = []
    with futures.ThreadPoolExecutor() as executor:
        tasks = [executor.submit(node_obj.execute, cmd)
                 for cmd in cmd_list]
    for task in futures.as_completed(tasks):
        results.append(task.result())
    return results
