#/bin/sh

# SCAR - Serverless Container-aware ARchitectures
# Copyright (C) GRyCAP - I3M - UPV 
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Originally obtained from: http://www.techpaste.com/2012/01/shell-script-collect-system-information/

###########################################################################################################

DATE=`/bin/date +date_%d-%m-%y_time_%H-%M-%S`
Time(){

echo " Computer Time : `date` "

}
GenInfo(){
echo "___________________________________________________________________________________"
echo " General Information "
echo "___________________________________________________________________________________"
echo "Architecture: `uname -m`"
echo "Kernel: `uname -r`"
echo "Linux Distro: `head -n1 /etc/issue`"
echo "Hostname: `hostname`"
echo "Username: `whoami`"
echo "Uptime: `uptime | awk '{ gsub(/,/, ""); print $3 }'` (Hrs:Min)"
echo "RunLevel: `runlevel`"
echo "Running Process :`ps ax | wc -l`"
echo "___________________________________________________________________________________"
}

CPUInfo(){ 
echo "___________________________________________________________________________________"
echo " CPU Information "
echo "___________________________________________________________________________________"
echo "# CPUs: `grep -c 'processor' /proc/cpuinfo`"
echo "CPU model: `awk -F':' '/^model name/ { print $2 }' /proc/cpuinfo`"
echo "CPU vendor: `awk -F':' '/^vendor_id/ { print $2 }' /proc/cpuinfo`"
echo "CPU Speed: `awk -F':' '/^cpu MHz/ { print $2 }' /proc/cpuinfo`"
echo "CPU Cache Size: `awk -F':' '/^cache size/ { print $2 }' /proc/cpuinfo`"
echo "___________________________________________________________________________________"
}

MemInfo(){
echo "___________________________________________________________________________________"
echo " Memory Information"
echo "___________________________________________________________________________________"
echo "`cat /proc/meminfo`"
echo "___________________________________________________________________________________"
echo "`free -m`"
echo "___________________________________________________________________________________"
}

EnvInfo(){
echo "___________________________________________________________________________________"
echo " Environment Information "
echo "___________________________________________________________________________________"
echo "`env`"
echo "___________________________________________________________________________________"
}


FileSInfo(){
echo "___________________________________________________________________________________"
echo " File Systems Information "
echo "___________________________________________________________________________________"
echo "`df -h`"
echo "`ls -lRa /tmp`"
echo "___________________________________________________________________________________"
}



NetInfo(){
echo "___________________________________________________________________________________"
echo " Network Connectivity "
echo "___________________________________________________________________________________"
echo "`networkctl`"
echo "___________________________________________________________________________________"
}


Run(){
#echo "<html><body>"
Time
GenInfo
CPUInfo
MemInfo
FileSInfo
NetInfo
#echo "</body></html>"
}
#log=Sysinfo_$DATE
#Run | tee $log.txt
#mv $log.txt $log.html
Run