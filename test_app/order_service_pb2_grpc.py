# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

import order_service_pb2 as order__service__pb2


class OrderServiceStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """

        # =========================================================
        #          Generated by grpc_tracer.proto_gen
        # =========================================================
        # vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
        import grpc_tracer
        my_intercepotor = grpc_tracer.ClientTracer()
        channel = grpc.intercept_channel(channel, my_intercepotor)
        # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        
        self.GetOrder = channel.unary_unary(
                '/OrderService/GetOrder',
                request_serializer=order__service__pb2.OrderId.SerializeToString,
                response_deserializer=order__service__pb2.Order.FromString,
                )


class OrderServiceServicer(object):
    """Missing associated documentation comment in .proto file."""

    def GetOrder(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_OrderServiceServicer_to_server(servicer, server):

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
    
    rpc_method_handlers = {
            'GetOrder': grpc.unary_unary_rpc_method_handler(
                    servicer.GetOrder,
                    request_deserializer=order__service__pb2.OrderId.FromString,
                    response_serializer=order__service__pb2.Order.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'OrderService', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class OrderService(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def GetOrder(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/OrderService/GetOrder',
            order__service__pb2.OrderId.SerializeToString,
            order__service__pb2.Order.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)
