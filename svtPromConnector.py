# -*- coding: utf-8 -*-
"""
Created on December 16, 2019
Version 2.3

Copyright (c) 2019 Hewlett Packard Enterprise

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.
    https://www.gnu.org/licenses/gpl-3.0.en.html

"""

from cryptography.fernet import *
from lxml import etree
import time
from SimpliVityClass import *
from datetime import datetime
from prometheus_client import Counter, Gauge, start_http_server

BtoGB = pow(1024, 3)
BtoMB = pow(1024, 2)
path = '/opt/svt/'


node_state = {
    'UNKOWN': 0,
    'ALIVE': 1,
    'SUSPECTED': 2,
    'MANAGED': 3,
    'FAULTY': 4,
    'REMOVED': 5
}

raid_card_state = {
    'RED' : 0,
    'GREEN' : 1,
    'YELLOW' : 2
}

battery_state = {
    'DEGRADED' : 0,
    'HEALTHY' : 1
}

accelerator_card_state = {
    'RED' : 0,
    'GREEN' : 1,
    'YELLOW' : 2
}

vm_state = {
    'ALIVE': 1,
    'DELETED': 2,
    'REMOVED': 3
}

capacitymetric = [
    'allocated_capacity',
    'free_space',
    'capacity_savings',
    'used_capacity',
    'used_logical_capacity',
    'local_backup_capacity',
    'remote_backup_capacity',
    'stored_compressed_data',
    'stored_uncompressed_data',
    'stored_virtual_machine_data'
]

dedupmetric = [
    'compression_ratio',
    'deduplication_ratio',
    'efficiency_ratio'
]

performancemetric = [
    'read_iops',
    'write_iops',
    'read_throughput',
    'write_throughput',
    'read_latency',
    'write_latency'
]

hardwaremetric = [
    'raid_card_status',
    'battery_health',
    'accelerator_card_status',
    'ssd_life_remaining'
]

vmcapacitymetric = [
    'hypervisor_consumed_space',
    'hypervisor_consumed_memory',
    'hypervisor_memory_usage'
]

def logwriter(f, text):
        output = str(datetime.today()) + ": "+text+" \n"
        print(output)
        f.write(output)


def logopen(filename):
        f = open(filename, 'a')
        f.write(str(datetime.today())+": Logfile opened \n")
        return f


def logclose(f):
        f.write(str(datetime.today())+": Logfile closed \n")
        f.close()


def getPerformanceAverage(data):
        perf = {
            'read_iops': 0,
            'write_iops': 0,
            'read_throughput': 0,
            'write_throughput': 0,
            'read_latency': 0,
            'write_latency': 0
        }
        for x in data:
            if x['name'] == 'iops':
                i = 0
                for y in x['data_points']:
                    perf['read_iops'] += y['reads']
                    perf['write_iops'] += y['writes']
                    i += 1
                if i > 0:
                    perf['read_iops'] /= i
                    perf['write_iops'] /= i
                else:
                    perf['read_iops'] = -1
                    perf['write_iops'] = -1
            if x['name'] == 'throughput':
                i = 0
                for y in x['data_points']:
                    perf['read_throughput'] += y['reads']
                    perf['write_throughput'] += y['writes']
                    i += 1
                if i > 0:
                    perf['read_throughput'] /= (i * BtoMB)
                    perf['write_throughput'] /= (i * BtoMB)
                else:
                    perf['read_throughput'] = -1
                    perf['write_throghput'] = -1
            if x['name'] == 'latency':
                i = 0
                for y in x['data_points']:
                    perf['read_latency'] += y['reads']
                    perf['write_latency'] += y['writes']
                    i += 1
                if i > 0:
                    perf['read_latency'] /= (i * 1000)
                    perf['write_latency'] /= (i * 1000)
                else:
                    perf['read_latency'] = -1
                    perf['write_latency'] = -1
        return(perf)


def getNodeCapacity(data):
        ndata = {
            'allocated_capacity': 0,
            'free_space': 0,
            'capacity_savings': 0,
            'used_capacity': 0,
            'used_logical_capacity': 0,
            'local_backup_capacity': 0,
            'remote_backup_capacity': 0,
            'stored_compressed_data': 0,
            'stored_uncompressed_data': 0,
            'stored_virtual_machine_data': 0,
            'compression_ratio': 0,
            'deduplication_ratio': 0,
            'efficiency_ratio': 0
        }
        for y in data:
            if 'ratio' in y['name']:
                ndata[y['name']] = y['data_points'][-1]['value']
            else:
                ndata[y['name']] = y['data_points'][-1]['value']/BtoGB
        return ndata

def getNodeHardware(data):
        raid_card = data['raid_card']
        battery = data['battery']
        accelerator_card = data['accelerator_card']
        logical_drives = data['logical_drives']
        ndata = {
            'raid_card_status' : 'RED',
            'battery_health' : 'DEGRADED',
            'accelerator_card_status' : 'RED',
            'ssd_life_remaining' : 0
        }
        ndata['raid_card_status'] = raid_card_state[raid_card['status']]
        ndata['battery_health'] = battery_state[battery['health']]
        ndata['accelerator_card_status'] = accelerator_card_state[accelerator_card['status']]
        for i in range(len(logical_drives)):
            drive_count = len(logical_drives[i]['drive_sets'][0]['physical_drives'])
            for j in range(drive_count):
                ndata['ssd_life_remaining'] += logical_drives[i]['drive_sets'][0]['physical_drives'][j]['life_remaining']
            ndata['ssd_life_remaining'] /= drive_count
        ndata['ssd_life_remaining'] /= len(logical_drives)
        return ndata

def getVmCapacity(data):
        ndata = {
            'hypervisor_consumed_space': 0,
            'hypervisor_consumed_memory': 0,
            'hypervisor_memory_usage' : 0
        }
        ndata['hypervisor_consumed_space'] = ((data['virtual_machine']['hypervisor_allocated_capacity'] - data['virtual_machine']['hypervisor_free_space'])/data['virtual_machine']['hypervisor_allocated_capacity'])*100
        ndata['hypervisor_consumed_memory'] = (data['virtual_machine']['hypervisor_consumed_memory']/data['virtual_machine']['hypervisor_total_memory'])*100
        ndata['hypervisor_memory_usage'] = data['virtual_machine']['hypervisor_consumed_memory']
        return ndata

# Main ###########################################################################
if __name__ == "__main__":
    t0 = time.time()
    """ read the key and input file """
    keyfile = path + 'SvtConnector.key'
    xmlfile = path + 'SvtConnector.xml'

    """ Parse XML File """
    tree = etree.parse(xmlfile)
    u2 = (tree.find("user")).text
    p2 = (tree.find("password")).text
    ovc = (tree.find("ovc")).text
    mintervall = int((tree.find("monitoringintervall")).text)
    mresolution = (tree.find("resolution")).text
    mrange = (tree.find("timerange")).text
    lfile = (tree.find("logfile")).text
    port = int((tree.find("port")).text)

    """ Open the logfile """
    log = logopen(path+lfile)

    """ Read keyfile """
    f = open(keyfile, 'r')
    k2 = f.readline()
    f.close()
    key2 = k2.encode('ASCII')
    f = Fernet(key2)

    """ Create the SimpliVity Rest API Object"""
    logwriter(log, "Open a connection to the SimpliVity systems")
    svtuser = f.decrypt(u2.encode('ASCII')).decode('ASCII')
    svtpassword = f.decrypt(p2.encode('ASCII')).decode('ASCII')
    url = "https://"+ovc+"/api/"
    svt = SimpliVity(url)
    logwriter(log, "Open Connection to SimpliVity")
    svt.Connect(svtuser, svtpassword)
    logwriter(log, "Connection to SimpliVity is open")
    logclose(log)

    start_http_server(port)
    c = Counter('simplivity_sample', 'SimpliVity sample number')
    scluster = Gauge('simplivity_cluster', 'SimpliVity Cluster Data', ['clustername', 'clustermetric'])
    snode = Gauge('simplivity_node', 'SimpliVity Node Data', ['nodename', 'nodemetric'])
    svm = Gauge('simplivity_vm', 'SimpliVity VM Data', ['vmname', 'vmmetric'])
    sdatastore = Gauge('simplivity_datastore', 'SimpliVity Datastore Data - Sizes in GB', ['dsname', 'dsmetric'])
    delta = Gauge('ConnectorRuntime', 'Time required for last data collection in seconds')

    """
    Start an endless loop to capture the current status every TIME_RANGE
    Errors will be catched with an error routine
    Please note that the connection must be refreshed after 24h or afte 10 minutes inactivity.
    """

    # Define a dictionary
    # Outside while scope
    # Add Active VMs here
    # And map them to 
    # their epoch

    vm_epochs = {}

    while True:
        try:
            t0 = time.time()
            c.inc()
            clusters = svt.GetCluster()['omnistack_clusters']
            hosts = svt.GetHost()['hosts']
            vms = svt.GetVM()['virtual_machines']
            datastores = svt.GetDataStore()['datastores']
            scluster.labels('Federation', 'Cluster_count').set(len(clusters))
            snode.labels('Federation', 'Node_count').set(len(hosts))
            svm.labels('Federation', 'VM_count').set(len(vms))
            sdatastore.labels('Federation', 'Datastore_count').set(len(datastores))
            """  Cluster metrics: """
            for x in clusters:
                perf = getPerformanceAverage(svt.GetClusterMetric(x['name'], timerange=mrange,
                                                                  resolution=mresolution)['metrics'])
                cn = (x['name'].split('.')[0]).replace('-', '_')
                for metricname in capacitymetric:
                    scluster.labels(cn, metricname).set(x[metricname]/BtoGB)
                for metricname in dedupmetric:
                    scluster.labels(cn, metricname).set(x[metricname].split()[0])
                for metricname in performancemetric:
                    scluster.labels(cn, metricname).set(perf[metricname])
                for x in svt.GetClusterThroughput():
                    cn = x['source_omnistack_cluster_name']
                    metricname = x['destination_omnistack_cluster_name']+' throughput'
                    scluster.labels(cn, metricname).set(x['throughput'])

            """  Node metrics: """
            for x in hosts:
                y = getNodeCapacity(svt.GetHostCapacity(x['name'], timerange=mrange,
                                                        resolution=mresolution)['metrics'])
                perf = getPerformanceAverage(svt.GetHostMetrics(x['name'], timerange=mrange,
                                             resolution=mresolution)['metrics'])
                hw_metrics = getNodeHardware(svt.GetHostHardware(x['name'])['host'])
                cn = (x['name'].split('.')[0]).replace('-', '_')
                snode.labels(cn, 'State').set(node_state[x['state']])
                for metricname in capacitymetric:
                    snode.labels(cn, metricname).set(y[metricname])
                for metricname in dedupmetric:
                    snode.labels(cn, metricname).set(y[metricname])
                for metricname in performancemetric:
                    snode.labels(cn, metricname).set(perf[metricname])
                for metricname in hardwaremetric:
                    snode.labels(cn, metricname).set(hw_metrics[metricname])

            """  VM metrics: """
            
            # Define an empty list
            # Make a note of all active VMs
            # every monitoring cycle

            # Use this list to ensure
            # that d remains up to date
            
            active_vms = []

            for x in vms:
                if x['state'] == 'ALIVE':
                    active_vms.append(x['name'])
                    if x['name'] not in vm_epochs:
                        vm_epochs[x['name']] = t0
                    y = getVmCapacity(svt.GetVMbyID(x['id']))
                    cn = (x['name'].split('.')[0]).replace('-', '_')
                    svm.labels(cn, 'state').set(vm_state[x['state']])
                    for metricname in vmcapacitymetric:
                        svm.labels(cn, metricname).set(y[metricname])    
                perf=getPerformanceAverage(svt.GetVMMetric(x['name'],timerange=mrange,resolution=mresolution)['metrics'])
                for metricname in performancemetric:
                    svm.labels(cn,metricname).set(perf[metricname]) 

            # Ensure all vms in hash
            # are still active
            # append inactive ones
            # to another list & fire alerts
            # for all VMs in this list

            inactive_vms = []

            for vm in vm_epochs:
                if vm not in active_vms:
                    inactive_vms.append(vm)

            for vm in inactive_vms:
                del vm_epochs[vm]

            for vm in active_vms:
                cn = (vm.split('.')[0]).replace('-', '_')
                svm.labels(cn, 'uptime').set(t0 - vm_epochs[vm])

            # Calculate uptime of an active vm
            # By doing a t0 - vm_epochs[vm]



            """ DataStore metrics """
            for x in datastores:
                cn = (x['name']).replace('-', '_')
                sdatastore.labels(cn, 'size').set(x['size']/BtoGB)

            t1 = time.time()
            delta.set((t1-t0))
            while ((t1-t0) < mintervall):
                time.sleep(1.0)
                t1 = time.time()
        except KeyError:
            log = logopen(path+lfile)
            logwriter(log, "KeyError")
            logwriter(log, str(e.expression))
            logwriter(log, str(e.status))
            logwriter(log, str(e.message))
            logclose(log)
        except SvtError as e:
            if e.status == 401:
                try:
                    log = logopen(path+lfile)
                    logwriter(log, "Open Connection to SimpliVity")
                    svt.Connect(svtuser, svtpassword)
                    logwriter(log, "Connection to SimpliVity is open")
                    logclose(log)
                except SvtError as e:
                    log = logopen(path+lfile)
                    logwriter(log, "Failed to open a conection to SimplVity")
                    logwriter(log, str(e.expression))
                    logwriter(log, str(e.status))
                    logwriter(log, str(e.message))
                    logwriter(log, "close SimpliVity connection")
                    logclose(log)
                    exit(-200)
            elif e.status == 555:
                log = logopen(path+lfile)
                logwriter(log, 'SvtError:')
                logwriter(log, str(e.expression))
                logwriter(log, str(e.status))
                logwriter(log, str(e.message))
                logclose(log)
            else:
                log = logopen(path+lfile)
                logwriter(log, 'Unhandeled SvtError:')
                logwriter(log, str(e.expression))
                logwriter(log, str(e.status))
                logwriter(log, str(e.message))
                logwriter(log, "close SimpliVity connection")
                logclose(log)
                exit(-200)
