import d4j_srepair
import subprocess
import multiprocessing as mp

def run(project_queue,core):
    while not project_queue.empty():
        project=project_queue.get()
        print(f'Run {project}')
        result=subprocess.run(['python3','alpharepair.py',project,str(core)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        with open(f'result/{project}-alpharepair.log','w') as f:
            f.write(result.stdout.decode("utf-8"))
        print(f'Finish {project} with returncode {result.returncode}')

queue=mp.Manager().Queue()

for i in range(1,d4j_srepair.CLI_SIZE+1):
    if i in d4j_srepair.CLI_SKIP: continue
    queue.put(f'Cli_{i}')
for i in range(1,d4j_srepair.CODEC_SIZE+1):
    queue.put(f'Codec_{i}')
for i in range(1,d4j_srepair.COLLECTIONS_SIZE+1):
    if i in d4j_srepair.COLLECTIONS_SKIP: continue
    queue.put(f'Collections_{i}')
for i in range(1,d4j_srepair.COMPRESS_SIZE+1):
    queue.put(f'Compress_{i}')
for i in range(1,d4j_srepair.CSV_SIZE+1):
    queue.put(f'Csv_{i}')
for i in range(1,d4j_srepair.GSON_SIZE+1):
    queue.put(f'Gson_{i}')
for i in range(1,d4j_srepair.JACKSON_CORE_SIZE+1):
    queue.put(f'JacksonCore_{i}')
for i in range(1,d4j_srepair.JACKSON_DATABIND_SIZE+1):
    if i in d4j_srepair.JACKSON_DATABIND_SKIP: continue
    queue.put(f'JacksonDatabind_{i}')
for i in range(1,d4j_srepair.JACKSON_XML_SIZE+1):
    queue.put(f'JacksonXml_{i}')
for i in range(1,d4j_srepair.JSOUP_SIZE+1):
    queue.put(f'Jsoup_{i}')
for i in range(1,d4j_srepair.JXPATH_SIZE+1):
    queue.put(f'JxPath_{i}')
for i in d4j_srepair.CLOSURE_NEW:
    queue.put(f'Closure_{i}')


from sys import argv

if len(argv)!=2:
    print(f'Usage: {argv[0]} <num of GPU cores>')
    exit(1)

procs=[]
for i in range(int(argv[1])):
    proc=mp.Process(target=run,args=(queue,i))
    procs.append(proc)
for proc in procs:
    proc.start()
for proc in procs:
    proc.join()