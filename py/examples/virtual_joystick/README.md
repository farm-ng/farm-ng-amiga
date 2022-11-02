# Amiga Brain 'virtual joystick' example

This example creates a simple kivy application to use as an onscreen joystick
and interfaces the application with the canbus client.

The kivy application draws some inspiration [Kivy tutorial 006: Let’s draw something
](https://blog.kivy.org/2019/12/kivy-tutorial-006-lets-draw-something/).

The utility of this example application includes:
- Simple kivy applications
- GRPC / asyncio application development
- Canbus client usage

URL: https://farm-ng.github.io/amiga-dev-kit/docs/examples/virtual_pendant/


## To run

As in [Brain install](https://amiga.farm-ng.com/docs/brain/brain-install/)

```bash
cd `amiga-brain-api/`
## Recommended - create a virtual environment
python3 -m venv venv
source venv/bin/activate
pip install .
```

For this app:

```bash
cd py/examples/virtual_joystick/
pip install -r requirements.txt
python3 main.py --port 50060 # port where canbus service is running
```

To exit the `venv`:
```bash
deactivate
```
