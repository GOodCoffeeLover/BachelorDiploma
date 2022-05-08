
import grpc
import grpc_interceptor

import types
import uuid
import inspect
import datetime
import socket
import json


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
