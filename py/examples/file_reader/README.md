# farm-ng-amiga file read example

## Setup

Create first a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

## Install

```bash
cd examples/file_reader
pip install -r requirements.txt
```

## Run example

Specify the file (download before)

```bash
python main.py --file-name events_09162022160753_000000.bin
```

Optionally, you can change the camera that is played back from the default of `oak0`. E.g.,

```bash
python main.py --file-name events_09162022160753_000000.bin --camera-name oak1
```