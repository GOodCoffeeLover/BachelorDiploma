import signal
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

import json
import multiprocessing

import datetime

MAX_SERVER_QUEUE_SIZE = 100


class SaverHTTPServer(HTTPServer):
    def __init__(self, server_address, RequestHandlerClass, queue):
        HTTPServer.__init__(self, server_address, RequestHandlerClass)
        self.queue = queue


class SaverHttpHandler(BaseHTTPRequestHandler):
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

            for dictio in recv_dicts:
                self.server.queue.put(dictio)

            self.send_response(200, "OK")
            self.end_headers()

        except Exception as e:
            self.send_error(501, message=str(e))


def run(queue, server_class=SaverHTTPServer, handler_class=SaverHttpHandler):
    server_address = ('0.0.0.0', 8000)
    httpd = server_class(server_address, handler_class, queue)

    def finish(*_):
        httpd.server_close()
        print("server has been stopped")
        sys.exit()

    signal.signal(signal.SIGTERM, finish)

    try:
        httpd.serve_forever()
    except Exception as e:
        print(e)
    finally:
        httpd.server_close()

def calculate_basic_metrics(msg, data = {}):
    needed_fields = ["GUID", "type", "time0", "time1", "hostname", "script", "status", "details", "method", "argument"]
    for field in needed_fields:
        if field not in msg.keys():
            return {}
    if msg["GUID"] not in data:
        msg["recv_time"] = datetime.datetime.now()
        data[msg["GUID"]] = msg
        return {}

    # calc metrics
    client_msg = {}
    server_msg = {}
    recv_time = ''
    if msg["type"] == "gRPC-server-call":
        server_msg = msg
        client_msg = data[msg["GUID"]]
        recv_time = client_msg["recv_time"]
    else:
        server_msg = data[msg["GUID"]]
        client_msg = msg
        recv_time = server_msg["recv_time"]

    t0 = datetime.datetime.fromisoformat(client_msg["time0"])
    t1 = datetime.datetime.fromisoformat(server_msg["time0"])
    t2 = datetime.datetime.fromisoformat(server_msg["time1"])
    t3 = datetime.datetime.fromisoformat(client_msg["time1"])

    info = {
        "type"                       : "grpc-call",
        "recive_time"                : str(recv_time),
        "method"                     : client_msg["method"],
        "argument"                   : client_msg["argument"],
        "GUID"                       : msg["GUID"],
        "client_side_time_in_seconds": float((t3 - t0).total_seconds()),
        "server_side_time_in_seconds": float((t2 - t1).total_seconds()),
        "network_time_in_seconds"    : float(((t3 - t0) - (t2 - t1)).total_seconds()),
        "client_hostname"            : client_msg["hostname"],
        "client_source"              : client_msg["script"],
        "server_hostname"            : server_msg["hostname"],
        "server_source"              : server_msg["script"],
        "status"                     : server_msg["status"],
        "details"                    : server_msg["details"]
    }

    del data[msg["GUID"]]


    return info




def main():
    q = multiprocessing.Queue(MAX_SERVER_QUEUE_SIZE)
    proc = multiprocessing.Process(target=run, args=(q,), daemon=True)
    proc.start()

    def finish(*_):
        proc.terminate()
        sys.exit()

    signal.signal(signal.SIGINT, finish)
    signal.signal(signal.SIGTERM, finish)
    try:
        while True:
            print(json.dumps(calculate_basic_metrics(q.get()), indent=2))
    except Exception as e:
        print(e)
    finally:
        proc.terminate()
        proc.join()


if __name__ == "__main__":
    main()
