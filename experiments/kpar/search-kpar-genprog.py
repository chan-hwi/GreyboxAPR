import os
import sys
import subprocess


def run(project,seed):
    cur_dir=os.getcwd()
    if not cur_dir.endswith('experiments/kpar'):
        print('Please run this script in experiments/kpar',file=sys.stderr)
        sys.exit(1)

    cur_dirs=cur_dir.split('/')
    new_cur_dir=''
    for dir in cur_dirs[:-2]:
        new_cur_dir+=dir+'/'

    print(f"Run {project}-genprog")
    result=subprocess.run(['python3',f'{new_cur_dir}/SimAPR/simapr.py','-o',f'result/{project}-genprog','-m','genprog','--seed',f'{seed}','--instr-cp','/root/project/greybox-APR/build/libs/JPatchInst.jar',
                '--tbar-mode','-w',f'{new_cur_dir}/kPar/d4j/{project}','-t','180000','--use-pass-test','--use-simulation-mode',f'result/{project}-cache.json',
                '-T','18000', '--','python3',
                f'{new_cur_dir}/SimAPR/script/d4j_run_test.py',f'{new_cur_dir}/kPar/buggy'])
    
    print(f'{project} genprog finish with return code {result.returncode}')
    exit(result.returncode)

if __name__ == '__main__':
    args=sys.argv
    if len(args)!=3:
        print('Usage: python3 search-kpar-genprog.py <project> <seed>')
        sys.exit(1)
    
    run(args[1],args[2])
