import json
import signal
import sys
import time
import datetime
import elasticsearch
from concurrent.futures import ThreadPoolExecutor

def normilize_grpc_evet_by_guid(elastic_search_client : elasticsearch.Elasticsearch, uuid) -> None:
    query = {
        "query": {
            "bool": {
                "must": [
                    {
                        "match": {
                            "event.GUID.keyword": uuid
                        }
                    },
                    {
                        "terms": {
                            "event.type.keyword": [
                                "grpc-server-call-send",
                                "grpc-server-call-receive",
                                "grpc-client-call-send",
                                "grpc-client-call-receive"
                            ]

                        }
                    }
                ]
            }
        }
    }
    resp = elastic_search_client.search(query=query['query'])
    events = {
        "grpc-server-call-send" : None,
        "grpc-server-call-receive": None,
        "grpc-client-call-send": None,
        "grpc-client-call-receive": None
    }
    ids = []
    time_receive = None
    for ev in resp['hits']['hits']:
        ids.append(ev['_id'])
        cur_time_recv = datetime.datetime.fromisoformat(ev['_source']['timestamp'])
        if time_receive == None or time_receive > cur_time_recv:
            time_receive = cur_time_recv
        events[ev['_source']['event']['type']] = ev['_source']['event']

    res = {
        "GUID": uuid
    }

    if not (events['grpc-server-call-send'] is None or events['grpc-server-call-receive'] is None):
        res['method']   = events['grpc-client-call-receive']['method']
        res['argument'] = events['grpc-client-call-receive']['argument']
        res["client_info"] = {
            "hostname":      events['grpc-client-call-receive']["hostname"],
            "script":        events['grpc-client-call-receive']["script"],
            "function_path": events['grpc-client-call-receive']["function_path"],
            "status":        events['grpc-client-call-receive']["status"],
            "details":       events['grpc-client-call-receive']["details"]
        }
        t0 = datetime.datetime.fromisoformat(events['grpc-client-call-send']['time'])
        t3 = datetime.datetime.fromisoformat(events['grpc-client-call-receive']['time'])
        res["client_side_time"] = (t3 - t0).total_seconds()

    if not (events['grpc-server-call-send'] is None or events['grpc-server-call-receive'] is None):
        res['method']   = events['grpc-server-call-send']['method']
        res['argument'] = events['grpc-server-call-send']['argument']
        res["server_info"] = {
            "hostname":      events['grpc-server-call-send']["hostname"],
            "script":        events['grpc-server-call-send']["script"],
            "function_path": events['grpc-server-call-send']["function_path"],
            "status":        events['grpc-server-call-send']["status"],
            "details":       events['grpc-server-call-send']["details"]
        }
        t1 = datetime.datetime.fromisoformat(events['grpc-server-call-receive']['time'])
        t2 = datetime.datetime.fromisoformat(events['grpc-server-call-send']['time'])
        res["server_side_time"] = (t2 - t1).total_seconds()

    if "server_side_time" in res.keys() and "client_side_time" in res.keys():
        res["network_time"] = res["client_side_time"] - res["server_side_time"]
        res["status"] = res["client_info"]["status"] if res["client_info"]["status"] == res["server_info"]["status"] else "UNKNOWN"
    else:
        res["status"] = "FAILED"

    resp = elastic_search_client.index(index="grpc-events", document=res)
    for doc_id in ids:
        resp = elastic_search_client.delete(index="events", id=doc_id)


def grpc_events(elastic_search_client):
    query_for_guids = {
        "query": {
            "range": {
                "timestamp": {
                    "lte": datetime.datetime.now()
                }
            }
        },
        "aggs":{
            "guid":{
                "terms":{
                    "field" : "event.GUID.keyword",
                    "size": 2147483647
                }
            }
        },
        "size": 0,
        "_source": False

    }
    resp = elastic_search_client.search(query=query_for_guids['query'],
                                        aggregations= query_for_guids['aggs'],
                                        size=query_for_guids['size'],
                                        source=query_for_guids['_source'])
    if resp.meta.status//100 != 2:
        print(f'error {resp.meta.status}')
        return
    # print(resp)
    with ThreadPoolExecutor(max_workers=16) as executor:
        for bucket in resp['aggregations']['guid']['buckets']:
        # normilize_grpc_evet_by_guid(elastic_search_client, bucket['key'])
            executor.submit(normilize_grpc_evet_by_guid, elastic_search_client, bucket['key'])
            # break


def main():
    es = elasticsearch.Elasticsearch(hosts = 'http://0.0.0.0:9200')
    retries = 5
    while not es.ping() and retries > 0:
        retries -= 1
    if not es.ping():
        raise Exception("can't connect to Elasticsearch")

    def final(signal, frame):
        es.close()
        print(f"finished by signal code {signal}")
        sys.exit(0)

    signal.signal(signal.SIGINT, final)
    signal.signal(signal.SIGTERM, final)
    functions = [grpc_events]
    while True:
        for func in functions:
            func(es)
        # grpc_events(es)
        print("go to sleep")
        time.sleep(5*60)


if __name__ == "__main__":
    main()