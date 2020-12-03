from __future__ import absolute_import

import logging
import os
import threading


try:
    from tensorflow.python.distribute.cluster_resolver import tpu_cluster_resolver  # type: ignore
    from tensorflow.python.profiler import profiler_client  # type: ignore
except ImportError:
    tpu_cluster_resolver = None
    profiler_client = None
    pass


logger = logging.getLogger(__name__)


class TPUProfiler(object):
    def __init__(
        self,
        service_addr=None,
        tpu=None,
        tpu_zone=None,
        gcp_project=None,
        duration_ms=1000,
    ):
        if service_addr:
            if tpu:
                logger.warn(
                    "Both service_addr and tpu arguments provided. "
                    "Ignoring tpu and using service_addr."
                )
        else:
            if not tpu:
                tpu = os.environ.get("TPU_NAME")
                if tpu is None:
                    raise Exception("Required environment variable TPU_NAME.")
            if tpu_zone is None:
                tpu_zone = os.environ.get("CLOUDSDK_COMPUTE_ZONE")
            if gcp_project is None:
                gcp_project = os.environ.get("CLOUDSDK_CORE_PROJECT")
            try:
                service_addr = tpu_cluster_resolver.TPUClusterResolver(
                    [tpu], zone=tpu_zone, project=gcp_project
                ).get_master()
            except (ValueError, TypeError):
                raise Exception(
                    "Failed to find TPU. Try specifying TPU zone "
                    "(via CLOUDSDK_COMPUTE_ZONE environment variable)"
                    " and GCP project (via CLOUDSDK_CORE_PROJECT "
                    "environment variable)."
                )
        service_addr = service_addr.replace("grpc://", "").replace(":8470", ":8466")
        self.service_addr = service_addr
        self.duration_ms = duration_ms
        self._tpu_utilization = 0.0
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._stop = False
        self._thread.start()

    def _get_tpu_utilization(self):
        # this call blocks for duration_ms milliseconds
        res = profiler_client.monitor(
            self.service_addr, duration_ms=self.duration_ms, level=2
        )
        return float(res.split("Utilization ")[1].split(": ")[1].split("%")[0])

    def _loop(self):
        while not self._stop:
            try:
                self._tpu_utilization = self._get_tpu_utilization()
            except Exception:
                pass

    def get_tpu_utilization(self):
        return self._tpu_utilization

    def stop(self):
        self._stop = True


def is_tpu_available():
    return profiler_client is not None and "TPU_NAME" in os.environ