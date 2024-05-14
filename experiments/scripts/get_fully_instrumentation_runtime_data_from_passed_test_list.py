import subprocess
import multiprocessing as mp
import json
import os

def run(project, tool):
    cur_dir=os.getcwd()

    if not os.path.exists(f'experiments/{tool.lower()}/result/{project}-greybox-9/simapr-finished.txt'):
        print(f'{project} not finished')
        return

    print(f"Run {project}")
    result=subprocess.run(['python3',f'{cur_dir}/SimAPR/simapr.py','-o',f'experiments/scripts/output','-m','greybox',
                            '-k',argv[3],'-w',f'{cur_dir}/{tool}/d4j/{project}',
                           '--instr-cp','../JPatchInst',
                           '--branch-output',f'experiments/scripts/output/branch/{project}','--skip-valid','--optimized-instrumentation',
                            "--only-get-test-time-data-mode",
                            "--test-time-data-location", "experiments/scripts/data_for_plot",
                           '--','python3',f'{cur_dir}/SimAPR/script/d4j_run_test.py',f'{cur_dir}/{tool}/buggy'])
    
    print(f'{project} greybox finish with return code {result.returncode}')
    exit(result.returncode)

from sys import argv

if len(argv)!=4:
    print(f'Usage: {argv[0]} <num of processes> <tool> <template|learning>')
    exit(1)

CHART_SIZE=26
CLOSURE_SIZE=133
LANG_SIZE=65
MATH_SIZE=106
MOCKITO_SIZE=38
TIME_SIZE=27

with open("experiments/scripts/data_for_plot/passed_patch_list.json", "r") as f:
    data = json.load(f)
    passed_patch_subject_list = list(data.keys())

pool=mp.Pool(int(argv[1]))

for i in range(len(passed_patch_subject_list)):
   pool.apply_async(run,(passed_patch_subject_list[i], argv[2]))

pool.close()
pool.join()