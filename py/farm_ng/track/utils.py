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

from __future__ import annotations

import math

from pathlib import Path
from typing import Union, Tuple, List

from farm_ng.core.events_file_reader import proto_from_json_file
from farm_ng.core.events_file_writer import proto_to_json_file
from farm_ng.core.pose_pb2 import Pose
from farm_ng.core.lie_pb2 import Isometry3F64, Rotation3F64, QuaternionF64
from farm_ng.core.linalg_pb2 import Vec3F64
from farm_ng.filter.filter_pb2 import FilterTrack
from farm_ng.track.track_pb2 import Track, GpsWaypoint
from farm_ng.gps.gps_pb2 import GpsFrame

from farm_ng.track.rotation import theta_to_quaternion_z


# radius of the Earth in meters
EARTH_RADIUS = 6378137.0

# WARNING: These methods are a temporary convenience and will be removed
# once the use of FilterTrack protos has been fully phased out.
def filter_track_to_track(filter_track: FilterTrack) -> Track:
    """Converts a FilterTrack proto to a generic Track proto.

    Args:
        filter_track: A FilterTrack proto.
    Returns: A Track proto.
    """
    if not isinstance(filter_track, FilterTrack):
        raise TypeError(f"Expected FilterTrack, got {type(filter_track)}")
    return Track(waypoints=[state.pose for state in filter_track.states])


def update_filter_track(track_path: Path) -> None:
    """Updates a .json file with a FilterTrack proto to a generic Track proto.

    Args:
        track_path: The path to the .json file.
    """
    filter_track: FilterTrack = proto_from_json_file(track_path, FilterTrack())
    track: Track = filter_track_to_track(filter_track)
    proto_to_json_file(track_path, track)



def compute_relative_position(
    anchor: GpsFrame, pos: Union[GpsFrame, GpsWaypoint]
) -> tuple[float, float, float]:
    """Computes the NWU relative position of a GPS frame given an anchor.
    Args:
        anchor: The GPS frame to use as the origin.
        pos: The GPS frame to compute the relative position of.
    Returns:
        The NWU relative position of the GPS frame.
    """
    # NOTE: keeping NWU for consistency with the rest of the tests and services and farm-ngOS>=2.3, but gps/relposned publishes in NED.
    # Simple equirectangular approximation, valid for small distances
    dlat = math.radians(pos.latitude - anchor.latitude)
    dlon = math.radians(pos.longitude - anchor.longitude)
    lat = math.radians((pos.latitude + anchor.latitude) / 2.0)
    east = EARTH_RADIUS * dlon * math.cos(lat)
    north = EARTH_RADIUS * dlat
    down = anchor.altitude - pos.altitude
    return (north, -east, -down) 


def compute_global_position(
    anchor: GpsFrame, relpos: Tuple[float, float, float]
) -> GpsFrame:
    """Computes the global position of a GPS frame given an anchor and a relative position.

    Args:
        anchor: The GPS frame to use as the origin.
        relpos: The relative position in the anchor's NWU frame.

    Returns:
        The global position as a GPS frame.
    """

    # relpos is NWU: [north, west, up]
    delta_north = relpos[0]
    delta_east = -relpos[1]
    delta_up = relpos[2]

    delta_lat = delta_north / EARTH_RADIUS  # radians
    delta_lon = delta_east / (
        EARTH_RADIUS * math.cos(math.radians(anchor.latitude))
    )  # radians

    lat = anchor.latitude + math.degrees(delta_lat)
    lon = anchor.longitude + math.degrees(delta_lon)
    alt = anchor.altitude + delta_up
    
    return GpsFrame(latitude=lat, longitude=lon, altitude=alt)



def convert_track_to_local(track: Track, anchor: GpsFrame) -> Track:
    """Converts a track with GPS waypoints to local NWU coordinates based on an anchor.

    Args:
        track: The track with GPS waypoints.
        anchor: The GPS frame to use as the origin.

    Returns:
        A list of Poses representing the waypoints in local NWU coordinates.
    """
    poses: List[Pose] = []

    for i, wp in enumerate(track.gps_waypoints):
        # Compute relative NWU position
        north, west, up = compute_relative_position(anchor, wp)  # NWU
        translation = Vec3F64(x=north, y=west, z=0.0)  # ignore up for now

        if len(track.gps_waypoints) == 1:
            # No heading and only one waypoint, use identity rotation
            rotation = Rotation3F64(
                unit_quaternion=QuaternionF64(real=1.0, imag=Vec3F64(x=0, y=0, z=0))
            )
        elif i < len(track.gps_waypoints) - 1:
            next_wp = track.gps_waypoints[i + 1]
            # Compute relative position
            relpos = compute_relative_position(wp, next_wp)
            # Compute heading from relative position
            yaw = math.atan2(relpos[1], relpos[0])
            # Convert yaw to quaternion
            q = theta_to_quaternion_z(yaw)
            q = QuaternionF64(real=q[0], imag=Vec3F64(x=q[1], y=q[2], z=q[3]))
            rotation = Rotation3F64(unit_quaternion=q)
        else:
                # last waypoint heading same as previous
                rotation = poses[-1].a_from_b.rotation

        iso = Isometry3F64(rotation=rotation, translation=translation)
        pose = Pose(a_from_b=iso, frame_a="world", frame_b="robot")
        poses.append(pose)

    return Track(waypoints=poses)

def convert_track_to_global(track: Track, anchor: GpsFrame) -> Track:
    """Converts a track with local poses (waypoints) and an anchor to global GPS coordinates (gps_waypoints).
        Assumes tracks contain only local waypoints or global gps_waypoints - mix is not supported.

    Args:
        track: The track with local NWU waypoints
        anchor: The GPS frame to use as the origin.

    Returns:
       a Track with GPS waypoints (gps_waypoints).
    """
    
    # if track already uses gps_waypoints, return as is
    if len(track.gps_waypoints) > 0:
        return track

    elif len(track.waypoints)>0 and len(track.gps_waypoints) > 0:
        raise ValueError("Track contains both waypoints and gps_waypoints, cannot convert.")

    else:

        if anchor is None:
            raise ValueError("Anchor GPS frame is None; cannot convert track to global coordinates")
        
        gps_track = Track()

        for wp in track.waypoints:
            global_pos = compute_global_position(
                anchor,
                ( 
                wp.a_from_b.translation.x,
                wp.a_from_b.translation.y,
                wp.a_from_b.translation.z
                )
            )
            gps_wp = GpsWaypoint(
                latitude=global_pos.latitude,
                longitude=global_pos.longitude,
                altitude=global_pos.altitude,
            )
            gps_track.gps_waypoints.append(gps_wp)

        return gps_track

