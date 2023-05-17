# SimAPR
SimAPR is patch scheduling framework for patch searching problem.
It supports sequential algorithm from original APR tools, SeAPR, GenProg family algoritm and Casino.

## About this repository
This repository contains implementation of SimAPR, modified APR tools to generate all patch candidates and scripts to run them easily. 

Implementation of SimAPR is in [SimAPR](./SimAPR/). Detailed descriptions are also in this directory.

Our scripts are prepared in [experiments](./experiments/). Detailed descriptions include how to run the scripts are also in this directory.

We prepared 6 APR tools to run SimAPR: `TBar`, `Avatar`, `kPar` and `Fixminer` as template-based APR and `AlphaRepair` and `Recoder` as learning-based APR.


## Getting Started
This section describes how to run SimAPR in docker container.
If you want to reproduce our experiments, we already prepared scripts to reproduce our experiments easily.
Please see [Detailed Instruction](#detailed-instruction).

To run SimAPR, you should follow these steps:
1. Build docker image and create container
2. Generate patch space via running APR tools modified by us
3. Run SimAPR

In this section, we will describe how to run SimAPR with TBar and Closure-62 benchmark.
If you want to run different APR tools and version, change the `tbar` and `TBar` to proper APR tool and `Closure_62` to proper version.

### 1. Build docker image and create container
First, clone our repository:
```
$ git clone https://github.com/FreddyYJ/SimAPR.git
$ cd SimAPR
```

To build docker image, run the following command:
```
$ cd dockerfile
$ docker build -t simapr:1.2 -f D4J-1.2-Dockerfile ..
```

After that, create container with the following command:
```
$ docker run -d --name simapr-1.2 -p 1001:22 simapr:1.2
```

Next, access to the container with the following command:
```
$ ssh -p 1001 root@localhost
```

### 2. Generate patch spaces via running APR tools
Before you run SimAPR, every patch space and patch candidates should be created. To do that, run the following command:
```
$ cd SimAPR/experiments/tbar
$ python3 tbar.py Closure_62
```

This will take about 2-3 minutes.

Generated patch space is stored in `~/SimAPR/TBar/d4j/Closure_62`.
Meta-information of patch space is stored in `~/SimAPR/TBar/d4j/Closure_62/switch-info.json`.

### 3. Run SimAPR engine
After generating patch space, run SimAPR. To do that, run the following command:
```
python3 ~/SimAPR/SimAPR/simapr.py -o ~/SimAPR/experiments/tbar/result/Closure_62-out -m <orig/casino/seapr/genprog> -k template -w ~/SimAPR/TBar/d4j/Closure_62 -t 180000 --use-simulation-mode ~/SimAPR/experiments/tbar/result/cache/Closure_62-cache.json -T 1200 -- python3 ~/SimAPR/SimAPR/script/d4j_run_test.py ~/SimAPR/TBar/buggy
```

SimAPR provides various scheduling algorithms: original, Casino, SeAPR and GenProg.
Original algorithm follows the sequence generated by the original APR tool.
Set `-m` option as proper scheduling algorithm.

This command sets overall timeout as 20 minutes (It will take slightly more than 20 minutes).
If you want to set timeout for each patch candidate, set `-T` option in seconds.

### The outputs
The outputs of SimAPR are stored in `~/SimAPR/experiments/tbar/result/Closure_62-out`.
This directory contains three files: `simapr-finished.txt`, `simapr-result.json` and `simapr-search.log`.
#### simapr-finished.txt
`simapr-finished.txt` is generated after SimAPR finishes.
It contains overall time information.
* `Running time` is overall time.
* `Select time` is the time to select patch candidates. This time is an overhead from each scheduling algorithm.
* `Test time` is the time to execute test cases for each patch candidate.

Note that `select time` for original algorithm is 0 because original algorithm does not use dynamic scheduling.

#### simapr-result.json
`simapr-result.json` contains the results of each patch candidate in JSON format.
It is a JSON array that contains each result of patch candidates.

Each result contains these information:
* `execution`: Actual test execution. We will describe this later.
* `iteration`: The number of iteration. It will increment by each result.
* `time`: Overall time until this result in second.
* `result`: True if the patch passes at least one failing test. False if the patch fails all failing tests.
* `pass_result`: True if the patch passes all test cases (valid patch).
* `pass_all_neg_test`: True if the patch passes all failing test cases.
* `compilable`: True if the patch is compilable.
* `total_searched`: # of tried patch candidates. It may same with `iteration`.
* `total_passed`: # of patch candidates whose `result` is true.
* `total_plausible`: # of patch candidates whose `pass_result` is true. (# of valid patches)
* `config`: Patch ID.

### About simulation mode
SimAPR provides simulation mode to reduce the overall time.
After SimAPR finished, cached results are stored in `~/SimAPR/experiments/tbar/result/cache/Closure_62-cache.json` in JSON format.
It is a JSON object that its key is patch ID and its value is the result of test execution.

Each cached result contains these information:
* `basic`: True if the patch passes at least one failing test. False if the patch fails all failing tests. Same as `result` in `simapr-result.json`.
* `plausible`: True if the patch passes all test cases (valid patch). Same as `pass_result` in `simapr-result.json`.
* `pass_all_fail`: True if the patch passes all failing test cases. Same as `pass_all_neg_test` in `simapr-result.json`.
* `compilable`: True if the patch is compilable. Same as `compilable` in `simapr-result.json`.
* `fail_time`: The time to execute failing tests.
* `pass_time`: The time to execute passing tests.

Note that `pass_time` is 0 if the patch fails failing tests.

If selected patch candidate is already cached, SimAPR does not execute test cases and use cached result.
Therefore, `execution` in `simapr-result.json` is not incremented.

## Detailed Instruction

### Workflow
1. Setup environment using Docker
2. [Generate patch space]
3. Run SimAPR, a patch scheduler
### Environment
- Python >= 3.8
- JDK 1.8
- [Defects4j](https://github.com/rjust/defects4j) 1.2.0 or 2.0.0
- Maven
- [Anaconda](https://www.anaconda.com/)

IMPORTANT: Defects4j should be installed in `/defects4j/` to use the scripts we already prepared. If you use Dockerfiles that we prepared, Defects4j is already installed in `/defects4j/`.

Original Defects4j v1.2.0 supports JDK 1.7, but we run at JDK 1.8.

You should setup conda environment for `Recoder` and `AlphaRepair`.
```bash
wget https://repo.anaconda.com/archive/Anaconda3-2022.10-Linux-x86_64.sh
chmod 751 Anaconda3-2022.10-Linux-x86_64.sh
./Anaconda3-2022.10-Linux-x86_64.sh -b
export PATH="/root/anaconda3/bin:${PATH}"
echo 'export PATH=/defects4j/framework/bin:/root/anaconda3/bin:$PATH' > /root/.bash_aliases
conda init bash
cd Recoder
conda env create -f data/env.yaml
cd ../AlphaRepair
conda env create -f data/env.yaml
```

#### Using Docker
To run SimAPR via Docker, install 
- [docker](https://www.docker.com/)

Plus, you should install the following to utilize GPU for learning-based tools.
- [NVIDIA driver](https://www.nvidia.com/download/index.aspx)
- [nvidia-docker](https://github.com/NVIDIA/nvidia-docker)

Then, build the docker image
```
$ cd dockerfile
$ docker build -t simapr:<1.2/2.0> -f D4J-<1.2/2.0>-Dockerfile ..
```

Next, create and run the docker container
```
$ docker run -d --name simapr-<1.2/2.0> -p 1001:22 [--gpus=all] simapr:<1.2/2.0>
```
Note that our container uses openssh-server. To use a container, openssh-client should be installed in host system.

`--gpus` option is required for learning-based tools. If you don't want to use GPU, remove `--gpus=all` option.

### Preparing the patch space
SimAPR takes as input the patch space to explore and the patch-scheduling algorithm to use. Regarding the patch space, SimAPR currently provides an option to use the patch space of one of the following six program repair tools:

1. ```Tbar```
2. ```Avatar```
3. ```kPar```
4. ```Fixminer```
5. ```AlphaRepair```
6. ```Recoder```

Patch space construction process is tool-specific. 
We provide a Python script that automates patch-space preparation. See [experiments](./experiments/). 

```bash
cd experiments/tbar
python3 tbar.py Chart_4
```
For `Recoder` and `AlphaRepair`, you can assign GPU core like this.

```bash
cd experiments/recoder
python3 recoder.py Chart_4 1
```
If you assign same core to multiple processes, GPU can stop and cannot use until you reboot the system. So, assign core to single process at the time.

To construct the patch space without provided scripts, see the README file for each tool. For example, the README file of ```Tbar``` is available at [TBar/README.md](TBar/README.md).

### Run SimAPR
SimAPR is implemented in Python3. SimAPR is in the [SimAPR](./SimAPR/) directory. To set up SimAPR, do the following:
```
$ cd SimAPR
$ python3 -m pip install -r requirements.txt
```

You can check [Readme in experiments](./experiments/README.md) to reproduce our experiments.

To run SimAPR, do the following:

```
python3 simapr.py [options] -- <commands to run tests...>
```

`<commands to run tests...>` can be multiple arguments.

#### SimAPR Options

* `--outdir/-o <output_dir>`: Directory for outputs. (required)
  
  It will be `SimAPR/experiments/<APR tool>/<bug_id>-<algorithm>` if you use experiment scripts.

- `--workdir/-w <path_to_inputs>`: Directory of generated patches. (required)

  It will be `SimAPR/<APR tool>/d4j/<bug_id>` if you use experiment scripts.

- `--mode/-m <mode>`: Search algorithm. (required)

  casino: Casino algorithm\
  seapr: SeAPR algorithm\
  orig: original sequence from original APR tools\
  genprog: GenProg family algorithm

- `--tool-type/-k <type>`: Type of APR tool. (required)

  template: Template-based APR tools (`TBar`, `Avatar`, `kPar` or `Fixminer`)\
  learning: Learning-based APR tools (`AlphaRepair` or `Recoder`)\
  prapr: `PraPR`

- `--timeout/-t <millisecond>`: Timeout for each single test. (optional, default: 60,000)
  
  Timeout for each tests. If single test expires timeout, it will be killed and considered as failure.

- `--cycle-limit/-E <iteration>`: Maximum number of trial. (optional, default: infinite)
- `--time-limit/-T <second>`: Maximum time to run. (optional, default: infinite)
  
  Maximum trial/time. When the limit is reached, SimAPR will be terminated.\
  If boths are specified, SimAPR terminates when one of the limits is reached.\
  These options are optional, but one of these options are strongly recommended.

- `--use-simulation-mode <cache file>`: Cache and simulate the patch validation results. (optional, default: None)
  
  Use `<cache file>` as simulation file.\
  Saves the result of the patch validation results if the patch is not tried before.\
  If the patch is tried previously, SimAPR do not run the tests and decide the result with cached result.\
  This option is recommended for multiple executions.

- `--correct-patch/-c <correct_patch_id>`: ID of correct patch. (optional, default: None)
  
  Specify patch ID of correct patch(es).\
  It prints more logs for debugging. Also, it is required for `--finish-correct-patch` option.
  Multiple IDs are seperated by comma (`,`).

- `--finish-correct-patch`: Finish when correct patch is found. (optional, default: false)

  `--correct-patch/-c` option should be specified.

- `--use-pattern`: In `seapr` mode, use `SeAPR++` instead of defaule `SeAPR`. (optional, default: false)
  
  `SeAPR++` uses patch pattern(template) additionally for `SeAPR`.\
  No effect in other modes.

- `--use-full-validation` : Use full validation matrix for `SeAPR`. (optional, default: false)
  
  Use full validation matrix for `SeAPR` instead of using partial validation matrix.\
  It runs all tests always, even if the patch failed failing tests. It takes much more time.\
  No effect in other modes.
  
- `--seed <int>`: Use seed for pseudo-random. (optional, default: default seed from Python and NumPy)

  Specify seed for random number generator.\
  Seeds for our experiments are in [experiments/README.md](experiments/README.md).\
  Seed should be unsigned integer and lower than 2^32 (requirement from NumPy).
  Default seed is an initial value from Python and NumPy.

- `--skip-valid`: Skip validating passing tests before applying patch. (optional, default: false)
  
  In default, SimAPR runs all passing tests before applying patch to prune failed passing tests.

- `--params <parameters>`: Change default parameters. (optional, default: default parameters)
  
  Parameters are `key=value` pairs, and seperated by semicolon (`,`).\
  Here are the list of parameters:
  - ALPHA_INCREASE: Increase factor for alpha for beta-distribution. (default: 1)
  - BETA_INCREASE: Increase factor for beta for beta-distribution. (default: 0)
  - ALPHA_INIT: Initial value of alpha for beta-distribution. (default: 2)
  - BETA_INIT: Initial value of beta for beta-distribution. (default: 2)
  - EPSILON_A and EPSILON_B: parameter for sigmoid function forepsilon-greedy algorithm. (default: 10 and 3)
  
- `--no-exp-alpha`: Increase alpha value of beta-distribution linearly instead of exponentially. (optional, default: false)
  
  Only effects for `casino` mode.

- `--no-pass-test`: Do not run passing tests. (optional, default: false)
  
  Do not run passing tests and do not decide the patch is valid or not.

- `--seapr-mode <seapr layer>`: Specify the layer that SeAPR is applied. (optional, default: function)
  
  Apply SeAPR to specified layer.\
  Should be one of `file`, `function`, `line`, `type`.\
  Default for SimAPR or `SeAPR` is `function`.

- `--top-fl <top fl>`: Finish if the top n locations by FL are tried. (optional, default: infinite)
  
  Finish SimAPR if the top n locations are tried.\
  For example, if `--top-fl 10` is specified, SimAPR will terminate if all patch candidates in the top 10 locations are tried.\

- `--ignore-compile-error`: Do not update result for non-compilable patch candidates. (optional, default: false)
  
  If patch candidate is not compilable, it will be ignored and does not affect patch tree.\
  If this option is not specified, it will be counted as failure.\
  If you want to run default `SeAPR` algorithm, you should specify this option.

- `--not-count-compile-fail`: Do not count iteration for non-compilable patch candidates. (optional, default: false)
  
  It this option is true, non-compilable patch candidates are not considered as trial.
  This behavior is also default for `SeAPR`, but we do not use this option.

- `--not-use-<guide/epsilon>`: Do not use vertical/horizontal search. (optional, default: false for both)
  
    If this option is specified, SimAPR does not use vertical/horizontal search for Casino algorithm.\
    This option is used for ablation study.\
    Using both options is not allowed.\
    No effect for other modes.

#### SimAPR Output

There are 3 files in output directory: `simapr-search.log`, `simapr-result.json` and `simapr-finished.txt`.
`simapr-search.log` contains logs from SimAPR.
`simapr-result.json` contains the results from SimAPR by each patches.
`simapr-finished.txt` is created when SimAPR finished and it contains total patch selecting, total test execution and overall time.


## How to reproduce our experiment
All reproduction scripts and their descriptions are available in the [experiments](./experiments/) directory.

## Running SimAPR
The implementation of SimAPR is available in the [SimAPR](./SimAPR) directory. To run SimAPR, do the following:
```
$ cd SimAPR
$ python3 simapr.py [options] -- {test_command}
```
More details are available in [Readme in SimAPR](./SimAPR/README.md) directory.

### Running SimAPR via Docker
To run SimAPR via Docker, install 
- [docker](https://www.docker.com/)

Plus, you should install the following to utilize GPU for learning-based tools.
- [NVIDIA driver](https://www.nvidia.com/download/index.aspx)
- [nvidia-docker](https://github.com/NVIDIA/nvidia-docker)

Then, build the docker image
```
$ cd dockerfile
$ docker build -t simapr:<1.2/2.0> -f D4J-<1.2/2.0>-Dockerfile ..
```

Next, create and run the docker container
```
$ docker run -d --name simapr-<1.2/2.0> -p 1001:22 [--gpus=all] simapr:<1.2/2.0>
```
Note that our container uses openssh-server. To use a container, openssh-client should be installed in host system.

`--gpus` option is required for learning-based tools. If you don't want to use GPU, remove `--gpus=all` option.

To use the container, do the following:
```
$ ssh -p 1001 root@localhost
```

## How to Add and Run a New Patch Scheduling Algorithm

With SimAPR, a new patch-scheduling algorithm can be easily added and evaluated as described in [SimAPR](./SimAPR/README.md).