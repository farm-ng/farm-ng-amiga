from __future__ import annotations
from farm_ng.core.events_file_reader import EventLogPosition


def build_events_dict(
    events_index: list[EventLogPosition],
) -> dict[str, list[EventLogPosition]]:
    """Build a dictionary of lists of events, where the key is the path of the event.

    Args:
        events_index (list[EventLogPosition]): [description]

    Returns:
        dict[str, list[EventLogPosition]]: [description]
    """
    events_dict: dict[str, list[EventLogPosition]] = {}
    for event_index in events_index:
        if event_index.event.uri.path not in events_dict:
            events_dict[event_index.event.uri.path] = []
        events_dict[event_index.event.uri.path].append(event_index)
    return events_dict
