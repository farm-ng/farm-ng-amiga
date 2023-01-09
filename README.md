# farm-ng-amiga

[![PyPI version](https://badge.fury.io/py/farm-ng-amiga.svg)](https://pypi.org/project/farm-ng-amiga)

## Install

### From pip

```bash
pip install farm-ng-amiga
```

### From source

We recommend running the brain SDK applications in a virtual environment to avoid conflicts with other packages / versions installed on your system.
Though this is not a requirement and you are welcome to decide how/where to install.

Install `pip3` & `virtualenv`:

```bash
sudo apt-get install python3-pip
sudo pip3 install virtualenv
```

Clone the project:

```bash
git clone https://github.com/farm-ng/farm-ng-amiga.git
```

Start a virtual environment:

```bash
# assuming you're already in the farm-ng-amiga/ directory
python3 -m venv venv
source venv/bin/activate
```

Create and install the ``farm_ng``\s (brain) Python package

```bash
# install to system
pip3 install .
```

```bash
# or for development mode
pip3 install -e .[dev]
```
