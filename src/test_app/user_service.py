import random
import signal
import os

import grpc
import user_service_pb2
import user_service_pb2_grpc
from concurrent import futures

NUMBER_OF_ITERATIONS = int(os.getenv("NUMBER_OF_ITERATIONS", 1000))

class UserServiceServer(user_service_pb2_grpc.UserServiceServicer):

    def __init__(self):
        self.Names = ['Alice', 'Bob', 'Cate', 'Dom', 'Evgeniy', 'Fedor']

    def GetUser(self, request, context):

        response = user_service_pb2.User(Name=random.choice(self.Names))

        prod = 1
        for i in range(NUMBER_OF_ITERATIONS):
            prod *= i

        return response

def serve():
    try:
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
        user_service_pb2_grpc.add_UserServiceServicer_to_server(
            UserServiceServer(), server)
        server.add_insecure_port('[::]' + ':50061')
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
