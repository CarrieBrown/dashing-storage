import rrdtool as rt
import sys
from time import sleep, gmtime, strftime
from subprocess import call
from sortedcontainers import SortedDict
import dashing
TOKEN = open("key.txt",'r').readline()[:-1]
dash = dashing.DashingImport('viz.unl.edu', auth_token = TOKEN)
def rrdToArrayPoint(rrdFile):
        result = rt.fetch(rrdFile, "AVERAGE")
        start, end, step = result[0]
        legend = result[1]
        rows = result[2]
        endTime = end - 00
        points = []
        counter = 0
        try:
            for i in range(20,0,-1):
                #print(rrdFile,i,rows[len(rows)-(3+i)][1])
                points.append({"y":int(rows[len(rows)-(3+i)][0] + rows[len(rows)-(3+i)][1])*8,"x":endTime})
                last_point = (rows[len(rows)-(3+i)][0] + rows[len(rows)-(3+i)][1])
                endTime = endTime - 300
                counter += 1
            return points, last_point
        except:
            return [{"y":50,"x":1},{"y":50,"x":2},{"y":50,"x":3},{"y":50,"x":4}], 50

while True:
    call(("rm shor_wan.rrd").split(" "))
    call(("rm pki_wan.rrd").split(" "))
    call(("wget -q http://hcc-mon.unl.edu/shor_wan.rrd -O shor_wan.rrd").split(" "))
    call(("wget -q http://hcc-mon.unl.edu/pki_wan.rrd -O pki_wan.rrd").split(" "))
    try: #try catch here due to RRD weirdness       
        points,last_point = rrdToArrayPoint("shor_wan.rrd")
        dash.SendEvent('ShorNetworkGraph', {'points':points})
        dash.SendEvent('HCCAmazonPrice', { 'network_bandwidth': last_point })
    except Exception as e:
        print("Something occurred with Shor")
        print(str(e))
        
    try:#try catch here due to RRD weirdness
            points,last_point2 = rrdToArrayPoint("pki_wan.rrd")     
            dash.SendEvent('HCCAmazonPrice', { 'network_bandwidth': last_point+last_point2 })
            dash.SendEvent('PkiNetworkGraph', {'points':points})


    except Exception as e:
        print("Something occurred with PKI")
        print(str(e))
    sleep(int(sys.argv[1]))
