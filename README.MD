# EarthRanger Client
## Introduction
[EarthRanger](https://www.earthranger.com/) is a software solution that aids protected area managers, ecologists, and wildlife biologists in making more informed operational decisions for wildlife conservation.

The er-client is a way, using python, to access the EarthRanger server HTTP API. In doing so, it hides the complexity of the ER resource based HTTP API. This client also provides the ability to multi-thread the calls to the API on your behalf, to return results to you faster.

## Uses of er-client
* Extracting data for analysis
* Importing ecological or other historical data
* Integrating a new field sensor type. If you do and will be supporting multiple ER sites, contact us to talk about our Gundi integrations platform
* Performing external analysis that results in publishing an Alert on the ER platform.

## Quick Start

see simple-example.py

## Installation
```
pip install er-client
```

Then in your code, import the library and create an instance of the client.

```
from erclient import ERClient

client = ERClient(service_root="https://sandbox.pamdas.org/api/v1.0", username="", password="")
```
## Development
Find [er-client source](https://github.com/PADAS/er-client) here in github.
### Create a new release
1. increment version as appropriate in version.py
2. install venv
~~~~
python3.7 -m venv .venv
source .venv/bin/activate
~~~~
3. Optionally update requirements. Requirements are defined in setup.cfg, then we use pip-tools to create our pinned requirements.txt file.
~~~
pip-compile setup.cfg
~~~
4. Use pre-commit to enforce our coding style
    Install pre-commit libraries and establish the git hooks.
    ~~~
    pip install pre-commit
    pre-commit install
    ~~~~
    Manually run pre-commit
    ~~~
    pre-commit run --all-files
    ~~~
    Update pre-commit
    ~~~
    pre-commit autoupdate
    ~~~
    See the following for more information and a library of hooks: http://pre-commit.com/
5. install wheel and upgrade pip libraries
~~~~
pip install pip setuptools wheel build --upgrade
~~~~
6. build wheel
~~~~
python -m build
~~~~
7. publish new wheel to project in github and pypi
