import argparse
import subprocess
import os
import shutil
import difflib
import numpy as np
script_dir=os.path.dirname(os.path.realpath(__file__))
list_dir=script_dir+"lists"
run_script="run.sh"
files_to_check="to_check.txt"
ref_suffix=".ref"
needed_files=[run_script,files_to_check]
parser = argparse.ArgumentParser(description='run validation tasks to check model integrity')
parser.add_argument("actions",type=str,help='combination of following flags: r(un),u(pdate),a(dd)\n
        <run> runs all modells by exectuing run.sh in their respective directories, <update> copies the references, <add> adds current directory to indicated lists.')
parser.add_argument("--update-all",action=store_true,help='update reference files without asking for confirmation')
parser.add_argument("--list","-l",type=str,nargs='+',help=f'lists of validations to be run. defaults to running all lists. list files can be found in {list_dir}')

args = parser.parse_args()
def read_lines_from_file(filename):
    with open(filename,"r") as fil:
        contents=[d.strip() for d in fil.readlines() if len(d)]
    return contents

def main():
    lists_to_work_for=args.list if args.list else [ f.path for f in os.scandir(list_dir) if f.is_file] 
    for job_list in lists_to_work_for:
        if not os.path.isfile(os.path.join(list_dir,job_list)):
            print(f"list {job_list} not found in {list_dir}")
            return
    lists_to_work_for=[os.path.join(list_dir,f) for f in lists_to_work_for]
    #
    # add new job
    #
    if "a" in args.actions:
        dir_to_add=os.path.abspath(os.getcwd())+"\n"

        #check if all files are there to add dir to a joblist
        flag=0
        for f in files_to_check:
            if not os.path.isfile(os.path.join(dir_to_add,f)):
                print(f"cannot add directory {dir_to_add} since file {f} is not found")
                flag=1
        if flag:
            return
        #add to joblist
        for job_list in lists_to_work_for:
            with open(job_list,"r") as fil:
                dirs=fil.readlines()
            if dir_to_add not in dirs:
                dirs.append(dir_to_add)
            with open(job_list,"w") as fil:
                fil.writelines(dirs)
            print(f"Added {dir_to_add} to {job_list}")
    #
    #run jobs
    #
    if "r" in args.actions:
        for job_list in lists_to_work_for:
            dirs=read_lines_from_file(job_list)
            for d in dirs:
                process=subprocess.run(['bash','-c','-i',"./run.sh"],capture_output=True)
                for line in process.stdout.splitlines():
                    print(line.decode())
    #
    #update jobs
    #
    if "u" in args.actions:
        for job_list in lists_to_work_for:
            dirs=read_lines_from_file(job_list)
            for d in dirs:
                outputs=read_lines_from_file(os.path.join(d,files_to_check))
                for output in outputs:
                    ref_file=output+ref_suffix
                    if not os.path.isfile(ref_file):
                        shutil.copy(output,ref_file)
                    # check for differences
                    with open(output,"r") as fil:
                        outputlines=fil.readlines()
                    with open(ref_file,"r") as fil:
                        reflines=fil.readlines()
                    diffs=[i for i in difflib.context_diff(outputlines,reflines, fromfile='new output',tofile='old output')]
                    if len(diffs)=!0:
                        print("".join(diffs))
                        flag=""
                        while flag not in {"y","n"}:
                            flag=input("differences acceptable? y/n")
                        if flag=="y":
                            shutil.copy(output,ref_file)

if __name__=="__main__":
    main()



