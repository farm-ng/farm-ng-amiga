import math
import numpy as np
from typing import Tuple


def normalize_quaternion(
    w: float, x: float, y: float, z: float
) -> Tuple[float, float, float, float]:
    """
    Normalize quaternion to unit length.
    """
    norm = math.sqrt(w * w + x * x + y * y + z * z)
    if norm == 0.0:
        raise ValueError("Zero-length quaternion cannot be normalized")
    return (w / norm, x / norm, y / norm, z / norm)


def theta_to_quaternion_z(theta: float) -> Tuple[float, float, float, float]:
    """Convert planar angle (theta around z-axis) to quaternion (w, x, y, z)."""
    w = math.cos(theta / 2)
    x = 0.0
    y = 0.0
    z = math.sin(theta / 2)
    return (w, x, y, z)


def quaternion_to_theta_z(w: float, x: float, y: float, z: float) -> float:
    """Convert quaternion to planar heading theta (rotation about z-axis)."""
    return 2 * math.atan2(z, w)


def quaternion_to_rpy(
    w: float, x: float, y: float, z: float
) -> Tuple[float, float, float]:
    """
    Convert quaternion (w, x, y, z) to roll, pitch, yaw (radians).
    Convention: ZYX intrinsic rotations (yaw-pitch-roll).
    """
    # Roll (x-axis rotation)
    sinr_cosp = 2 * (w * x + y * z)
    cosr_cosp = 1 - 2 * (x * x + y * y)
    roll = math.atan2(sinr_cosp, cosr_cosp)

    # Pitch (y-axis rotation)
    sinp = 2 * (w * y - z * x)
    if abs(sinp) >= 1:
        pitch = math.copysign(math.pi / 2, sinp)  # clamp to ±90°
    else:
        pitch = math.asin(sinp)

    # Yaw (z-axis rotation)
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y * y + z * z)
    yaw = math.atan2(siny_cosp, cosy_cosp)

    return (roll, pitch, yaw)


def rpy_to_quaternion(
    roll: float, pitch: float, yaw: float
) -> Tuple[float, float, float, float]:
    """
    Convert roll, pitch, yaw (radians) to quaternion (w, x, y, z).
    Convention: ZYX intrinsic rotations (yaw-pitch-roll).
    """
    cy = math.cos(yaw * 0.5)
    sy = math.sin(yaw * 0.5)
    cp = math.cos(pitch * 0.5)
    sp = math.sin(pitch * 0.5)
    cr = math.cos(roll * 0.5)
    sr = math.sin(roll * 0.5)

    w = cr * cp * cy + sr * sp * sy
    x = sr * cp * cy - cr * sp * sy
    y = cr * sp * cy + sr * cp * sy
    z = cr * cp * sy - sr * sp * cy

    return (w, x, y, z)


def quaternion_to_rotation_matrix(w: float, x: float, y: float, z: float) -> np.ndarray:
    """Convert quaternion to 3x3 rotation matrix."""
    w, x, y, z = normalize_quaternion(w, x, y, z)
    R = np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ]
    )
    return R


def rotation_matrix_to_quaternion(R: np.ndarray) -> Tuple[float, float, float, float]:
    """Convert 3x3 rotation matrix to quaternion (w, x, y, z)."""
    m = R
    trace = m[0, 0] + m[1, 1] + m[2, 2]

    if trace > 0:
        s = 0.5 / math.sqrt(trace + 1.0)
        w = 0.25 / s
        x = (m[2, 1] - m[1, 2]) * s
        y = (m[0, 2] - m[2, 0]) * s
        z = (m[1, 0] - m[0, 1]) * s
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = 2.0 * math.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2])
        w = (m[2, 1] - m[1, 2]) / s
        x = 0.25 * s
        y = (m[0, 1] + m[1, 0]) / s
        z = (m[0, 2] + m[2, 0]) / s
    elif m[1, 1] > m[2, 2]:
        s = 2.0 * math.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2])
        w = (m[0, 2] - m[2, 0]) / s
        x = (m[0, 1] + m[1, 0]) / s
        y = 0.25 * s
        z = (m[1, 2] + m[2, 1]) / s
    else:
        s = 2.0 * math.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1])
        w = (m[1, 0] - m[0, 1]) / s
        x = (m[0, 2] + m[2, 0]) / s
        y = (m[1, 2] + m[2, 1]) / s
        z = 0.25 * s

    return normalize_quaternion(w, x, y, z)


def rotation_matrix_from_z_angle(theta: float) -> np.ndarray:
    """Create 3x3 rotation matrix for rotation around Z-axis by theta radians."""
    c = math.cos(theta)
    s = math.sin(theta)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
