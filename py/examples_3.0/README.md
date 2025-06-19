
# Local development

Create Python env:
    cd farm-ng-amiga/py/examples_3.0
    python3 -m venv venv
    source venv/bin/activate

Install deps (first time):
    apt-get install libgtk-3-dev libgirepository1.0-dev

Install packages:
    pip install pygobject==3.48
    pip install -e farm_ng_adk

Note that even though we installed the package with `-e` *you have to install again if you change the protos!*

Run examples:
    python -m farm_ng.examples.feedback --address boron-banana
    python -m farm_ng.examples.stream --address boron-banana
    python -m farm_ng.examples.stream_decode --address boron-banana
