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
    # needed_fields = ["GUID", "type", "time",  "hostname", "script", "status", "details", "method", "argument"]
    # for field in needed_fields:
    #     if field not in msg.keys():
    #         return {}
    guid = msg["GUID"]
    if guid not in data:
        data[guid] = {"recv_time" : str(datetime.datetime.now())}

    data[guid][msg["type"]] = msg

    if len(data[guid]) < 5:
        return {}

    info = data[guid]

    t0 = datetime.datetime.fromisoformat(info["grpc-client-call-send"]["time"])
    t1 = datetime.datetime.fromisoformat(info["grpc-server-call-receive"]["time"])
    t2 = datetime.datetime.fromisoformat(info["grpc-server-call-send"]["time"])
    t3 = datetime.datetime.fromisoformat(info["grpc-client-call-receive"]["time"])

    inf = {
        "type"                       : "grpc-call",
        "recive_time"                : info["recv_time"],
        "method"                     : info["grpc-client-call-receive"]["method"],
        "argument"                   : info["grpc-client-call-receive"]["argument"],
        "GUID"                       : guid,
        "client_side_time_in_seconds": float((t3 - t0).total_seconds()),
        "server_side_time_in_seconds": float((t2 - t1).total_seconds()),
        "network_time_in_seconds"    : float(((t3 - t0) - (t2 - t1)).total_seconds()),
        "client_hostname"            : info["grpc-client-call-receive"]["hostname"],
        "client_source"              : info["grpc-client-call-receive"]["script"],
        "server_hostname"            : info["grpc-server-call-send"]["hostname"],
        "server_source"              : info["grpc-server-call-send"]["script"],
        "status"                     : info["grpc-server-call-send"]["status"],
        "details"                    : info["grpc-server-call-send"]["details"]
    }

    del data[guid]
    return inf

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
            res = calculate_basic_metrics(q.get())
            if len(res) != 0:
                print(json.dumps(res, indent=2))
    except Exception as e:
        print(e)
    finally:
        proc.terminate()
        proc.join()


if __name__ == "__main__":
    main()
