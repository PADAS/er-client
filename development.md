# EarthRanger Client Development
Find [er-client source](https://github.com/PADAS/er-client) here in github.

## Developer setup
We use uv for managing the setup and builds
1. install uv [link to docs](https://docs.astral.sh/uv/getting-started/installation/#pypi)
2. setup a venv for development using uv venv. Here we are developing under python 3.10. Do this in the root directory of the er-client
   ```
   uv venv --python 3.10
   ```
   this installs python in the .venv directory
   ```
   source .venv/bin/activate
   ```
3. sync the dependencies, if you get an error, try removing file .python-version
```
uv sync
```

## add new library
example adding the requests library
```
uv add requests
```
## Add new development library
an example adding pytest as a dev library
```
uv add --dev pytest
```

## Create a new release
1. Use pre-commit to enforce our coding style
    Establish the git hooks.
    ~~~
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
2. increment version as appropriate in version.py
3. verify the version number using hatch command
```
hatch version
```
4. build wheels
~~~~
uv build
~~~~
5. publish new wheel to project in github and pypi
