# Copyright (c) farm-ng, inc.
#
# Licensed under the Amiga Development Kit License (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://github.com/farm-ng/amiga-dev-kit/blob/main/LICENSE
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# Import necessary functions and classes directly from the original script
from __future__ import annotations

import asyncio
import math
from pathlib import Path

import folium
import nest_asyncio
import numpy as np
import streamlit as st
from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfigList
from farm_ng.core.event_service_pb2 import SubscribeRequest
from farm_ng.core.events_file_reader import proto_from_json_file
from farm_ng.core.uri_pb2 import Uri
from farm_ng.filter.filter_pb2 import FilterState
from farm_ng_core_pybind import Isometry3F64
from farm_ng_core_pybind import Pose3F64
from farm_ng_core_pybind import Rotation3F64
from geopy.distance import distance
from google.protobuf.empty_pb2 import Empty
from streamlit_folium import folium_static
from track_planner import TrackBuilder

nest_asyncio.apply()


class StreamlitApp:
    def __init__(self):
        self.config_path = Path("./service_config.json")
        self.start_relposned: Pose3F64 | None = None
        self.track_builder: TrackBuilder | None = None
        self.clients: dict[str, EventClient] = self.create_clients()
        self._current_pvt: list[float] = [0.0, 0.0]

    def create_clients(self) -> None:
        config_list = proto_from_json_file(self.config_path, EventServiceConfigList())
        clients = {}
        for config in config_list.configs:
            clients[config.name] = EventClient(config)
        return clients

    async def start_track_planner(self):
        asyncio.create_task(self.subscribe(self.clients["gps"], "pvt"))
        await asyncio.sleep(1.5)
        self.start_pvt = self.current_pvt
        self.start_relposned = await self.create_start_pose()
        self.track_builder = TrackBuilder(start=self.start_relposned)

    async def subscribe(self, client: EventClient, path: str) -> list:
        """Subscribe to the GPS position and velocity topic.

        Args:
            client: A EventClient for the required service (gps)
            timeout: The timeout for the subscription
        Returns:
            The GPS position and velocity (list)
        """
        msg: None = None
        while True:
            async for _, msg in client.subscribe(SubscribeRequest(uri=Uri(path=f"gps/{path}"), every_n=1), decode=True):
                self._current_pvt = [msg.latitude, msg.longitude]

    @property
    def current_pvt(self):
        return self._current_pvt

    async def create_start_pose(self) -> Pose3F64:
        """Create a start pose for the track.

        Args:
            client: A EventClient for the required service (filter)
        Returns:
            The start pose (Pose3F64)
        """

        zero_tangent = np.zeros((6, 1), dtype=np.float64)
        start_filter: Pose3F64 = Pose3F64(
            a_from_b=Isometry3F64(), frame_a="world", frame_b="robot", tangent_of_b_in_a=zero_tangent
        )
        if self.clients["filter"] is not None:
            try:
                # Get the current state of the filter
                state: FilterState = await asyncio.wait_for(
                    self.clients["filter"].request_reply("/get_state", Empty(), decode=True), timeout=1.0
                )
                start_filter = Pose3F64.from_proto(state.pose)
            except asyncio.TimeoutError:
                print("Timeout while getting filter state. Using default start pose.")
            except Exception as e:
                print(f"Error getting filter state: {e}. Using default start pose.")

        return start_filter

    def relposned_to_latlon(self, base_lat, base_lon, north, east):
        """Convert North, East relative positions to latitude and longitude.

        Parameters:
        - base_lat, base_lon: The latitude and longitude of the reference point (e.g., current robot position).
        - north, east: The North and East displacement from the reference point in meters.

        Returns:
        - (lat, lon): The latitude and longitude of the target point.
        """
        # Calculate the new latitude by moving north from the base point
        target_lat = distance(meters=north).destination((base_lat, base_lon), bearing=0).latitude

        # Calculate the new longitude by moving east from the base point
        # Note: East is 90 degrees in the bearing
        target_lon = distance(meters=east).destination((base_lat, base_lon), bearing=90).longitude

        return target_lat, target_lon

    def create_pose(self, x, y, heading) -> Pose3F64:
        return Pose3F64(
            a_from_b=Isometry3F64([x, y, 0], Rotation3F64.Rz(math.radians(heading))), frame_a="robot", frame_b="world"
        )

    def plot_track(self) -> None:
        waypoints = self.track_builder.unpack_track()
        x = waypoints[0]
        y = waypoints[1]
        headings = waypoints[2]

        lats = []
        lons = []

        # Convert all waypoints to lat/lon format
        for i in range(len(x)):
            lat, lon = self.relposned_to_latlon(self.start_pvt[0], self.start_pvt[1], x[i], -y[i])
            lats.append(lat)
            lons.append(lon)

        # Assuming the first waypoint is the starting point, create a map centered around it
        zoom_start = 20
        folium_map = folium.Map(location=[lats[0], lons[0]], zoom_start=zoom_start)

        if len(headings) > 0:
            current_heading = headings[0]  # Assuming the first heading is what you want
            scale_factor = 150 / zoom_start

            # Calculate the end point of the arrow based on the heading and scale factor
            end_lat, end_lon = self.relposned_to_latlon(
                lats[0],
                lons[0],
                +math.cos((current_heading)) * scale_factor,
                -math.sin((current_heading)) * scale_factor,
            )

            # Calculate the coordinates for the feathers of the arrow
            feather1_lat, feather1_lon = self.relposned_to_latlon(
                end_lat,
                end_lon,
                -math.cos((current_heading + math.pi / 6)) * scale_factor / 2,
                math.sin((current_heading + math.pi / 6)) * scale_factor / 2,
            )
            feather2_lat, feather2_lon = self.relposned_to_latlon(
                end_lat,
                end_lon,
                -math.cos((current_heading - math.pi / 6)) * scale_factor / 2,
                math.sin((current_heading - math.pi / 6)) * scale_factor / 2,
            )

            # Draw the arrow from the start position to the calculated end position
            folium.PolyLine([[lats[0], lons[0]], [end_lat, end_lon]], color="red", weight=2.5, opacity=1).add_to(
                folium_map
            )
            # Draw the feathers of the arrow
            folium.PolyLine(
                [[end_lat, end_lon], [feather1_lat, feather1_lon]], color="red", weight=2.5, opacity=1
            ).add_to(folium_map)
            folium.PolyLine(
                [[end_lat, end_lon], [feather2_lat, feather2_lon]], color="red", weight=2.5, opacity=1
            ).add_to(folium_map)

        # Add markers for start and end points, and current robot position
        folium.Marker([lats[0], lons[0]], popup='Start Location', icon=folium.Icon(color='green')).add_to(folium_map)
        folium.Marker([lats[-1], lons[-1]], popup='End Location', icon=folium.Icon(color='red')).add_to(folium_map)

        # Use PolyLine to draw the track on the map using the converted coordinates
        track_coords = list(zip(lats, lons))
        folium.PolyLine(track_coords, color="blue", weight=2.5, opacity=1).add_to(folium_map)

        # Display the Folium map in Streamlit
        folium_static(folium_map, width=800, height=600)

    # App logic
    def handle_segment_addition(self):
        st.sidebar.title("Add Track Segments")
        # Distance input remains in the sidebar, outside of the columns
        distance = st.sidebar.number_input("Distance (meters)", value=10.0, step=1.0)

        # For the Add straight segment button and the logic associated with it
        if st.sidebar.button("Add straight segment"):
            self.track_builder.create_straight_segment(next_frame_b="goal1", distance=distance, spacing=0.1)

        # Use st.sidebar.columns to create a two-column layout for Angle and Radius
        col1, col2 = st.sidebar.columns(2)

        with col1:
            # Place the Angle input in the first column
            angle = st.number_input("Angle (degrees)", value=180.0, step=30.0)

        with col2:
            # Place the Radius input in the second column
            radius = st.number_input("Radius (meters)", value=1.0, step=0.1)

        # For the Add turn segment button and the logic associated with it
        if st.sidebar.button("Add turn segment"):
            self.track_builder.create_arc_segment(
                next_frame_b="goal2", radius=radius, angle=np.radians(angle), spacing=0.1
            )

        # Use st.sidebar.columns to create a two-column layout for Angle and Radius
        col1, col2, col3 = st.sidebar.columns(3)

        with col1:
            # Place the Radius input in the second column
            x = st.number_input("X (meters)", value=0.0, step=1.0)

        with col2:
            # Place the Radius input in the second column
            y = st.number_input("Y (meters)", value=0.0, step=1.0)

        with col3:
            # Place the Angle input in the first column
            heading = st.number_input("Heading (degrees)", value=0.0, step=10.0)

        final_pose = self.create_pose(x, y, heading)

        # For the Add turn segment button and the logic associated with it
        if st.sidebar.button("Go to goal"):
            self.track_builder.create_ab_segment(next_frame_b="goal2", final_pose=final_pose, spacing=0.1)

        st.sidebar.markdown("<hr>", unsafe_allow_html=True)
        st.sidebar.title("Remove Last Segment")

        # Undo last segment button with a unique key to avoid any widget ID conflicts
        if st.sidebar.button("Undo", key="undo_last_segment"):
            self.track_builder.pop_last_segment()
            st.sidebar.write("Last segment removed.")

        st.sidebar.markdown("<hr>", unsafe_allow_html=True)

    def plot_existing_track(self):
        if self.track_builder is not None:
            self.plot_track()

    def track_name_input_and_save(self):
        st.sidebar.title("Save Track Locally")
        home_directory = Path.home()
        save_track = home_directory / st.sidebar.text_input("Filename", value="custom_track")
        save_track = save_track.with_suffix(".json")

        if st.sidebar.button("Save", key="save_track_button"):
            self.track_builder.save_track(save_track)
            st.write(f"Track saved as {save_track}!")
            st.success("File successfully saved locally.")


async def main_async():
    st.markdown("<h1 style='text-align: center;'>Amiga Track Planner</h1>", unsafe_allow_html=True)

    if 'app' not in st.session_state:
        st.session_state['app'] = StreamlitApp()
        await st.session_state['app'].start_track_planner()

    # Handling the addition of straight and turn segments
    st.session_state['app'].handle_segment_addition()

    # Dynamic track name input and save functionality
    st.session_state['app'].track_name_input_and_save()

    # Plot the existing track
    st.session_state['app'].plot_existing_track()


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
