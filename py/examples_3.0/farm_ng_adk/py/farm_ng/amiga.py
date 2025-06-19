from typing import Dict, Any, Awaitable, Callable, Optional
import time
from datetime import datetime
from contextlib import asynccontextmanager
from farm_ng.helpers import load_track_from_json
from farm_ng.nexus_client import NexusClient
from farm_ng.nexus import Request, RecorderRequest, RecorderStartRequest, RecorderStopRequest, \
    Value, RecorderAnnotationRequest, Timestamp, Stream, Feedback, VideoStreamRequest, \
    VideoEncoderSettings, VideoStreamResolution, TeleopRequest, TeleopActivateRequest, TeleopDeactivateRequest, TeleopCommandRequest, \
    NavigationRequest, StopRequest, TurnAroundRequest, TurnAroundManeuverKind, TurnAroundReferenceFrame, DirectionKind, \
    FollowRouteRequest, ImplementRequest, ImplementState, ToolRequest, ToolState, EnabledKind, PolarToolState, PolarToolStateKind, \
    RotaryToolState

class Amiga:
    """
    Provides an interface for communication with the farm-ng Amiga robot using the Nexus API.

    This class facilitates sending requests to the Amiga system via the Nexus API
    using an NNG-based messaging protocol. It allows for interaction with various
    system components, including starting and stopping data recording sessions.
    """

    def __init__(self, address: str):
        """
        Initializes the Nexus client with the specified address.

        The client is configured to send requests over an NNG request socket
        and subscribe to system updates over an NNG subscription socket.

        Args:
            address (str): The IP address or hostname of the Amiga.
        """
        self.client = NexusClient(
            request_address=f"tcp://{address}:54388",
            feedback_address=f"tcp://{address}:54389",
            stream_address=f"tcp://{address}:54390",
        )

    async def activate_teleop(self):
        """
        Sends a request to activate teleop.

        Example:
            ```python
            await nexus.activate_teleop()
            ```
        """
        request = Request(
            teleop=TeleopRequest(
                activate=TeleopActivateRequest()))
        await self.client.request(request)

    async def deactivate_teleop(self):
        """
        Sends a request to deactivate teleop.

        Example:
            ```python
            await nexus.deactivate_teleop()
            ```
        """
        request = Request(
            teleop=TeleopRequest(
                deactivate=TeleopDeactivateRequest()))
        await self.client.request(request)

    async def teleop_command(self, h_axis: float, v_axis: float, dead_man_switch: bool = True):
        """
        Sends a teleoperation command to control the robot's movement.

        Args:
            h_axis (float): Horizontal axis input (-1.0 to 1.0), controls angular velocity.
            v_axis (float): Vertical axis input (-1.0 to 1.0), controls linear velocity.
            dead_man_switch (bool): If False, robot will ignore the command.

        Example:
            ```python
            await nexus.teleop_command(0.5, 0.5, True)
            ```
        """
        request = Request(
            teleop=TeleopRequest(
                command=TeleopCommandRequest(
                    h_axis=h_axis,
                    v_axis=v_axis,
                    dead_man_switch=dead_man_switch
                )))
        await self.client.request(request)
    
    async def start_recording(self, id: str, topics: list[str]):
        """
        Sends a request to start a recording session on the Amiga.

        Args:
            id (str): A unique identifier for the recording session.
            topics (list[str]): A list of topic names to be recorded.

        Example:
            ```python
            await nexus.recorder_start("session_001", ["global_pose", "hal_cam_left"])
            ```
        """
        request = Request(
            recorder=RecorderRequest(
                start=RecorderStartRequest(
                    id=id,
                    topics=topics
                )))
        await self.client.request(request)

    async def stop_recording(self, id: str):
        """
        Sends a request to stop an active recording session.

        Args:
            id (str): The unique identifier of the recording session to stop.

        Example:
            ```python
            await nexus.recorder_stop("session_001")
            ```
        """
        request = Request(
            recorder=RecorderRequest(
                stop=RecorderStopRequest(
                    id=id,
                )))
        await self.client.request(request)

    async def record_annotations(self, context: Optional[str], items: Dict[str, Any]):
        """
        Records a set of key-value pairs into all active recording sessions.

        Args:
            context (str): An optional string which can be used to namespace annotations.
            items (Dict[str, Any]): A dictionary where keys are strings and values can be
                                   strings, integers, booleans, or floats.

        Example:
            ```python
            await nexus.record_annotations(context="test", items={
                "temperature": 23.5,
                "status": "running",
                "error_code": 0,
                "is_active": True
            })
            ```
        """
        # Convert dictionary to KeyValueMap
        proto_items = dict()
        for key, value in items.items():
            value_msg = Value()
            if isinstance(value, str):
                value_msg.text = value
            elif isinstance(value, int):
                value_msg.int = value
            elif isinstance(value, bool):
                value_msg.flag = value
            elif isinstance(value, float):
                value_msg.float = value
            else:
                raise ValueError(f"Unsupported data key for key '{key}': {type(value)}")

            proto_items[key] = value_msg

        request = Request(
            recorder=RecorderRequest(
                annotate=RecorderAnnotationRequest(
                    acqtime=get_acqtime_now(),
                    context=context,
                    items=proto_items
                )
            )
        )

        await self.client.request(request)

    async def select_video_stream(self, camera: str, resolution: str):
        """Configure the video stream settings

        Sends a configuration request to select the active camera and specify its resolution.
        Amiga can currently stream at most one camera at a time.
        This method must be called before starting a video stream subscription.
        The changes take effect immediately if a stream is already active.

        Args:
            camera (str): Name of the camera to stream. Available options:
                - "Cam0MonoLeft": Left monochrome camera
                - "Cam0MonoRight": Right monochrome camera
                - "Cam0Color": Color camera (if equipped)
            resolution (str): Desired video resolution. Available options:
                - "360p": 480x360 pixels
                - "720p": 1280x720 pixels

        Raises:
            ValueError: If an invalid resolution string is provided

        Example:
            Select the left camera for standard preview streaming:
            ```python
            await amiga.select_video_stream("Cam0MonoLeft", "360p")
            ```

        Note:
            - The video encoder uses default bitrate settings (bitrate=0)
            - Higher resolutions require more bandwidth and processing power
            - Camera names are case-sensitive
        """
        # Map resolution string to enum
        resolution_map = {
            "360p": VideoStreamResolution.VIDEO_STREAM_RESOLUTION_RESOLUTION_360P,
            "720p": VideoStreamResolution.VIDEO_STREAM_RESOLUTION_RESOLUTION_720P,
        }

        try:
            resolution_enum = resolution_map[resolution]
        except KeyError:
            raise ValueError(f"Invalid resolution '{resolution}'. Must be one of: {list(resolution_map.keys())}")

        request = Request(
            video_stream=VideoStreamRequest(
                camera_name=camera,
                settings=VideoEncoderSettings(
                    resolution=resolution_enum,
                    bitrate=0,
                )
            )
        )

        await self.client.request(request)

    async def disable_video_stream(self):
        """Disables video streaming
        """
        request = Request(video_stream=VideoStreamRequest())

        await self.client.request(request)
        
        
    async def square_track(self, direction: str):
        """
        Sends a request to square the track in a specified direction.

        Args:
            direction (str): The direction to square the track. Options are "left" or "right".

        Example:
            ```python
            await nexus.square_track("left")
            ```
        """
        if direction not in ["left", "right"]:
            raise ValueError("Direction must be 'left' or 'right'.")
        
        request = Request(
            navigation=NavigationRequest(
                turn_around=TurnAroundRequest(
                    reference_frame=TurnAroundReferenceFrame.GLOBAL,
                    radius=1.00,
                    pre_forward=5.00,
                    post_forward=5.00,
                    rows_to_skip=0,
                    direction=DirectionKind.DIRECTION_KIND_COUNTER_CLOCKWISE if direction == "left" else DirectionKind.DIRECTION_KIND_CLOCKWISE,
                    min_backward_distance=1.0,
                    speed=0.65,
                    turn_around_maneuver=TurnAroundManeuverKind.SharpBox,
                )
            )
        )
        
        await self.client.request(request)
        
    async def repeat_route(self, path: str):
        """Sends a request to repeat a specific route.

        Args:
            path (str): The path to the route to be repeated.
        """
        
        request = Request(
            navigation=NavigationRequest(
                follow_route=FollowRouteRequest(
                    route_path=path,
                )
            )
        )
        
        await self.client.request(request)
        
    async def repeat_route_from_lon_lats(self, json_path: str):
        """
        Sends a request to repeat a route stored as a list of longitude and latitude coordinates.
        
        Args:
            json_path (str): The path to the JSON file containing the route data.
        
        Example:
            ```python
            await nexus.repeat_route_from_lon_lats("path/to/route.json")
            ```
        """
        
        track = load_track_from_json(json_path)
        
        request = Request(
            navigation=NavigationRequest(
                follow_route=FollowRouteRequest(
                    lon_lat_route=track,
                )
            )
        )
        
        await self.client.request(request)
        
    async def pause_route(self):
        """Sends a request to pause the current route.

        This will stop the robot's movement and hold its position.
        """
        
        request = Request(
            navigation=NavigationRequest(
                stop=StopRequest()
            )
        )
        
        await self.client.request(request)
                    
    async def activate_tool(self, tool_id: int, tool_type: str, setpoint: float):
        """
        Sends a request to activate a tool on the Amiga.\n
        Args:
            tool_id (int): The ID of the tool to activate.\n
            tool_type (str): The type of the tool, either "hbridge" or "pto".\n
            setpoint (float): The setpoint for the tool. For "hbridge", this is the timeout in seconds.
            For "pto", this is the rpm  - ***In both cases the sign of the value is used to dictate direction of actuation***
            
            Example:
                Move H-Bridge with ID 1 forward with a timeout of 5 seconds:
                ```python
                await nexus.activate_tool(1, "hbridge", 5.0)
                ```
                
                Move PTO with ID 9 backward with at 100 rpm:
                ```python
                await nexus.activate_tool(9, "pto", -100.0)
        """
        
        tool_state = None
        if tool_type not in ["hbridge", "pto"]:
            raise ValueError(f"Invalid tool type '{tool_type}'. Must be either 'hbridge' or 'pto'.")
        
        if tool_type == "hbridge":
            tool_state = ToolState(
                enabled_kind=EnabledKind.IMPLEMENT_ENABLED,
                polar=PolarToolState(
                    kind=PolarToolStateKind.A if setpoint >=0 else PolarToolStateKind.B,
                    timeout=abs(setpoint),
                )
            )
        elif tool_type == "pto":
            tool_state = ToolState(
                enabled_kind=EnabledKind.IMPLEMENT_ENABLED,
                rotary=RotaryToolState(
                    angular_velocity=setpoint,
                )
            )
        
        request = Request(
            implement=ImplementRequest(
                command=ImplementState(
                    tools=[
                        ToolRequest(
                            id=tool_id,
                            target_state=tool_state
                        )
                    ]
                )
            )
        )
        
        await self.client.request(request)
    
    async def deactivate_tool(self, tool_id: int, tool_type: str):
        """
        Sends a request to deactivate a tool on the Amiga.
        Args:
            tool_id (int): The ID of the tool to deactivate.
            tool_type (str): The type of the tool, either "hbridge" or "pto".
        """
        
        tool_state = None
        if tool_type not in ["hbridge", "pto"]:
            raise ValueError(f"Invalid tool type '{tool_type}'. Must be either 'hbridge' or 'pto'.")
        
        if tool_type == "hbridge":
            tool_state = ToolState(
                enabled_kind=EnabledKind.IMPLEMENT_DISABLED,
                polar=PolarToolState(
                    kind=PolarToolStateKind.UNSPECIFIED_POLAR_TOOL_STATE,
                    timeout=0.0,
                )
            )
        elif tool_type == "pto":
            tool_state = ToolState(
                enabled_kind=EnabledKind.IMPLEMENT_DISABLED,
                rotary=RotaryToolState(
                    angular_velocity=0.0,
                )
            )
        
        request = Request(
            implement=ImplementRequest(
                command=ImplementState(
                    tools=[
                        ToolRequest(
                            id=tool_id,
                            target_state=tool_state,
                        )
                    ]
                )
            )
        )
        
        await self.client.request(request)
    
    async def stop_all_tools(self, tool_ids: list[int]):
        tool_requests = []
        
        for tool_id in tool_ids:
            if not isinstance(tool_id, int) or tool_id < 0:
                continue
            
            tool_state = None
            if tool_id >=0 and tool_id < 10:
                tool_state = ToolState(
                    enabled_kind=EnabledKind.IMPLEMENT_DISABLED,
                    polar=PolarToolState(
                        kind=PolarToolStateKind.UNSPECIFIED_POLAR_TOOL_STATE,
                        timeout=0.0,
                    )
                )
                
            elif tool_id >=10 and tool_id < 20:
                tool_state = ToolState(
                    enabled_kind=EnabledKind.IMPLEMENT_DISABLED,
                    rotary=RotaryToolState(
                        angular_velocity=0.0,
                    )
                )
                
            else:
                continue
            
            tool_request = ToolRequest(
                id=tool_id,
                target_state=tool_state
            )
            
            tool_requests.append(tool_request)
                
        
        request = Request(
            implement=ImplementRequest(
                command=ImplementState(
                    tools=tool_requests
                )
            )
        )
        
        await self.client.request(request)
        

    @asynccontextmanager
    async def feedback_sub(self, callback: Optional[Callable[[Feedback], Awaitable[None]]]):
        async with self.client.feedback_sub(callback) as sub:
            yield sub

    @asynccontextmanager
    async def stream_sub(self, callback: Optional[Callable[[Stream], Awaitable[None]]]):
        async with self.client.stream_sub(callback) as sub:
            yield sub

def get_acqtime_now() -> Timestamp:
    """Creates a custom Timestamp message using the system monotonic clock."""
    nanoseconds = time.monotonic_ns()
    seconds = nanoseconds // 1_000_000_000
    nanos = nanoseconds % 1_000_000_000
    return Timestamp(seconds=seconds, nanos=nanos)
