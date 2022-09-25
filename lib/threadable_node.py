from concurrent import futures
from typing import Union, List


def sync_parallel_run(node_obj,cmd_list: List[Union[str, list]],) -> List[str]:
    
    
    results = []
    with futures.ThreadPoolExecutor() as executor:
        tasks = [executor.submit(node_obj.execute, cmd)
                 for cmd in cmd_list]
    for task in futures.as_completed(tasks):
        results.append(task.result())
    return results
