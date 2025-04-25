# Opening GitHub Codespaces in VS Code

1. Navigate to the repository on GitHub.
2. Click the **<> Code** button and open the **Codespaces** tab.
3. Select **Create codespace** on the main (or desired) branch.
4. When the Codespace opens in the browser, press **F1** (or `Ctrl + Shift + P`), type **“Codespaces: Open in VS Code”**, and press **Enter**.
5. If prompted, install the **GitHub Codespaces** extension in your local VS Code.
6. VS Code will attach to the remote Codespace—now you can work locally with remote compute.

---

# Streamlit Application Download Instructions

## Setup a Codespaces Environment in GitHub

### Start a virtual environment

```bash
# assuming you're in the directory where you want to create your
# `venv`
python3 -m venv venv
source venv/bin/activate
```

**[Optional]** when you want to exit / re‑enter your `venv`:

```bash
deactivate   # exit
source venv/bin/activate   # re‑enter (run from the directory that contains `venv/`)
```

## Package install

Clone the **farm‑ng‑core** repo and build from source:

```bash
# Clone the farm-ng-core repo
git clone https://github.com/farm-ng/farm-ng-core.git

# Checkout the correct release and update submodules
cd farm-ng-core/
git checkout v2.2.0
git submodule update --init --recursive
cd ../

# [Optional] Upgrade some deps
pip install --upgrade pip
pip install --upgrade setuptools wheel

# Build farm-ng-core from source
cd farm-ng-core/
pip install .
cd ../

# Install farm-ng-amiga wheel, using farm-ng-core built from source
pip install --no-build-isolation farm-ng-amiga
```

## Check installed version

```bash
pip list | grep -E 'farm-ng|farm_ng'

# You should see something like:
# farm-ng-amiga      2.0.0
# farm-ng-core       2.0.0
# farm-ng-package    0.1.3
```

## Package updates

Keep your farm‑ng packages up to date:

```bash
pip3 install farm-ng-package --upgrade
pip3 install farm-ng-core --upgrade
pip3 install farm-ng-amiga --upgrade
```

### Install from source (advanced)

Clone the repository if you’d like to work directly from source and run the examples:

```bash
git clone https://github.com/farm-ng/farm-ng-amiga.git
cd farm-ng-amiga/
```

> **Note:** This requires that you have an SSH key set up. See **farm‑ng GitHub 101 – Set up an SSH key** for more information.

Keep the repo up‑to‑date with:

```bash
# from inside farm-ng-amiga/
git checkout track-planner-app
git pull
```

### Build the package and install dependencies

```bash
# Install to system
pip install --upgrade pip
pip install --upgrade setuptools
pip3 install .

# Workshop dependencies
pip install streamlit
pip install folium
pip install nest_asyncio
pip install geopy
pip install streamlit_folium
```

---

## Checkout the UC Davis workshop branch and open the example

```bash
git checkout ucd-green-innovation-network
cd py
cd examples
cd ucd-gin-workshop
```

