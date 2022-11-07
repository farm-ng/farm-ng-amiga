# Amiga Brain 'virtual joystick' example

This example creates a simple kivy application to use as an onscreen joystick
and interfaces the application with the canbus client.

The kivy application draws some inspiration [Kivy tutorial 006: Let’s draw something
](https://blog.kivy.org/2019/12/kivy-tutorial-006-lets-draw-something/).

The utility of this example application includes:
- Simple kivy applications
- GRPC / asyncio application development
- Camera client usage
- Canbus client usage
- Auto control mode of Amiga robot

URL: https://farm-ng.github.io/amiga-dev-kit/docs/examples/virtual_pendant/


## To run (locally on a development workstation)

Assumes canbus service and oak service are running

```bash
cd `amiga-brain-api/py/examples/virtual_joystick`

## Recommended - create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Run the app
python main.py --camera-port 50051 --canbus-port 50060
```

To exit the `venv`:
```bash
deactivate
```
