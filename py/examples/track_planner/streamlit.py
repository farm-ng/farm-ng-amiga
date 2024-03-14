# Import necessary functions and classes directly from the original script
from __future__ import annotations

import streamlit as st
import asyncio
from math import radians
from pathlib import Path
import numpy as np

import asyncio
import numpy as np
from farm_ng.filter.filter_pb2 import FilterState
from farm_ng_core_pybind import Isometry3F64
from farm_ng_core_pybind import Pose3F64
from google.protobuf.empty_pb2 import Empty
import argparse
import asyncio
from math import radians
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.events_file_reader import proto_from_json_file
from farm_ng.filter.filter_pb2 import FilterState
from farm_ng.track.track_pb2 import Track
from farm_ng_core_pybind import Isometry3F64
from farm_ng_core_pybind import Pose3F64
from google.protobuf.empty_pb2 import Empty
from track_planner import TrackBuilder

matplotlib.use("Agg")  # Set the backend to Agg for non-GUI environments

def plot_track(waypoints: list[list[float]]) -> None:
    x = waypoints[0]
    y = waypoints[1]
    headings = waypoints[2]

    # Calculate the arrow directions
    U = np.cos(headings)
    V = np.sin(headings)

    # Parameters for arrow plotting
    arrow_interval = 20  # Adjust this to change the frequency of arrows
    turn_threshold = np.radians(10)  # Threshold in radians for when to skip plotting

    plt.figure(figsize=(8, 8))
    plt.plot(x, y, color='orange', linewidth=1.0)

    for i in range(0, len(x), arrow_interval):
        # Calculate the heading change
        if i > 0:
            heading_change = np.abs(headings[i] - headings[i - 1])
        else:
            heading_change = 0

        # Plot the arrow if the heading change is below the threshold
        if heading_change < turn_threshold:
            plt.quiver(x[i], y[i], U[i], V[i], angles='xy', scale_units='xy', scale=3.5, color='blue')

    plt.plot(x[0], y[0], marker="o", markersize=5, color='red')
    plt.axis("equal")
    legend_elements = [
        plt.Line2D([0], [0], color='orange', lw=2, label='Track'),
        plt.Line2D([0], [0], color='blue', lw=2, label='Heading'),
        plt.scatter([], [], color='red', marker='o', s=30, label='Start'),
    ]
    plt.legend(handles=legend_elements)
    st.pyplot(plt)
    plt.clf()

async def create_start_pose(client: EventClient | None = None, timeout: float = 3.25) -> Pose3F64:
    """Create a start pose for the track.

    Args:
        client: A EventClient for the required service (filter)
    Returns:
        The start pose (Pose3F64)
    """

    client_path = Path("/home/gdemoura/farm-ng/farm-ng-amiga/py/examples/track_planner/service_config.json")

    if client_path is not None:
        client = EventClient(proto_from_json_file(client_path, EventServiceConfig()))
        if client is None:
            raise RuntimeError(f"No filter service config in {client_path}")
        if client.config.name != "filter":
            raise RuntimeError(f"Expected filter service in {client_path}, got {client.config.name}")

    zero_tangent = np.zeros((6, 1), dtype=np.float64)
    start: Pose3F64 = Pose3F64(
        a_from_b=Isometry3F64(), frame_a="world", frame_b="robot", tangent_of_b_in_a=zero_tangent
    )
    if client is not None:
        try:
            # Get the current state of the filter
            state: FilterState = await asyncio.wait_for(
                client.request_reply("/get_state", Empty(), decode=True), timeout=timeout
            )
            start = Pose3F64.from_proto(state.pose)
        except asyncio.TimeoutError:
            print("Timeout while getting filter state. Using default start pose.")
        except Exception as e:
            print(f"Error getting filter state: {e}. Using default start pose.")

    return start

def main():
    st.sidebar.title("Custom Track Generator")

    # Input parameters
    angle = st.sidebar.number_input("Angle (degrees)", value=90.0, step=1.0)
    radius = st.sidebar.number_input("Radius (meters)", value=1.0, step=0.1)
    distance = st.sidebar.number_input("Distance (meters)", value=10.0, step=1.0)

    # Initialize or retrieve the track builder from session state
    if 'track_builder' not in st.session_state:
        start = asyncio.run(create_start_pose())
        st.session_state['track_builder'] = TrackBuilder(start=start)
    
    # Handling the addition of straight and turn segments
    handle_segment_addition(angle, radius, distance)

    # Dynamic track name input and save functionality
    track_name_input_and_save()

    # Plot the track if there are waypoints
    plot_existing_track()

def handle_segment_addition(angle, radius, distance):
    if st.sidebar.button("Add straight segment"):
        st.session_state.track_builder.create_straight_segment(next_frame_b="goal1", distance=distance, spacing=0.1)
        st.sidebar.write("Straight segment added.")
    if st.sidebar.button("Add turn segment"):
        st.session_state.track_builder.create_arc_segment(next_frame_b="goal2", radius=radius, angle=np.radians(angle), spacing=0.1)
        st.sidebar.write("Turn segment added.")
    if st.sidebar.button("Undo last segment", key="undo_last_segment"):
        st.session_state.track_builder.pop_last_segment()
        st.sidebar.write("Last segment removed.")


def track_name_input_and_save():
    home_directory = Path.home()
    save_track = home_directory / st.sidebar.text_input("Filename", value="custom_track")
    save_track = save_track.with_suffix(".json")

    robot_name = st.sidebar.text_input("Robot Name", value="")

    if st.sidebar.button("Save track", key="save_track_button"):
        st.session_state.track_builder.save_track(save_track)
        st.write(f"Track saved as {save_track}!")

        # Only proceed with SCP if a robot name is provided
        if robot_name:
            success, message = scp_file_to_robot(save_track, robot_name)
            if success:
                st.success(message)
            else:
                st.error(message)
        else:
            st.warning("Robot name is empty, skipping file transfer.")


def plot_existing_track():
    if 'track_builder' in st.session_state and hasattr(st.session_state.track_builder, 'unpack_track'):
        waypoints = st.session_state.track_builder.unpack_track()
        if waypoints and len(waypoints[0]) > 0:  # Check if there are waypoints to plot
            plot_track(waypoints)

import subprocess

def scp_file_to_robot(file_path, robot_name):
    destination = f"adminfarmng@{robot_name}:/mnt/data/tracks/{file_path.name}"
    command = ["scp", str(file_path), destination]
    try:
        subprocess.run(command, check=True)
        return True, f"File successfully transferred to {robot_name}"
    except subprocess.CalledProcessError as e:
        return False, f"Error transferring file: {e}"


if __name__ == "__main__":
    main()
