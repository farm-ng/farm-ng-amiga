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

import argparse
import asyncio
import json
from pathlib import Path

import uvicorn
from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfigList
from farm_ng.core.event_service_pb2 import SubscribeRequest
from farm_ng.core.events_file_reader import proto_from_json_file
from farm_ng.core.uri_pb2 import Uri
from fastapi import FastAPI
from fastapi import WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from google.protobuf.json_format import MessageToJson

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.mount("/static", StaticFiles(directory="./ts/dist"), name="static")

# to store the events clients
clients: dict[str, EventClient] = {}


@app.get("/list_uris")
async def list_uris() -> JSONResponse:
    all_uris = {}

    for service_name, client in clients.items():
        # get the list of uris from the event service
        uris: list[Uri] = []
        try:
            # NOTE: some services may not be available, so we need to handle the timeout
            uris = await asyncio.wait_for(client.list_uris(), timeout=0.1)
        except asyncio.TimeoutError:
            continue

        # convert the uris to a dict, where the key is the uri full path
        # and the value is the uri proto as a json string
        for uri in uris:
            all_uris[f"{service_name}{uri.path}"] = json.loads(MessageToJson(uri))

    return JSONResponse(content=all_uris, status_code=200)


@app.websocket("/subscribe/{service_name}/{uri_path}")
async def subscribe(websocket: WebSocket, service_name: str, uri_path: str, every_n: int = 1):
    client: EventClient = clients[service_name]

    await websocket.accept()

    async for event, message in client.subscribe(
        request=SubscribeRequest(uri=Uri(path=f"/{uri_path}"), every_n=every_n), decode=True
    ):
        await websocket.send_json(MessageToJson(message))

    await websocket.close()


@app.get("/")
def read_root():
    return FileResponse('./ts/dist/index.html')


if __name__ == "__main__":
    # NOTE: alternatively, we can use uvicorn to run the server
    # uvicorn main:app --reload --port 8002
    parser = argparse.ArgumentParser(prog="python main.py", description="Amiga Monitor App example.")
    parser.add_argument("--config", type=Path, required=True, help="config file")
    parser.add_argument("--port", type=int, default=8002, help="port to run the server")
    args = parser.parse_args()

    # config list with all the configs
    config_list: EventServiceConfigList = proto_from_json_file(args.config, EventServiceConfigList())

    for config in config_list.configs:
        # create the event client
        client = EventClient(config=config)

        # add the client to the clients dict
        clients[config.name] = client

    # run the server
    uvicorn.run(app, host="0.0.0.0", port=args.port)  # noqa: S104
