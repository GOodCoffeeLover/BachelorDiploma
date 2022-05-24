import signal
import sys
import os
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from concurrent.futures import ThreadPoolExecutor

import json
import elasticsearch
import multiprocessing

import datetime

MAX_SERVER_QUEUE_SIZE = 100
ELASTICSEARCH_ADDRESS = 'http://' + os.getenv("ELASTICSEARCH_ADDRESS", "0.0.0.0") + ':9200'

# class QueueSaverHTTPServer(ThreadingMixIn, HTTPServer):
class QueueSaverHTTPServer(HTTPServer):

    def __init__(self, server_address, RequestHandlerClass, queue):
            # ThreadingMixIn.__init__(self)
        HTTPServer.__init__(self, server_address, RequestHandlerClass)
        self.queue = queue




class QueueSaverHttpHandler(BaseHTTPRequestHandler):
    # def do_GET(self):
    #     print(self.request)
    #     self.send_response(200, "OK")
    #     self.send_header('Content-type', 'string')
    #     self.end_headers()
    #     self.wfile.write("it's succes".encode("utf-8"))

    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            raw_data = self.rfile.read(content_length)
            recv_dicts = json.loads(raw_data)

            for event in recv_dicts:
                doc = {
                    "timestamp" : datetime.datetime.utcnow(),
                    "event" : event,
                }
                self.server.queue.put(doc)

            self.send_response(200, "OK")
            self.end_headers()

        except Exception as e:
            self.send_error(501, message=str(e))


def run(queue, server_class=QueueSaverHTTPServer, handler_class=QueueSaverHttpHandler):
    server_address = ('0.0.0.0', 8000)
    httpd = server_class(server_address, handler_class, queue)

    def finish(singnal, frame):
        httpd.server_close()
        print(f"daemon has been stopped by signal {singnal}")
        sys.exit()

    signal.signal(signal.SIGTERM, finish)
    signal.signal(signal.SIGINT, finish)

    try:
        httpd.serve_forever()
    except Exception as e:
        print(f'daemon error is {e}')


def send_event_to_es(es, doc):
    try:
        resp = es.index(index="events", document=doc)
    except Exception as e:
        print(e)
        raise




def main():
    es = elasticsearch.Elasticsearch(hosts=ELASTICSEARCH_ADDRESS)

    retries = 5
    while not es.ping() and retries != 0:
        retries -= 1
        time.sleep(1)

    if not es.ping() and retries == 0:
        raise Exception(f"can't connect to Elasticsearch at {ELASTICSEARCH_ADDRESS}")

    q = multiprocessing.Queue(MAX_SERVER_QUEUE_SIZE)
    proc = multiprocessing.Process(target=run, args=(q,), daemon=True)
    proc.start()

    def finish(signal, frame):
        es.close()
        print(f'Main proc was stoped by signal {signal}')
        # proc.terminate()
        sys.exit()

    signal.signal(signal.SIGINT, finish)
    signal.signal(signal.SIGTERM, finish)


    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            while True:
                doc = q.get()
                # send_event_to_es(es, doc)
                executor.submit(send_event_to_es, es, doc)
    except Exception as e:
        print(f'Main proc error is {e}')
        finish(-1, -1)



if __name__ == "__main__":
   main()
