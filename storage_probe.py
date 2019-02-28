#!/usr/bin/python

import subprocess
import dashing
import os
import time
import sys
import socket
import urllib2
import json
import re
import pymysql as SQL
import pymysql.cursors
import operator

MOUNT = "/lustre"
CLUSTER = socket.gethostname().split(".")[1].capitalize()
from math import log
terabyte = 1073741824

unit_list = zip(['bytes', 'kB', 'MB', 'GB', 'TB', 'PB'], [0, 0, 1, 1, 1, 1])
def sizeof_fmt(num):
    """Human friendly file size"""
    if num > 1:
        exponent = min(int(log(num, 1024)), len(unit_list) - 1)
        quotient = float(num) / 1024**exponent
        unit, num_decimals = unit_list[exponent + 1]
        format_string = '%%.%sf%s' % (num_decimals, unit)
        format_string = format_string % (quotient)
        return format_string
    if num == 0:
        return '0 bytes'
    if num == 1:
        return '1 byte'

def main():
    with open('key.txt', 'r') as file:
        auth_key = file.read().strip()

    p = subprocess.Popen(["df", "-P", MOUNT], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (stdoutdata, stderrdata) = p.communicate()
    for line in stdoutdata.split("\n"):
        split_line = line.split()
        if len(split_line) < 5:
            continue
        if split_line[5] == MOUNT:
            dash = dashing.DashingImport('viz.unl.edu', auth_token = auth_key)
            dashUNO = dashing.DashingImport('viz.unl.edu',port=4000, auth_token = auth_key)
            send_dict = { 'min': 0, 'max': float("%.1f" % (float(split_line[1]) / terabyte)) , 'value': float("%.1f" % (float(split_line[2]) / terabyte)), 'moreinfo': "Capacity: %s" % sizeof_fmt(int(split_line[1])) }
            dash.SendEvent(CLUSTER+'Storage', send_dict)
            dash.SendEvent('HCCAmazonPrice', {CLUSTER.lower()+'Storage': send_dict['value']})
            
            dashUNO.SendEvent(CLUSTER+'Storage', send_dict)
            dashUNO.SendEvent('HCCAmazonPrice', {CLUSTER.lower()+'Storage': send_dict['value']})


    # Send the number of jobs running
    command = "squeue -t R -O numcpus,account -h".split(" ")
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (stdout, stderr) = p.communicate()
    sum_running_cores = 0
    per_user_cores = {}
    for line in stdout.split("\n"):
        if line == "":
            break
        try:
            (cores, username) = line.split()
            sum_running_cores += int(cores)
            username.strip()
            if username not in per_user_cores:
                per_user_cores[username] = 0
            per_user_cores[username] += int(cores)
        except:
            print "Error parsing line: %s" % line
            pass
        
    if os.path.isfile('dashing.txt') and os.access('dashing.txt', os.R_OK):
        date = os.path.getmtime('dashing.txt')
        with open('dashing.txt', 'r') as file:
            last_running_cores = int(file.read())
    else:
        print "Error reading from dashing.txt"
        date = time.time() + 3600
        last_running_cores = sum_running_cores
    with open('dashing.txt', 'w') as file:
        file.write(str(sum_running_cores))
    date = time.strftime('%m-%d-%Y %H:%M:%S', time.localtime(date))
    dash.SendEvent(CLUSTER+'Running', {'current': sum_running_cores, 'last': last_running_cores, 'last_period': date})
    dash.SendEvent('HCCAmazonPrice', {CLUSTER+'Cores': sum_running_cores})
    
    dashUNO.SendEvent(CLUSTER+'Running', {'current': sum_running_cores, 'last': last_running_cores, 'last_period': date})
    dashUNO.SendEvent('HCCAmazonPrice', {CLUSTER+'Cores': sum_running_cores})
    
    # send number of completed jobs
    current_time = time.strftime('%m/%d/%y-%H:%M:%S', time.localtime(time.time()))
    start_time = time.strftime('%m/%d/%y', time.localtime(time.time()))
    command = "sacct -a -E " + current_time + " -S " + start_time + " -s CD -o JobID -X"
    command = command.split(" ")
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (stdout, stderr) = p.communicate()
    jobs_completed = len(stdout.split())
    path = '/common/swanson/.dashing/'
    files = ['crane_jobs.txt', 'tusker_jobs.txt', 'sandhills_jobs.txt']
    filename = path + files[0]
    with open(filename, 'w') as file:
        file.write(str(jobs_completed))
    total_jobs = 0
    for filename in files:
        filename = path + filename
        if os.path.isfile(filename) and os.access(filename, os.R_OK):
            with open(filename, 'r') as file:
                total_jobs += int(file.read())
        else:
            print "Error reading from %s" % filename
    
    dash.SendEvent('JobsCompleted', {'current': total_jobs})
    
    dashUNO.SendEvent('JobsCompleted', {'current': total_jobs})


    #Send number of CPU Hours for Today
    command = "sacct -a -o CPUTimeRaw -n -T"
    command = command.split(" ")
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (stdout, stderr) = p.communicate()
    stdout = map(int, stdout.split())
    hours_completed = sum(stdout)/3600
    files = ['crane_hours.txt', 'tusker_hours.txt', 'sandhills_hours.txt']
    filename = path + files[0]
    with open(path + CLUSTER.lower()+'_hours.txt', 'w') as file:
        file.write(str(hours_completed))
    total_hours = 0
    for filename in files:
        filename = path + filename
        if os.path.isfile(filename) and os.access(filename, os.R_OK):
            with open(filename, 'r') as file:
                total_hours += int(file.read())
        else:
            print "Error reading from %s" % filename


    dash.SendEvent('HoursToday', {'current': total_hours})
    
    dashUNO.SendEvent('HoursToday', {'current': total_hours})
    
    # Send Anvil Information
    ## Time Delay is to allow dashing to keep up with POST
    
    f = urllib2.urlopen("http://anvil-beta.unl.edu:8123/")
    rawData = json.load(f)
    dashUNO.SendEvent('AnvilTile', {'current_vm': rawData["vm_count"]})
    time.sleep(1)
    dashUNO.SendEvent('AnvilTile', {'current_cores': rawData["core_count"]})
    time.sleep(1)
    dashUNO.SendEvent('AnvilTile', {'current_mem': str(round(int(rawData["mem_count"])/(1024.0**2),2))})
    time.sleep(1)
    dashUNO.SendEvent('AnvilTile', {'current_vol': str(round(int(rawData["volume_gb"])/1024.0,2))})
    time.sleep(1)
    dashUNO.SendEvent('AnvilTile', {'current_disk': str(round(int(rawData["disk_gb"])/1024.0,2))})

    # Red Storage
    redT2 = urllib2.urlopen("http://t2.unl.edu:8088/dfshealth.jsp")
    redData = re.findall("\d+\.\d+",str(redT2.read()))
    dash.SendEvent('RedStorage', {'min': 0, 'max': float(redData[9])*1024, 'value': float(redData[10])*1024, 'Capacity': redData[9] + " PB"})  
    dashUNO.SendEvent('RedStorage', {'min': 0, 'max': float(redData[9])*1024, 'value': float(redData[10])*1024, 'Capacity': redData[9] + " PB"}) 
    dash.SendEvent('HCCAmazonPrice', {'redStorage':float(redData[10])*1024})  
    dashUNO.SendEvent('HCCAmazonPrice', {'redStorage':float(redData[10])*1024})
    
    
    
    # Top Users UNL
    dbFile = open('db.yml', 'r')
    lines = dbFile.readlines()
    SQLItems = {}
    for i in lines:
        SQLItems[i.split(" ")[0]] = i.split(" ")[1][:-1]
        
    f.close()
    
    rcfdb = SQL.connect(host=SQLItems["rcfmysql_host"],user=SQLItems["rcfmysql_username"],passwd=SQLItems["rcfmysql_pass"],db=SQLItems["rcfmysql_db"],cursorclass=pymysql.cursors.DictCursor)
    
    ## Grab this clusters squeue
    
    command = "squeue -h -t R -o '%u %C'"
    p = subprocess.Popen(command,shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (stdout, stderr) = p.communicate()
    file = open(path + CLUSTER.lower()+'_users.txt', 'w')
    file.write(stdout)
    file.close()
    
    
    
    ## Pull top Users
    files = ['crane_users.txt', 'tusker_users.txt']
    topUsers = {}
    for file in files:
        filename = path + file
        if os.path.isfile(filename) and os.access(filename, os.R_OK):
            userFile = open(filename,'r').readlines()
            for line in userFile:
                if line.split(',')[0] in topUsers:
                    topUsers[line.split(' ')[0]] += int(line.split(' ')[1])
                else:
                    topUsers[line.split(' ')[0]] = int(line.split(' ')[1])
    topUsers25 = sorted(topUsers.items(), key=operator.itemgetter(1), reverse=True)[:25]
    
    ## The real magic of sql begins
    dataToDash = []
    cur = rcfdb.cursor()
    for k,v in topUsers25:
        stmt = "select Department, Campus from Personal where LoginID = \"" + k + "\";"
        cur.execute(stmt)
        result = cur.fetchall()[0]
        dataToDash.append({"label":k[:9],"value":v,"dept":result["Department"][:14],"campus":result["Campus"]})
    dash.SendEvent('BiggestUsers', {'items': dataToDash})
    cur.close()
    
    
    




if __name__ == "__main__":
    main()

