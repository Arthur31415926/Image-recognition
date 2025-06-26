# auto_scaler.py
import time
from create_log import init_logging

log = init_logging("auto_scaler", "auto_scaler.log")

from config import Config
from aws_resources import (
    get_queue_depth, list_instances_by_tag, launch_worker_instance, terminate_worker_instance
)


def auto_scale(request_queue_url):
    log.info("Auto-scaler started.")
    while True:
        try:
            depth = get_queue_depth(request_queue_url)

            workers = list_instances_by_tag("Role", Config.WORKER_TAG, ["pending", "running"])
            num_instances = len(workers)
            log.info(f"Queue depth: {depth}, Active workers: {num_instances}")

            desired = min(Config.MAX_WORKERS, max(Config.MIN_WORKERS, depth // Config.TASKS_PER_WORKER + 1))

            if depth >= 40:
                desired = max(10, desired)

                # 启动实例只在未达到 desired 的前提下进行
            if num_instances < desired:
                launch_count = min(desired - num_instances, Config.MAX_WORKERS - num_instances)
                for _ in range(launch_count):
                    launch_worker_instance()
                    time.sleep(2)
            elif num_instances > desired:
                to_terminate = workers[:num_instances - desired]
                for inst_id in to_terminate:
                    terminate_worker_instance(inst_id)

        except Exception as e:
            log.error(f"Auto-scale error: {e}")

        time.sleep(Config.SCALE_INTERVAL)
