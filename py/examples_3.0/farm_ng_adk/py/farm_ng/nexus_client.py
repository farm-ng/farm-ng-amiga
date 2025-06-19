from __future__ import annotations

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from enum import Enum
from typing import Awaitable, Callable, Optional
import pynng

from farm_ng.nexus import nexus_pb2


class NexusClient:
    """
    A wrapper class around pynng for interacting with Nexus
    (https://github.com/farm-ng/autumn/tree/main/autonomy/crates/nexus).

    Design asynchronously to handle requests and subscriptions concurrently.
    """

    def __init__(
        self,
        request_address: str | None = None,
        feedback_address: str | None = None,
        stream_address: str | None = None,
        timeout: int = 200,
    ):
        self.request_address = request_address
        self.feedback_address = feedback_address
        self.stream_address = stream_address
        self.timeout = timeout

        self.req_socket: pynng.Req0 | None = None
        self.feedback_socket: pynng.Sub0 | None = None
        self.stream_socket: pynng.Sub0 | None = None

        self._request_lock = asyncio.Lock()

        self.feedback_subs: dict[
            str, Callable[[nexus_pb2.Feedback], Awaitable[None]]
        ] = {}
        self._feedback_sub_task: asyncio.Task | None = None
        self._running = False

        self.stream_subs: dict[
            str, Callable[[nexus_pb2.Stream], Awaitable[None]]
        ] = {}
        self._stream_task: asyncio.Task | None = None
        self._streaming = False

    async def _try_connect_request(self, max_retries: int = 3) -> bool:
        """Try to establish request socket connection"""
        if not self.request_address:
            return False

        for attempt in range(max_retries):
            if self.req_socket is None:
                try:
                    backoff = min(2**attempt, 10)  # Cap at 10 seconds
                    await asyncio.sleep(backoff)
                    self.req_socket = pynng.Req0(
                        recv_timeout=self.timeout, send_timeout=self.timeout
                    )
                    self.req_socket.dial(self.request_address, block=True)
                    return True
                except Exception as e:
                    logging.error(f"Connection attempt {attempt + 1} failed: {e}")
                    if self.req_socket:
                        self.req_socket.close()
                        self.req_socket = None
                    return False
            else:
                return True
        return False

    async def _try_connect_feedback(self, max_retries: int = 3) -> bool:
        """Try to establish subscription socket connection with retries"""
        if not self.feedback_address:
            return False

        logging.debug(f"Connecting to nexus feedback: {self.feedback_address}")

        for attempt in range(max_retries):
            if self.feedback_socket is None:
                try:
                    backoff = min(2**attempt, 10)  # Cap at 10 seconds
                    await asyncio.sleep(backoff)

                    self.feedback_socket = pynng.Sub0(recv_timeout=self.timeout)
                    self.feedback_socket.subscribe(b"")
                    self.feedback_socket.dial(self.feedback_address, block=True)
                    self._running = True
                    self._feedback_sub_task = asyncio.create_task(
                        self._handle_feedback_subs()
                    )
                    return True
                except Exception as e:
                    logging.error(f"Connection attempt {attempt + 1} failed: {e}")
                    if self.feedback_socket:
                        self.feedback_socket.close()
                        self.feedback_socket = None
                    self._running = False
            else:
                return True
        return False

    async def _try_connect_stream(self, max_retries: int = 3) -> bool:
        """Try to establish subscription socket connection with retries"""
        if not self.stream_address:
            return False

        logging.debug(f"Connecting to nexus stream: {self.stream_address}")

        for attempt in range(max_retries):
            if self.stream_socket is None:
                try:
                    backoff = min(2**attempt, 10)  # Cap at 10 seconds
                    await asyncio.sleep(backoff)

                    self.stream_socket = pynng.Sub0(recv_timeout=self.timeout)
                    self.stream_socket.subscribe(b"")
                    self.stream_socket.dial(self.stream_address, block=True)
                    self._streaming = True
                    self._stream_task = asyncio.create_task(
                        self._handle_stream_subs()
                    )
                    return True
                except Exception as e:
                    logging.error(f"Connection attempt {attempt + 1} failed: {e}")
                    if self.stream_socket:
                        self.stream_socket.close()
                        self.stream_socket = None
                    self._streaming = False
            else:
                return True
        return False

    async def stop(self):
        """Stop the client and clean up resources"""
        self._running = False
        if self._feedback_sub_task:
            self._feedback_sub_task.cancel()
            try:
                await self._feedback_sub_task
            except asyncio.CancelledError:
                pass

        self._streaming = False
        if self._stream_sub_task:
            self._stream_sub_task.cancel()
            try:
                await self._stream_sub_task
            except asyncio.CancelledError:
                pass

        if self.req_socket:
            self.req_socket.close()
        if self.feedback_socket:
            self.feedback_socket.close()
        if self.stream_socket:
            self.stream_socket.close()

    async def request(self, message: nexus_pb2.Request) -> Optional[nexus_pb2.Reply]:
        if not await self._try_connect_request():
            logging.error("Failed to establish request connection")
            return None

        async with self._request_lock:
            try:
                if self.req_socket:
                    await self.req_socket.asend(message.SerializeToString())
                    response = await self.req_socket.arecv()
                    reply = nexus_pb2.Reply()
                    reply.ParseFromString(response)
                    return reply
                else:
                    return None
            except Exception as e:
                logging.error(f"Request failed: {e}")
                if self.req_socket:
                    self.req_socket.close()
                    self.req_socket = None
                return None

    async def _handle_feedback_subs(self):
        """Background task that handles all subscriptions"""
        while self._running:
            try:
                if not self.feedback_subs:  # No active feedback_subs
                    await asyncio.sleep(0.1)  # Avoid busy waiting
                    continue

                message = await self.feedback_socket.arecv()  # type: ignore
                feedback = nexus_pb2.Feedback()
                feedback.ParseFromString(message)

                # Deliver feedback to all feedback_subs
                dead_feedback_subs: set = set()
                for sub_id, callback in self.feedback_subs.items():
                    try:
                        await callback(feedback)
                    except Exception as e:
                        logging.error(f"Error in subscriber {sub_id}: {e}")
                        dead_feedback_subs.add(sub_id)  # Mark for removal

                # Clean up dead feedback_subs
                for sub_id in dead_feedback_subs:
                    del self.feedback_subs[sub_id]

            except pynng.exceptions.Timeout:
                continue
            except Exception as e:
                logging.error(f"Error in subscription handler: {e}")
                await asyncio.sleep(1)  # Avoid rapid retries

    async def _handle_stream_subs(self):
        """Background task that handles all subscriptions"""
        while self._streaming:
            try:
                if not self.stream_subs:  # No active stream_subs
                    await asyncio.sleep(0.1)  # Avoid busy waiting
                    continue

                message = await self.stream_socket.arecv()  # type: ignore
                stream = nexus_pb2.Stream()
                stream.ParseFromString(message)

                # Deliver stream to all stream_subs
                dead_stream_subs: set = set()
                for sub_id, callback in self.stream_subs.items():
                    try:
                        await callback(stream)
                    except Exception as e:
                        logging.error(f"Error in streamer {sub_id}: {e}")
                        dead_stream_subs.add(sub_id)  # Mark for removal

                # Clean up dead stream_subs
                for sub_id in dead_stream_subs:
                    del self.stream_subs[sub_id]

            except pynng.exceptions.Timeout:
                continue
            except Exception as e:
                logging.error(f"Error in stream handler: {e}")
                await asyncio.sleep(1)  # Avoid rapid retries

    def register_feedback_callback(
        self, callback: Callable[[nexus_pb2.Feedback], Awaitable[None]]
    ) -> str:
        """
        Register a callback for subscription. Returns a subscription ID that can be used
        to remove the callback later.
        """
        sub_id = str(uuid.uuid4())
        self.feedback_subs[sub_id] = callback
        return sub_id

    def remove_feedback_callback(self, sub_id: str) -> None:
        """
        Remove a previously registered callback using its subscription ID.
        """
        self.feedback_subs.pop(sub_id, None)

    def register_stream_callback(
        self, callback: Callable[[nexus_pb2.Stream], Awaitable[None]]
    ) -> str:
        """
        Register a callback for subscription. Returns a subscription ID that can be used
        to remove the callback later.
        """
        sub_id = str(uuid.uuid4())
        self.stream_subs[sub_id] = callback
        return sub_id

    def remove_stream_callback(self, sub_id: str) -> None:
        """
        Remove a previously registered callback using its subscription ID.
        """
        self.stream_subs.pop(sub_id, None)

    @asynccontextmanager
    async def feedback_sub(
        self, callback: Optional[Callable[[nexus_pb2.Feedback], Awaitable[None]]] = None
    ):
        class EmptyGenerator:
            def __aiter__(self):
                return self

            async def __anext__(self):
                raise StopAsyncIteration

        if not await self._try_connect_feedback():
            logging.error("Failed to establish subscription connection")
            yield EmptyGenerator() if callback is None else None
            return

        if callback:
            sub_id = self.register_feedback_callback(callback)
            try:
                yield None
            finally:
                self.remove_feedback_callback(sub_id)
        else:
            queue: asyncio.Queue[nexus_pb2.Feedback] = asyncio.Queue()

            async def queue_callback(feedback):
                await queue.put(feedback)

            async def feedback_generator():
                while True:
                    yield await queue.get()

            sub_id = self.register_feedback_callback(queue_callback)
            try:
                yield feedback_generator()
            finally:
                self.remove_feedback_callback(sub_id)

    @asynccontextmanager
    async def stream_sub(
        self, callback: Optional[Callable[[nexus_pb2.Stream], Awaitable[None]]] = None
    ):
        class EmptyGenerator:
            def __aiter__(self):
                return self

            async def __anext__(self):
                raise StopAsyncIteration

        if not await self._try_connect_stream():
            logging.error("Failed to establish stream connection")
            yield EmptyGenerator() if callback is None else None
            return

        if callback:
            sub_id = self.register_stream_callback(callback)
            try:
                yield None
            finally:
                self.remove_stream_callback(sub_id)
        else:
            queue: asyncio.Queue[nexus_pb2.Stream] = asyncio.Queue()

            async def queue_callback(feedback):
                await queue.put(feedback)

            async def stream_generator():
                while True:
                    yield await queue.get()

            sub_id = self.register_stream_callback(queue_callback)
            try:
                yield stream_generator()
            finally:
                self.remove_stream_callback(sub_id)


class FeedbackKind(Enum):
    All = 0
    AmigaState = 1
    WorldModelFeedback = 2
    NavigationFeedback = 3
    ImplementFeedback = 4
    JobFeedback = 5
    VideoStreamFeedback = 6
    TrackRecorderFeedback = 7


def switch_feedback_kind(kind: FeedbackKind) -> str:
    if kind == FeedbackKind.AmigaState:
        return "amiga_state"
    elif kind == FeedbackKind.WorldModelFeedback:
        return "world_model"
    elif kind == FeedbackKind.NavigationFeedback:
        return "navigation"
    elif kind == FeedbackKind.ImplementFeedback:
        return "implement"
    elif kind == FeedbackKind.JobFeedback:
        return "job"
    elif kind == FeedbackKind.VideoStreamFeedback:
        return "video_stream"
    elif kind == FeedbackKind.TrackRecorderFeedback:
        return "track_recorder_feedback"
    else:
        return ""


async def filter_feedback_by_kind(
    feedback: nexus_pb2.Feedback, feedback_kind: FeedbackKind
) -> Optional[nexus_pb2.Feedback]:
    """
    Callback function that filters feedback messages.
    """
    if feedback_kind == FeedbackKind.All:
        return feedback
    else:
        kind = switch_feedback_kind(feedback_kind)
        if feedback.HasField(kind):
            return feedback
    return None
