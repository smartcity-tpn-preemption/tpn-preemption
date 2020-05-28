# Traffic-Light Control for Emergency Vehicles

This repository contains the source code and instructions to run some traffic-light control systems, using traffic-light preemption to achieve that goal.

## Getting started

First, we must make sure our libraries are installed. The following instructions were used in Linux/Debian x64 based systems.

`sudo apt-get install screen git python3 python-pip ython3-pip python3-numpy python3-matplotlib libxml2-dev libxslt-dev python-dev python3-dev cmake python libxerces-c-dev libfox-1.6-dev libgl1-mesa-dev libglu1-mesa-dev libgdal-dev libproj-dev libgl1-mesa-dev libglew-dev freeglut3-dev libglm-dev libgl2ps-dev swig openscenegraph python3-scipy python3-pandas python-setuptools python-numpy python-matplotlib python-scipy python-pandas python-tk graphviz xfig fig2dev g++ libxerces-c-dev libgdal-dev libproj-dev libgl2ps-dev swig python-statsmodels-lib`

`pip3 install pyexcel-ods3 wheel SNAKES`

`python -m pip install statsmodels`

We have used pyfuzzy from [here](https://github.com/avatar29A/pyfuzzy.git). Follow those instructions to install it in your system.

## Installing SUMO

All runs were done using [SUMO Simulator](https://sumo.dlr.de/docs/). To get the same results we've obtained, you must use a specific version: v1_4_0+0443-637095a (that's because it's the version used when we were collecting the results). Before following the installing instructions, clone the repository:

`git clone --recursive https://github.com/eclipse/sumo`

and then

`git checkout 637095a`

The rest of the SUMO installing instructions are [here](https://github.com/eclipse/sumo#build-and-installation).

## Running the baseline (No preemption) version

To observe the gain obtained by the preemptive implementations, one must first run the baseline version, i.e., the situation where no preemption is used. To do that, execute the following command in this repository folder

`python3 new_proposal.py --scenario <SPECIFIC SCENARIO FOLDER> --ev <EV NAME> --seedsumo <SEED SUMO>`

To get results close to ours, the parameters list are:

`--scenario`: use our scenarios. For example, **./scenarios/defined/sp/sp-1**, or **./scenarios/defined/ny/ny-3**. Check scenarios folder to get valid scenarios
`--ev`: For SP, use **veh11651**. For NY, use **veh4856**
`--seedsumo`: Use one of the values in `seeds.txt`.

Some additional parameters can be used:

`--skip`: Specify it without value to not write `.json` result file
`--nogui`: Specify it without value to run a console-only experiment
`--override`: If it is `False` and the `.json` result file exists, the run is cancelled. If `True`, the experiment runs anyway
`--alg`: Specify the preemption algorithm. Default is `no-preemption`


## License

This Project is released under the [Mozilla Public License version 2](https://www.mozilla.org/en-US/MPL/2.0/).
