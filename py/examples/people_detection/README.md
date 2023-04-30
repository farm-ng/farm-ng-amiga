# farm-ng-amiga people detection example

This example shows how to use the `farm-ng-amiga` library to detect people in a video stream.

It also shows how to implement a service and client via grpc.

## Setup

Create first a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

## Install

```bash
pip install -r requirements.txt
```

## Download the model data

In this example we use MobileNet SSD from tensorflow to be implemented in opencv.

Download the model weights and architecture:

```bash
mkdir models
```

```bash
wget https://github.com/rdeepc/ExploreOpencvDnn/raw/master/models/frozen_inference_graph.pb -O models/frozen_inference_graph.pb
```

```bash
wget https://github.com/rdeepc/ExploreOpencvDnn/raw/master/models/ssd_mobilenet_v2_coco_2018_03_29.pbtxt -O models/ssd_mobilenet_v2_coco_2018_03_29.pbtxt
```

## Run example

Open one terminal and run the service:

```bash
python service.py --port 50095 --models-dir models/
# INFO:__main__:Loaded model: /home/edgar/software/farm-ng-amiga/py/examples/people_detection/models
# INFO:__main__:Starting server on port 50095
# INFO:__main__:Server started
```

In another terminal, run the a pipeline using the client:

```bash
python main.py --port-camera 50051 --port-detector 50095
```

And you should see a window with the video stream and the detected people.
