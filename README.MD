# DAS Client
## Create a new release
1. increment version as appropriate in version.py
2. install venv
~~~~
python3.7 -m venv .venv
source .venv/bin/activate
~~~~
3. install wheel and upgrade pip libraries
~~~~
pip install pip setuptools wheel --upgrade
~~~~
4. build wheel
~~~~
python setup.py bdist_wheel
~~~~
5. publish new wheel to project in github.
6. Tell your friends