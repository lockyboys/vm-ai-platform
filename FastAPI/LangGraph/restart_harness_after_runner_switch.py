import subprocess
subprocess.run(['sudo','systemctl','restart','sps-harness.service'],check=True)
print(subprocess.run(['systemctl','is-active','sps-harness.service'],capture_output=True,text=True,check=True).stdout.strip())
