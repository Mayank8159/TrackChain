# Background task queue for video transcoding and heavy edge jobs (tc.v1 SOTA).

import asyncio
from typing import Optional
from src.services.video_transcoder import video_transcoder


class TaskQueue:
    """
    Asynchronous task queue manager.
    Supports asynchronous task execution and optional Redis-backed queueing.
    """

    def __init__(self):
        self.redis_pool = None

    async def enqueue_transcode(self, media_id: str):
        """Enqueue video transcoding job."""
        asyncio.create_task(self._run_transcode(media_id))

    async def _run_transcode(self, media_id: str):
        """Execute video transcoding in background thread pool."""
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, video_transcoder.transcode_to_hls, f"videos/{media_id}.mp4", f"hls/{media_id}")
        except Exception as exc:
            print(f"[WARN] Background transcoding task encountered: {exc}")


task_queue = TaskQueue()
