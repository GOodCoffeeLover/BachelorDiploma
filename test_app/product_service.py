import random
import signal
import json

import grpc
import product_service_pb2
import product_service_pb2_grpc
from concurrent import futures


class ProductServiceServer(product_service_pb2_grpc.ProductServiceServicer):

    def __init__(self):
        self.Products = ['apple', 'orange', 'banana', 'coffee', 'milk']
        self.Prices = [i + 0.5 for i in range(7)]

    def GetProduct(self, request, context):
        response = product_service_pb2.Product(Name =random.choice(self.Products),
                                               Price=random.choice(self.Prices))
        return response




def serve():
    try:
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
        product_service_pb2_grpc.add_ProductServiceServicer_to_server(
            ProductServiceServer(), server)
        server.add_insecure_port('[::]' + ':50062')
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
