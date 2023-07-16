import kopf
import logging
import json
import time
from kubernetes import client, config

@kopf.on.create('replicasetscalers')
def create_cronjob(spec, name, namespace, **kwargs):
    cron_schedules=spec['schedules']
    for schedule in cron_schedules:
        replicaset_name = schedule['replicasetname']
        replicaset_namespace = schedule['namespace']

        scale_up_config=schedule['scaleup']
        scale_down_config=schedule['scaledown']

        scale_up_cronjob_name=name+"-"+replicaset_name+"-"+scale_up_config['label']
        scale_down_cronjob_name=name+"-"+replicaset_name+"-"+scale_down_config['label']
        
        create_namespaced_cron_job(scale_up_cronjob_name,namespace,scale_up_config, replicaset_name, replicaset_namespace)
        create_namespaced_cron_job(scale_down_cronjob_name,namespace,scale_down_config, replicaset_name, replicaset_namespace)


@kopf.on.event('', 'v1', 'pods', labels={"app": "rs-scale-up"})
def scale_up_replicaset(spec, name, namespace, **kwargs):
    logging.info("scale-up initiated")
    patch_replicaset(spec)

@kopf.on.event('', 'v1', 'pods', labels={"app": "rs-scale-down"})
def scale_down_replicaset(spec, name, namespace, **kwargs):
    logging.info("scale-down initiated")
    patch_replicaset(spec)

def patch_replicaset(spec):
    env_list = spec['containers'][0]['env']

    replicaset_name = get_env('REPLICASET_NAME',env_list)
    replicaset_namespace = get_env('REPLICASET_NAMESPACE',env_list)
    replicaset_scale_count = get_env('REPLICAS',env_list)
    
    patch = {
        "spec": {
            "replicas": int(replicaset_scale_count)
        }
    }

    v1 = client.AppsV1Api()
    api_response = v1.patch_namespaced_replica_set_scale(name=replicaset_name, namespace=replicaset_namespace, body=patch)
    print(api_response)

def create_namespaced_cron_job(name, namespace, scale_config, replicaset_name, replicaset_namespace):
    scale_schedule = scale_config['schedule']
    cron_job_label = scale_config['label']
    env_arr = get_env_arr(scale_config)
    env_arr.append({ 'name' : 'REPLICASET_NAME', 'value': replicaset_name })
    env_arr.append({ 'name' : 'REPLICASET_NAMESPACE', 'value': replicaset_namespace })
    cronjob_json = get_cronjob_body(namespace, name, scale_schedule, cron_job_label, env_arr)
    name = cronjob_json['metadata']['name']
    if judge_crontab_exists(namespace, name):
        print(f'{name} exists, skipping!')
    else:
        v1 = client.BatchV1Api()
        ret = v1.create_namespaced_cron_job(namespace=namespace, body=cronjob_json, pretty=True,
                                            _preload_content=False, async_req=False)
        ret_dict = json.loads(ret.data)
        print(f'create succeed\n{json.dumps(ret_dict)}')

def get_cronjob_list(namespace='default'):
    v1 = client.BatchV1Api()
    ret = v1.list_namespaced_cron_job(namespace=namespace, pretty=True, _preload_content=False)
    cron_job_list = json.loads(ret.data)
    print(f'cronjob number={len(cron_job_list["items"])}')
    return cron_job_list["items"]

def judge_crontab_exists(namespace, name):
    cron_job_list = get_cronjob_list(namespace)
    for cron_job in cron_job_list:
        if name == cron_job['metadata']['name']:
            return True
    return False

def get_cronjob_body(namespace, name, schedule, cron_job_label, env_arr):
    body = {
        "apiVersion": "batch/v1",
        "kind": "CronJob",
        "metadata": {
            "name": name,
            "namespace": namespace,
        },
        "spec": {
            "schedule": schedule,
            "concurrencyPolicy": "Forbid",
            "suspend": False,
            "jobTemplate": {
                "spec": {
                    "template": {
                        "metadata": {
                            "labels": {
                                "app": cron_job_label
                                }
                        },
                        "spec": {
                            "containers": [
                                {
                                    "name": name,
                                    "image": "busybox:1.35",
                                    "env": env_arr,
                                    "command": [ 
                                        "/bin/sh",
                                        "-c",
                                        "date; echo triggering scale event"
                                    ]
                                }
                            ],
                            "restartPolicy": "Never"
                        }
                    }
                }
            },
            "successfulJobsHistoryLimit": 1,
            "failedJobsHistoryLimit": 1
        }
    }
    return body

def get_env_arr(env_list):
    env_arr=[]
    keys = list(env_list.keys())
    for key in keys:
        env_arr.append({ 'name' : key.upper(), 'value': str(env_list[key]) })
    return env_arr

def get_env(key, list):
    for item in list:
        if item['name'] == key:
            return item['value']