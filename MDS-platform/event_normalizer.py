import json
import signal
import sys
import time
import datetime
import elasticsearch
from concurrent.futures import ThreadPoolExecutor
import uuid


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
        "GUID": uuid,
        "timestamp": time_receive.isoformat()
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
            executor.submit(normilize_grpc_evet_by_guid, elastic_search_client, bucket['key'])


def make_dependency_graph(elastic_search_client : elasticsearch.Elasticsearch):
    try:
        elastic_search_client.indices.delete(index='grpc-dependencies')
    except Exception as e:
        print(f'error is {e}')
    query = {
        "size": 0,
        "aggs": {
            "agg": {
                "terms": {
                    "field": "client_info.hostname.keyword",
                    "size": 10
                }
            }
        }
    }
    resp = elastic_search_client.search(index="grpc-events", aggs=query['aggs'], size=query['size'])
    src_hosts =  resp['aggregations']['agg']['buckets']
    query['query'] = {"bool": {"must": []}}
    for out_host in src_hosts:
        client_host_match = {
            "match": {
                "client_info.hostname.keyword": out_host['key']
            }
        }
        query['query']['bool']['must'] = [client_host_match]
        query['aggs']['agg']['terms']['field'] = "client_info.script.keyword"
        resp = elastic_search_client.search(index="grpc-events", query=query['query'], aggs=query['aggs'], size=query['size'])
        src_scripts = resp['aggregations']['agg']['buckets']

        for out_script in src_scripts:
            client_script_match = {
                "match": {
                    "client_info.script.keyword": out_script['key']
                }
            }
            query['query']['bool']['must'] = [client_host_match, client_script_match]
            query['aggs']['agg']['terms']['field'] = "server_info.hostname.keyword"
            resp = elastic_search_client.search(index="grpc-events", query=query['query'], aggs=query['aggs'],
                                                size=query['size'])
            dest_hosts = resp['aggregations']['agg']['buckets']
            for in_host in dest_hosts:
                server_host_match = {
                    "match": {
                        "server_info.hostname.keyword": in_host['key']
                    }
                }
                query['query']['bool']['must'] = [client_host_match, client_script_match, server_host_match]
                query['aggs']['agg']['terms']['field'] = "server_info.script.keyword"
                resp = elastic_search_client.search(index="grpc-events", query=query['query'], aggs=query['aggs'],
                                                    size=query['size'])
                dest_scripts = resp['aggregations']['agg']['buckets']
                for in_script in dest_scripts:
                    server_script_match = {
                        "match": {
                            "server_info.script.keyword": in_script['key']
                        }
                    }
                    query['query']['bool']['must'] = [client_host_match, client_script_match, server_host_match, server_script_match]
                    query['aggs']['agg']['terms']['field'] = "method.keyword"
                    resp = elastic_search_client.search(index="grpc-events", query=query['query'], aggs=query['aggs'],
                                                        size=query['size'])
                    methods = resp['aggregations']['agg']['buckets']
                    # print(json.dumps(methods, indent=1))
                    # for method in methods:
                    for method in [1]:

                        # method_match = {
                        #     "match": {
                        #         "method.keyword": method['key']
                        #     }
                        # }
                        query['query']['bool']['must'] = [client_host_match, client_script_match, server_host_match,
                                                          server_script_match]#, method_match]

                        query['aggs'] = {
                            "sum_client_time": {
                                "sum": {
                                    "field": "client_side_time"
                                }
                            },
                            "sum_server_time": {
                                "sum": {
                                    "field": "server_side_time"
                                }
                            },
                            "sum_network_time": {
                                "sum": {
                                    "field": "network_time"
                                }
                            },
                            "number_of_calls": {
                                "value_count": {
                                    "field": "GUID.keyword"
                                }
                            },
                            "first_time_call": {
                                "min": {
                                    "field": "timestamp"
                                }
                            },
                            "last_time_call": {
                                "max": {
                                    "field": "timestamp"
                                }
                            }
                        }
                        # print(json.dumps(query, indent=2))
                        resp = elastic_search_client.search(index="grpc-events", query=query['query'],
                                                            aggs=query['aggs'],
                                                            size=query['size'])

                        t_first = datetime.datetime.fromisoformat(resp['aggregations']['first_time_call']['value_as_string'][:-1])
                        t_last  = datetime.datetime.fromisoformat(resp['aggregations']['last_time_call' ]['value_as_string'][:-1])
                        count = resp['aggregations']['number_of_calls']['value']

                        edge = {
                            # "type" : "edge",
                            "id" : str(uuid.uuid4()),
                            # "service_src"
                            "source" : out_host['key']+':'+out_script['key'].split('/')[-1],
                            # "service_dest"
                            "target" : in_host['key']+':'+in_script['key'].split('/')[-1],

                            # "detail_total_network_time" : resp['aggregations']['sum_network_time']['value'],
                            "detail_total_client_time"  : resp['aggregations']['sum_client_time']['value'],
                            # "detail_total_server_time"  : resp['aggregations']['sum_server_time']['value'],
                            "frequency"          : count,
                            # "detail_method"             : method['key'],
                            "timestamp"                 : datetime.datetime.now()
                        }
                        elastic_search_client.index(index="grpc-dependencies", document=edge)




def main():
    es = elasticsearch.Elasticsearch(hosts = 'http://0.0.0.0:9200')
    retries = 5
    while not es.ping() and retries > 0:
        retries -= 1
        time.sleep(1)

    if not es.ping():
        raise Exception("can't connect to Elasticsearch")

    def final(signal, frame):
        es.close()
        print(f"finished by signal code {signal}")
        sys.exit(0)

    signal.signal(signal.SIGINT, final)
    signal.signal(signal.SIGTERM, final)

    # functions = [grpc_events, make_dependency_graph]
    functions = [make_dependency_graph]

    while True:
        for func in functions:
            func(es)
        # grpc_events(es)
        print("go to sleep")
        # time.sleep(5*60)
        break


if __name__ == "__main__":
    main()