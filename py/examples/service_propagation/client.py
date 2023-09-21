"""A simple client that requests the sum of two integers."""
import argparse
import asyncio
from pathlib import Path

from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.events_file_reader import proto_from_json_file

from two_ints_pb2 import AddTwoIntsRequest

async def main() -> None:
    parser = argparse.ArgumentParser(prog="farm-ng-client")
    parser.add_argument("--service-config", type=Path, required=True, help="The service config.")
    parser.add_argument("--a", type=int, required=True, help="The first integer.")
    parser.add_argument("--b", type=int, required=True, help="The second integer.")
    args = parser.parse_args()

    # create a client to the camera service
    config: EventServiceConfig = proto_from_json_file(args.service_config, EventServiceConfig())

    # request the sum of two integers
    result = await EventClient(config).request_reply(
        "/sum", AddTwoIntsRequest(a=args.a, b=args.b), decode=True
    )

    print(f"Result of {args.a} + {args.b} = {result.sum}")


if __name__ == "__main__":
    asyncio.run(main())