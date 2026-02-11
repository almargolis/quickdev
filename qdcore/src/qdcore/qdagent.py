import subprocess

process = subprocess.Popen(
    ['long-running-command'],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1  # Line buffered
)

# Stream output line by line
for line in process.stdout:
    # Agent can react to each line as it comes
    print(line, end='')
    
process.wait()