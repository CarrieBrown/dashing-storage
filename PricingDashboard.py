import pymysql as SQL
import pymysql.cursors
import time
import datetime
import time
import dashing
import sys
import urllib.request
import re
import dashing
import json

### Import SQL Login
f = open(sys.argv[1], 'r')
lines = f.readlines()
SQLItems = {}
for i in lines:
    SQLItems[i.split(" ")[0]] = i.split(" ")[1][:-1]
    print(i.split(" ")[0],i.split(" ")[1][:-1])
f.close()
with open('key.txt', 'r') as file:
    auth_key = file.read().strip()
dash = dashing.DashingImport('viz.unl.edu', auth_token = auth_key)

### Cloud Service Pricing

###AWS -- 4 Core Instance with 8GB Memory for 1 hour
#Storage: per GB Hour // 0.045 per GB/Month
#Network: per GB
###GCP -- Retrieved from Google Cloud Platform
#CPU:  per CPU Hour
#Storage: per GB Hour
#Memory: per GB Hour // 0.040 per GB/Month
#Network: per GB
###Azure -- 4 Core Instance with 8GB Memory for 1 hour
#Storage: per GB Hour // 0.048 per GB/Month
#Network: per GB
###DO -- 4 Core Instance with 8GB Memory for 1 hour
#Storage: per GB Hour // 0.10 per GB/Month
#Network: per GB
###IBM -- 4 Core Instance with 8GB Memory for 1 hour
#Storage: per GB Hour // 0.10 per GB/Month
#Network: per GB
prices = {
"AWS_CPU" : 0.1920/4,
"AWS_MEM" : 0,
"AWS_STOR" : 0.0000616438,
"AWS_NET" : 0.01,
"GCP_CPU" : 0.031611,
"GCP_MEM" : 0.004237,
"GCP_STOR" : 0.00005479452,
"GCP_NET" : 0.08/1024,
"AZ_CPU" : 0.06975,
"AZ_MEM" : 0,
"AZ_STOR" : (1.54/32)/730,
"AZ_NET" : 0.0865722,
"DO_CPU" :  0.04475,
"DO_MEM" : 0,
"DO_STOR" : 0.000136986,
"DO_NET": 0.01,
"IBM_CPU" :  0.05225,
"IBM_MEM" : 0,
"IBM_STOR" : 0.000035616,
"IBM_NET" : 0.09
}

f = urllib.request.urlopen("http://anvil-beta.unl.edu:8123/")
rawData = json.load(f)
ANVIL_MEM = int(rawData["mem_count"])/1024
ANVIL_CPU = int(rawData["core_count"])
ANVIL_STOR = int(rawData["volume_gb"]) + int(rawData["disk_gb"])


SILO_STOR = 2*1024**2
CTR_STOR = 2*1024**2


### Do data magic to get pricing from data values for clusters
def getPricingData(timeDelta, SQLItems):

    ### Handle Authentication with database and dashing
    xdmoddb = SQL.connect(host=SQLItems["xdmodmysql_host"],user=SQLItems["xdmodmysql_username"],password=SQLItems["xdmodmysql_pass"],db=SQLItems["xdmodmysql_db"],cursorclass=pymysql.cursors.DictCursor)
    with open(sys.argv[2], 'r') as file:
        auth_key = file.read().strip()
    #dash = dashing.DashingImport('viz.unl.edu', auth_token = auth_key)   
    with xdmoddb:
        cur = xdmoddb.cursor()
        stmt = "SELECT cpu_time,start_time_ts, end_time_ts, mem_req   FROM jobfact WHERE start_time_ts > "+timeDelta+";"
        print(stmt)
        cpuHour = 0.0
        memAmt = 0.0
        cur.execute(stmt)
        result = cur.fetchall()
        for i in result:
            # Translate Memory
            timeUsed = (float(i["end_time_ts"])-float(i["start_time_ts"]))/3600.0
            if "M" in i["mem_req"]:
                i["mem_req"] = str(float(i["mem_req"].split("M")[0])/1024.0)
            elif "G" in i["mem_req"]:
                i["mem_req"] = str(float(i["mem_req"].split("G")[0])/1.0)
            
            else:
                i["mem_req"] = "0"
            #cost += (float(i["cpu_time"])/3600) * cpuCost + float(i["mem_req"]) * memCost
            cpuHour += float(i["cpu_time"])/3600
            memAmt += float(i["mem_req"])
        stmt = "SELECT MIN(start_time_ts) FROM jobfact;"
        cur.execute(stmt)
        result = cur.fetchall()
        return(cpuHour, memAmt, result[0]["MIN(start_time_ts)"])
        cur.close()
def pushPrice(service):
    #
    tempDay = (float(dayCPU)) * prices[service+"_CPU"] + float(dayMem) * prices[service+"_MEM"] + REDMONTHCOMP/30 * prices[service+"_CPU"] + REDMONTHSTOR/30 * prices[service+"_STOR"] + REDMONTHMEM/30 * prices[service+"_MEM"] + NETMONTH/30 * prices[service+"_NET"] + ((ANVIL_MEM * prices[service+"_MEM"] + ANVIL_CPU * prices[service+"_CPU"] + prices[service+"_STOR"] * ANVIL_STOR)* 24)
    
    tempMonth = (float(dayCPU)) * prices[service+"_CPU"] + float(dayMem) * prices[service+"_MEM"] + REDMONTHCOMP * prices[service+"_CPU"] + REDMONTHSTOR * prices[service+"_STOR"] + REDMONTHMEM * prices[service+"_MEM"] + NETMONTH * prices[service+"_NET"] + ((ANVIL_MEM * prices[service+"_MEM"] + ANVIL_CPU * prices[service+"_CPU"] + prices[service+"_STOR"] * ANVIL_STOR)* 24*30)
    
    tempYear = (float(dayCPU)) * prices[service+"_CPU"] + float(dayMem) * prices[service+"_MEM"] + REDMONTHCOMP*12 * prices[service+"_CPU"] + REDMONTHSTOR*12 * prices[service+"_STOR"] + REDMONTHMEM*12 * prices[service+"_MEM"] + NETMONTH*12* prices[service+"_NET"] + ((ANVIL_MEM * prices[service+"_MEM"] + ANVIL_CPU * prices[service+"_CPU"] + prices[service+"_STOR"] * ANVIL_STOR)* 24*365)
    
    
    print(service+" day cost: $" + str(tempDay))
    print(service+" week cost: $" + str(tempMonth))
    print(service+" year cost: $" + str(tempYear))
    dash.SendEvent(service.lower()+'Day', {'current': tempDay})
    time.sleep(1)
    dash.SendEvent(service.lower()+'Month', {'current': tempMonth})
    time.sleep(1)
    dash.SendEvent(service.lower()+'Year', {'current': tempYear})

# SYNCOFFSET is to account for database delay regarding data pushed at midnight and is used for testing with snapshots 
REDMONTHSTOR = (7.2*1024*1024) + CTR_STOR + SILO_STOR    
REDMONTHCOMP = 6309390
REDMONTHMEM = 29900800
NETMONTH = (730*60*60)*(0.063)/8 + (730*60*60)*(6.5)/8
SYNCOFFSET =86400 
DAY = 86400     
WEEK = DAY * 7      
MONTH = DAY * 30
YEAR = DAY * 365
ALL = DAY * 99999999
currentTime = int(time.time())      
dayCPU, dayMem, startTS = getPricingData(str(currentTime - (DAY+SYNCOFFSET)),SQLItems)
weekCPU, weekMem, startTS = getPricingData(str(currentTime - (WEEK+SYNCOFFSET)),SQLItems)
monthCPU, monthMem,startTS = getPricingData(str(currentTime - (MONTH+SYNCOFFSET)),SQLItems)
yearCPU, yearMem, startTS = getPricingData(str(currentTime - (YEAR+SYNCOFFSET)),SQLItems)
services = ["AWS","GCP","IBM","DO","AZ"]

for serv in services:
    pushPrice(serv)













