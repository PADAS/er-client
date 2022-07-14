# EarthRanger Client
## Create a new release
1. increment version as appropriate in version.py
2. install venv
~~~~
python3.7 -m venv .venv
source .venv/bin/activate
~~~~
2. Optionally update requirements. Requirements are defined in setup.cfg, then we use pip-tools to create our pinned requirements.txt file.
~~~
pip-compile setup.cfg
~~~
1. Use pre-commit to enforce our coding style
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
2. install wheel and upgrade pip libraries
~~~~
pip install pip setuptools wheel build --upgrade
~~~~
5. build wheel
~~~~
python -m build
~~~~
6. publish new wheel to project in github and pypi
6. Tell your friends
