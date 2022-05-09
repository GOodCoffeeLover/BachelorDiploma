import re

import grpc
import grpc_interceptor

import types
import uuid
import inspect
import datetime
import socket
import json

from grpc_tools import protoc

# for server check https://realpython.com/python-microservices-grpc/#interceptors \/checked


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


# class ServiceStub():
# def __init__(self):

# import grpc_tracer
# my_intercepotor = grpc_tracer.ClientTracer()
# channel = grpc.intercept_channel(channel, my_intercepotor)


class ClientTracer(grpc.UnaryUnaryClientInterceptor,
                   grpc.StreamUnaryClientInterceptor,
                   grpc.UnaryStreamClientInterceptor,
                   grpc.StreamStreamClientInterceptor):
    def __init__(self):
        pass

    def intercept(self, continuation, client_call_details, argument):
        guid = str(uuid.uuid4())
        argument = _set_GUID(argument, guid)

        def send_info(response):
            time1 = datetime.datetime.now()
            status = response.code()
            msg = {
                "hostname"  : socket.gethostname(),
                "sqript"    : __file__,
                "type"      : "gRPC-client-call",
                "method"    : str(client_call_details.method),
                "function_path" : "",
                "argument"  : str(argument),
                "GUID"      : guid,
                "time0"     : str(time0),
                "time1"     : str(time1),
                "status"    : str(status).split(sep='.')[1],
                "details"   : ""
            }

            function_path = ''
            stack = inspect.stack()
            for i in range(len(stack) - 1, 5, -1):
                function_path += '/' + str(stack[i].function)

            msg["function_path"] = function_path

            if status is not grpc.StatusCode.OK:
                msg["details"] = str(response.exception().details())
            # send to proc_sender
            print('\\' * 50)
            import sys
            print(json.dumps(msg, indent=2), file=sys.stderr)
            print('/' * 50)

        time0 = datetime.datetime.now()
        response = continuation(client_call_details, argument)

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
        pass

    def intercept(self, method, request, context, method_name):

        guid, request_or_iterator = _get_GUID(request)

        def send_info():
            time1 = datetime.datetime.now()
            status = context.code()
            msg = {
                "hostname": socket.gethostname(),
                "sqript": __file__,
                "type": "gRPC-server-call",
                "method": str(method_name),
                "function_path": "",
                "argument": str(request),
                "GUID": guid,
                "time0": str(time0),
                "time1": str(time1),
                "status": str(status).split(sep='.')[1],
                "details": ""
            }

            function_path = ''
            stack = inspect.stack()
            for i in range(len(stack) - 1, 0, -1):
                function_path += '/' + str(stack[i].function)

            msg["function_path"] = function_path

            if status is not grpc.StatusCode.OK:
                msg["details"] = str(context.details())
            # send to proc_sender
            print('\\' * 50)
            import sys
            print(json.dumps(msg, indent=2), file=sys.stderr)
            print('/' * 50)



        context.add_callback(send_info)
        try:
            time0 = datetime.datetime.now()
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

    for file in [f[:-6]+'_pb2_grpc.py' for f in files]:
        _insert_interceptors(file)

