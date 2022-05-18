import multiprocessing
import re
import signal

import grpc
import grpc_interceptor

import types
import uuid
import inspect
import datetime
import socket
import json
import sys
import __main__
import requests

from grpc_tools import protoc

# for server check https://realpython.com/python-microservices-grpc/#interceptors \/checked

MAX_QUEUE_SIZE = 100


def _set_GUID(request_or_iterator, guid):
    if (isinstance(request_or_iterator, types.GeneratorType)):

        def put_back(_first, _generator):
            yield _first
            for elem in _generator:
                yield elem

        first_request = next(request_or_iterator)
        first_request.GUID = guid
        request_or_iterator = put_back(first_request, request_or_iterator)

    else:

        request_or_iterator.GUID = guid

    return request_or_iterator


def _get_GUID(request_or_iterator):
    guid = ''

    if (isinstance(request_or_iterator, grpc._server._RequestIterator)):

        def put_back(_first, _generator):
            yield _first
            for elem in _generator:
                yield elem

        first_request = next(request_or_iterator)

        guid = first_request.GUID
        first_request.GUID = ''

        request_or_iterator = put_back(first_request, request_or_iterator)

    else:

        guid = request_or_iterator.GUID

    return guid, request_or_iterator


def send(list_of_msgs):
    try:
        requests.post("http://0.0.0.0:8000", data=json.dumps(list_of_msgs))
    except Exception as exp:
        print(f'can\'t send info to MDS-platform cause of {exp}')


def sink_sender(queue):

    list_of_msgs = []

    def handle_term_or_kill(*_):
        while not queue.empty():
            list_of_msgs.append(queue.get())
        if len(list_of_msgs) > 0:
            send(list_of_msgs)
        list_of_msgs.clear()
        sys.exit()

    # signal.signal(signal.SIGKILL, handle_term_or_kill)
    signal.signal(signal.SIGTERM, handle_term_or_kill)

    try:
        while True:
            list_of_msgs.append(queue.get())

            if len(list_of_msgs) >= MAX_QUEUE_SIZE / 10:
                send(list_of_msgs)
                list_of_msgs = []
    except KeyboardInterrupt:
        print("Interrupted")
    finally:
        handle_term_or_kill()


class ClientTracer(grpc.UnaryUnaryClientInterceptor,
                   grpc.StreamUnaryClientInterceptor,
                   grpc.UnaryStreamClientInterceptor,
                   grpc.StreamStreamClientInterceptor):
    def __init__(self):
        self._queue = multiprocessing.Queue(MAX_QUEUE_SIZE)
        self._process = multiprocessing.Process(target=sink_sender, args=(self._queue,), daemon=True)
        self._process.start()

    def __del__(self):
        self._process.terminate()
        self._process.join()

    def intercept(self, continuation, client_call_details, arg):
        guid = str(uuid.uuid4())
        argument = _set_GUID(arg, guid)
        event_type = None
        def send_info(resp=None):
            time = datetime.datetime.now()
            status = ''
            if not(resp is None):
                status = resp.code()
            msg = {
                "hostname": socket.gethostname(),
                "script": __main__.__file__,
                "type": event_type,
                "method": str(client_call_details.method),
                "function_path": "",
                "argument": str(arg),
                "GUID": guid,
                "time": str(time),
                "status": None if resp is None else str(status).split(sep='.')[1],
                "details": ""
            }

            function_path = ''
            stack = inspect.stack()
            for i in range(len(stack) - 1, -1, -1):
                function_path += '/' + str(stack[i].function)

            msg["function_path"] = function_path

            if not(resp is None) and status is not grpc.StatusCode.OK:
                msg["details"] = str(resp.exception().details())
            # send to proc_sender
            self._queue.put(msg)

        event_type = "grpc-client-call-send"
        send_info()
        response = continuation(client_call_details, argument)
        event_type = "grpc-client-call-receive"
        response.add_done_callback(send_info)

        return response

    def intercept_unary_unary(self, continuation, client_call_details, request):
        return self.intercept(continuation, client_call_details, request)

    def intercept_unary_stream(self, continuation, client_call_details, request):
        return self.intercept(continuation, client_call_details, request)

    def intercept_stream_unary(self, continuation, client_call_details, request_it):
        return self.intercept(continuation, client_call_details, request_it)

    def intercept_stream_stream(self, continuation, client_call_details, request_it):
        return self.intercept(continuation, client_call_details, request_it)


# def add_RouteGuideServicer_to_server(servicer, server):

#   import grpc_tracer

#   if ( server._state.interceptor_pipeline is None ) :
#     server._state.interceptor_pipeline = grpc._interceptor.service_pipeline([grpc_tracer.ServerTracer()])

#   else:
#     list_interceptors = list(server._state.interceptor_pipeline.interceptors)
#     list_interceptors.append(grpc_tracer.ServerTracer())
#     server._state.interceptor_pipeline.interceptors = tuple(list_interceptors)


class ServerTracer(grpc_interceptor.ServerInterceptor):

    def __init__(self):
        self._queue = multiprocessing.Queue(MAX_QUEUE_SIZE)
        self._process = multiprocessing.Process(target=sink_sender, args=(self._queue,), daemon=True)
        self._process.start()

    def __del__(self):
        self._process.terminate()
        self._process.join()

    def intercept(self, method, request, context, method_name):

        guid, request_or_iterator = _get_GUID(request)
        event_type = ''
        def send_info():
            time = datetime.datetime.now()
            status = context.code()
            msg = {
                "hostname": socket.gethostname(),
                "script": __main__.__file__,
                "type": event_type,
                "method": str(method_name),
                "function_path": "",
                "argument": str(request),
                "GUID": guid,
                "time": str(time),
                "status": None if status is None else str(status).split(sep='.')[1],
                "details": ""
            }

            function_path = ''
            stack = inspect.stack()
            for i in range(len(stack) - 1, -1, -1):
                function_path += '/' + str(stack[i].function)

            msg["function_path"] = function_path

            if not (status is None) and status is not grpc.StatusCode.OK:
                msg["details"] = str(context.details().decode("utf-8"))
            # send to proc_sender
            self._queue.put(msg)
        event_type = "grpc-server-call-receive"
        send_info()
        event_type = "grpc-server-call-send"
        context.add_callback(send_info)
        try:
            response = method(request, context)
            if context.code() is None:
                context.set_code(grpc.StatusCode.OK)
        except Exception as e:
            if context.code() is None:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(repr(e))
            raise e

        return response


def _join_back(list_of_text, list_of_mathces):
    res = list_of_text[0]
    for match, text in zip(list_of_mathces, list_of_text[1:]):
        res += match + text
    return res


def _add_guid_to_proto(file_name):
    # data = ''
    with open(file_name, 'r') as in_file:
        data = in_file.read()

        msg_regex = 'message\s+\w+\s*\{[\s\S]*?\}'
        list_of_msgs = re.findall(msg_regex, data)
        another_text = re.split(msg_regex, data)

        for idx, msg in enumerate(list_of_msgs):
            start_re = re.compile('\d+\s*;\s*\}')
            end_re = re.compile('\s*;\s*\}')
            start = start_re.search(msg).start()
            end = end_re.search(msg).start()
            guid_num = int(msg[start:end]) + 1

            list_of_msgs[idx] = msg[0:-1] + f'\n  //GUID\n  string GUID = {guid_num};\n}}'

        data = _join_back(another_text, list_of_msgs)
        # print(data)
    with open(file_name, 'w') as out_file:
        out_file.write(data)


def _insert_interceptors(file_name):
    client_tracer = """
        # =========================================================
        #          Generated by grpc_tracer.proto_gen
        # =========================================================
        # vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
        import grpc_tracer
        my_intercepotor = grpc_tracer.ClientTracer()
        channel = grpc.intercept_channel(channel, my_intercepotor)
        # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        \n"""
    server_tracer = """
    # =========================================================
    #           Generated by grpc_tracer.proto_gen
    # =========================================================
    # vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
    import grpc_tracer
    if  server._state.interceptor_pipeline is None  :
        server._state.interceptor_pipeline = grpc._interceptor.service_pipeline([grpc_tracer.ServerTracer()])
    else:
        list_interceptors = list(server._state.interceptor_pipeline.interceptors)
        list_interceptors.append(grpc_tracer.ServerTracer())
        server._state.interceptor_pipeline.interceptors = tuple(list_interceptors)
    # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    \n"""
    client_re = 'class \w+Stub\(?\w*\)?:[\s\S]+?def\s__init__\(.*\):\s+"""[\s\S]+?"""\s*\n'
    server_re = 'def \w+Servicer_to_server\(.*\):\n'

    with open(file_name, 'r') as file:
        data = file.read()

        stubs_inits = re.findall(client_re, data)
        text = re.split(client_re, data)
        stubs_inits = [init + client_tracer for init in stubs_inits]

        data = _join_back(text, stubs_inits)

        servicer_adds = re.findall(server_re, data)
        text = re.split(server_re, data)
        servicer_adds = [adds + server_tracer for adds in servicer_adds]

        data = _join_back(text, servicer_adds)

    with open(file_name, 'w') as file:
        file.write(data)


def proto_gen(command_arguments):
    files = []

    for i, arg in enumerate(command_arguments):
        if i == 0 or arg[0] == '-':
            continue
        files.append(arg)
        _add_guid_to_proto(arg)

    protoc.main(command_arguments)

    for file in [f[:-6] + '_pb2_grpc.py' for f in files]:
        _insert_interceptors(file)
