from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import Callable

from app.schemas import JobInfo, JobStatus


RenderTask = Callable[[str, Callable[[int, str], None]], str]


class JobManager:
    def __init__(self, max_workers: int = 1):
        self._jobs: dict[str, JobInfo] = {}
        self._lock = Lock()
        self._executor = ThreadPoolExecutor(max_workers=max(1, max_workers))

    def create(self, job_id: str) -> JobInfo:
        job = JobInfo(job_id=job_id, status=JobStatus.queued, progress=0, message="Đang chờ")
        with self._lock:
            self._jobs[job_id] = job
        return job.model_copy()

    def get(self, job_id: str) -> JobInfo:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                raise KeyError(job_id)
            return job.model_copy()

    def _patch(self, job_id: str, **changes) -> None:
        with self._lock:
            current = self._jobs[job_id]
            self._jobs[job_id] = current.model_copy(update=changes)

    def start(self, job_id: str, task: RenderTask) -> None:
        self._executor.submit(self._run, job_id, task)

    def _run(self, job_id: str, task: RenderTask) -> None:
        self._patch(
            job_id,
            status=JobStatus.running,
            progress=5,
            message="Bắt đầu render",
        )

        def update(progress: int, message: str) -> None:
            self._patch(
                job_id,
                status=JobStatus.running,
                progress=max(0, min(99, progress)),
                message=message,
            )

        try:
            output_url = task(job_id, update)
            self._patch(
                job_id,
                status=JobStatus.completed,
                progress=100,
                message="Hoàn tất",
                output_url=output_url,
                error=None,
            )
        except Exception as exc:  # noqa: BLE001 - job boundary must capture model/ffmpeg errors
            self._patch(
                job_id,
                status=JobStatus.failed,
                message="Render thất bại",
                error=str(exc),
            )
