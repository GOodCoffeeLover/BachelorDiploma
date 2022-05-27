import os
import random
import signal

import grpc
import user_service_pb2
import user_service_pb2_grpc
import product_service_pb2
import product_service_pb2_grpc
import order_service_pb2
import order_service_pb2_grpc

from concurrent import futures

USER_SERVER_ADDRESS = os.getenv("USER_SERVER_ADDRESS", '[::]') + ':50061'
PRODUCT_SERVER_ADDRESS = os.getenv("PRODUCT_SERVER_ADDRESS", '[::]') + ':50062'


class OrderServiceServer(order_service_pb2_grpc.OrderServiceServicer):

    def __init__(self):
        self.ProductChanel = grpc.insecure_channel(PRODUCT_SERVER_ADDRESS)
        self.ProductStub = product_service_pb2_grpc.ProductServiceStub(self.ProductChanel)
        self.UserChanel = grpc.insecure_channel(USER_SERVER_ADDRESS)
        self.UserStub = user_service_pb2_grpc.UserServiceStub(self.UserChanel)

    def GetOrder(self, request, context):
        user_id = random.randint(0, 64)
        product_id = random.randint(0, 64)

        user = self.UserStub.GetUser(user_service_pb2.UserId(Id=user_id))
        product = self.ProductStub.GetProduct(product_service_pb2.ProductId(Id=product_id))

        response = order_service_pb2.Order(Name=user.Name + ' ' + product.Name,
                                           UserId=user_id,
                                           ProductId=product_id,
                                           Count=random.randint(0, 128))

        return response

    def __del__(self):
        self.UserChanel.close()
        self.ProductChanel.close()





def serve():
    try:
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
        order_service_pb2_grpc.add_OrderServiceServicer_to_server(
            OrderServiceServer(), server)
        server.add_insecure_port('[::]' + ':50063')
        server.start()

        def handle_sigterm(sig, term):
            print()
            print(f"Received shutdown by signal {sig}")
            all_rpcs_done_event = server.stop(10)
            all_rpcs_done_event.wait(10)
            print("Shut down gracefully")

        # signal(SIGTERM, handle_sigterm)
        signal.signal(signal.SIGINT, handle_sigterm)
        server.wait_for_termination()
    except Exception as e:
        print(f'Error is {e!r} ')


if __name__ == '__main__':
    serve()
