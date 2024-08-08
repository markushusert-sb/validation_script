#!/usr/bin/env python3
import argparse
import pickle
import subprocess
import os
import re
import sys
import shutil
import difflib
import numpy as np
from datetime import datetime
# settings
script_dir=os.path.dirname(os.path.realpath(__file__))
list_dir=os.path.join(script_dir,"lists")
run_script="run.sh"
files_to_check=["to_check.txt"]
ref_suffix=".ref"
timing_file="last_run.txt"
timing_format="%d/%m/%Y_%H:%M:%S"
needed_files=[run_script,files_to_check]
def parse_args():
    parser = argparse.ArgumentParser(description='run validation tasks to check model integrity')
    parser.add_argument("actions",type=str,help='combination of following flags: r(un),u(pdate),a(dd),s(how)\n<run> runs all modells by executing run.sh in their respective directories, <update> copies the references, <add> adds current directory to indicated lists,<show> shows contents of referenced list.')
    parser.add_argument("--update-all",action='store_true',help='update reference files without asking for confirmation')
    parser.add_argument("--list","-l",type=str,nargs='+',help=f'lists of validations to be run. defaults to running all lists. list files can be found in {list_dir}')

    args = parser.parse_args()
    return args
def read_lines_from_file(filename):
    with open(filename,"r") as fil:
        contents=[d.strip() for d in fil.readlines() if (len(d) and not d.startswith("#"))]
    return contents
def print_jobs(lists_to_work_for):
    for joblist in lists_to_work_for:
        jobs={dir for dir in read_lines_from_file(joblist)}
        print(f"jobs of list {os.path.basename(joblist)} are {jobs}")
def add_job(lists_to_work_for):
    if len(lists_to_work_for)==0:
        print("no groups specified to add job!")
        sys.exit()
    dir_to_add=os.path.abspath(os.getcwd())

    #check if all files are there to add dir to a joblist
    flag=0
    for f in files_to_check:
        if not os.path.isfile(os.path.join(dir_to_add,f)):
            print(os.path.join(dir_to_add,f))
            print(f"cannot add directory {dir_to_add} since file {f} is not found")
            flag=1
    if flag:
        return
    #add to joblist
    for job_list in lists_to_work_for:
        if os.path.isfile(job_list):
            with open(job_list,"r+") as fil:
                dirs=fil.readlines()
        else:
            dirs=[]
        if dir_to_add not in dirs:
            dirs.append(dir_to_add+"\n")
        with open(job_list,"w") as fil:
            fil.writelines(dirs)
        print(f"Added {dir_to_add} to {job_list}")
def run_job(d):
    print(f"running jobs in {d}")
    process = subprocess.Popen([os.environ.get('SHELL'), "run.sh"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=d)
    return process, d
def clean_line(line):
    # Replace common invisible characters with a normal space
    # This regex includes zero-width spaces, non-breaking spaces, etc.
    cleaned_line = re.sub(r'[\u200B\u200C\u200D\u2060\uFEFF]', ' ', line)
    # Normalize spaces and strip leading/trailing whitespace
    return re.sub(r'\s+', ' ', cleaned_line.strip())

def run_jobs(jobs):
    jobsublists=[list(jobs)[i:i + 8] for i in range(0, len(jobs), 8)]

    # Wait for all jobs to complete
    for joblist in jobsublists:
        processes = [run_job(d) for d in joblist]
        for process, d in processes:
            print(f'waiting for process {d.strip()}')
            stdout, stderr = process.communicate() 
            print(' ',flush=True)
            if process.returncode != 0:
                print(f'ERRORS OF JOB: {d.strip()}',flush=True)
                with open(os.path.join(script_dir,"errorlist.pkl"),"wb") as fil:
                    pickle.dump(stderr,fil)
                print(stderr.decode())
                raise Exception(stderr.decode())
            else:
                print(stdout.decode())
                update_timestamp(d)

def update_ref(directory,output,ref_file):
    if os.path.isfile(output):
        shutil.copy(output,ref_file)
        print(f"deleting {output}")
        os.remove(output)
def update_timestamp(directory):
    t_string =datetime.now().strftime(timing_format)
    with open(os.path.join(directory,timing_file),"w") as fil:
        fil.write(t_string)

def update_jobs(jobs):
    for d in jobs:
        outputs=[os.path.join(d,f) for f in read_lines_from_file(os.path.join(d,files_to_check[0]))]
        update_timestamp_flag=True
        print(f"updating jobs in {d}")
        copy_all_results=False
        for output in outputs:
            ref_file=output+ref_suffix
            if copy_all_results:
                update_ref(d,output,ref_file) 
                continue
            if not os.path.isfile(ref_file):
               update_ref(d,output,ref_file) 
               continue
                    
            if not os.path.isfile(output):
                #missing output is ok only if ref-file is more recent than last run
                with open(os.path.join(d,timing_file),"r") as fil:
                    string=fil.read()
                    run_time= datetime.strptime(string, timing_format)
                ref_time=datetime.fromtimestamp(os.path.getmtime(ref_file))
                if ref_time>=run_time:
                    continue
                else:
                    flag=input(f"result file {output} is missing, acceptable?y/n")
                    if flag=="y":
                        continue
                    else:
                        return
            # check for differences
            with open(output,"r") as fil:
                outputlines=fil.readlines()
            with open(ref_file,"r") as fil:
                reflines=fil.readlines()
            diffs=[i for i in difflib.context_diff(reflines,outputlines, tofile=output,fromfile=ref_file)]
            if len(diffs)!=0:
                print("".join(diffs))
                flag=""
                while flag not in {"y","n","a"}:
                    flag=input("differences acceptable(y/n/a(ll accepted))?")
                if flag=="y":
                    update_ref(d,output,ref_file) 
                if flag=='a':
                    update_ref(d,output,ref_file) 
                    copy_all_results=True
            else:
                update_ref(d,output,ref_file)
def check_lists(lists_to_work_for):
    for job_list in lists_to_work_for:
        if not os.path.isfile(os.path.join(list_dir,job_list)):
            print(f"list {job_list} not found in {list_dir}")
            sys.exit()
def main():
    args=parse_args()
    lists_to_work_for=args.list if args.list else [ f.path for f in os.scandir(list_dir) if f.is_file] 
    lists_to_work_for=[os.path.join(list_dir,f) for f in lists_to_work_for]
    #
    # add new job
    #
    if "a" in args.actions:
        print("adding new job")
        add_job(lists_to_work_for)
    if "s" in args.actions:
        print_jobs(lists_to_work_for)
    if "r" in args.actions or "u" in args.actions:
        check_lists(lists_to_work_for)
        jobs={dir for joblist in lists_to_work_for for dir in read_lines_from_file(joblist)}
        #
        #run jobs
        #
        if "r" in args.actions:
            print(f"running jobs {jobs}")
            run_jobs(jobs)
            update_jobs(jobs)
        #
        #update jobs
        #
        if "u" in args.actions:
            print(f"updating jobs {jobs}")
            update_jobs(jobs)

if __name__=="__main__":
    main()



