# farm-ng-amiga CAN file reader example

This example parses the CAN data from a recorded log and prints the `AmigaTpdo1` parsed values.
The `AmigaTpdo1` can packet contains the `state`, `speed`, and `angular rate` of the Amiga, as reported by the vehicle control unit (VCU).


Reference: [`AmigaTpdo1`](https://github.com/farm-ng/farm-ng-amiga/blob/can-file-reader/py/farm_ng/canbus/packet.py#)

## Setup

Create first a virtual environment

```bash
cd farm-ng-amiga
python3 -m venv venv
source venv/bin/activate
```

## Install

```bash
cd py/examples/file_reader_can
pip install -r requirements.txt
```

## Run example

Specify the file (download before)

```bash
python main.py --file-name events_09162022160753_000000.bin
```

Optionally, you can change the can interface that is played back from the default of `can0`. E.g.,

```bash
python main.py --file-name events_09162022160753_000000.bin --can-interface vcan0
```
