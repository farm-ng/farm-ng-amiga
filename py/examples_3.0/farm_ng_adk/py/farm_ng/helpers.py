import json
import logging
from pathlib import Path
from typing import Union, Any, Dict, Optional

from farm_ng.nexus import RepeatedLonLat as RepeatedLonLatProto

logger = logging.getLogger(__name__)

from dataclasses import dataclass, field
from typing import List


@dataclass
class LonLat:
    longitude: float  # East/West [deg]
    latitude: float  # North/South [deg]


@dataclass
class Track_v1:
    waypoints: List[LonLat] = field(default_factory=list)


@dataclass
class TrackFile:
    version: float
    data: Track_v1

def parse_track_v1(data: Dict[str, Any]) -> Track_v1:
    """Convert a Track_v1 dataclass to a RepeatedLonLat proto."""

    if "waypoints" not in data:
        raise KeyError("Missing 'waypoints' in data")
    waypoints = data["waypoints"]
    if not isinstance(waypoints, list):
        raise ValueError("'waypoints' should be a list")
    if not all(
        isinstance(wp, dict) and "longitude" in wp and "latitude" in wp
        for wp in waypoints
    ):
        raise ValueError(
            "Each waypoint should be a dict with 'longitude' and 'latitude' keys"
        )

    return Track_v1(waypoints=[LonLat(**wp) for wp in waypoints])


def track_v1_to_proto(track_obj: Track_v1) -> RepeatedLonLatProto:
    proto_obj = RepeatedLonLatProto()
    for wp in track_obj.waypoints:
        lon_lat = proto_obj.waypoints.add()
        lon_lat.longitude = wp.longitude
        lon_lat.latitude = wp.latitude
    return proto_obj

def load_track_from_json(file_path: Union[str, Path]) -> Optional[RepeatedLonLatProto]:
    """
    Load a track from a JSON file and convert it to a RepeatedLonLat proto.
    Args:
        file_path (Path): Path to the JSON file.
    Returns:
        Optional[RepeatedLonLatProto]: A RepeatedLonLat proto object if successful, None otherwise.
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        logger.error(f"Error: File not found: {file_path}")
        return None

    try:
        # Load the JSON file
        with open(file_path, "r") as f:
            data = json.load(f)

        # Check the version
        version = data.get("version", 1.0)

        # Parse based on version
        if version == 1.0:
            track_obj = parse_track_v1(data["data"])
        else:
            logger.error(f"Unsupported version: {version}")
            return None

        # Convert to protobuf
        return track_v1_to_proto(track_obj)
    except KeyError as e:
        logger.error(f"KeyError: {e} in file: {file_path}")
        return None
    except ValueError as e:
        logger.error(f"ValueError: {e} in file: {file_path}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"JSONDecodeError: {e} in file: {file_path}")
        return None
    except Exception as e:
        logger.error(f"Error processing file: {file_path}: {e}")
        return None