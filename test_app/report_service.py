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
import report_service_pb2
import report_service_pb2_grpc


from concurrent import futures

USER_SERVER_ADDRESS = os.getenv("USER_SERVER_ADDRESS", '[::]') + ':50061'
PRODUCT_SERVER_ADDRESS = os.getenv("PRODUCT_SERVER_ADDRESS", '[::]') + ':50062'
ORDER_SERVER_ADDRESS = os.getenv("ORDER_SERVER_ADDRESS", '[::]') + ':50063'


class ReportServiceServer(report_service_pb2_grpc.ReportServiceServicer):

    def __init__(self):
        self.ProductChanel = grpc.insecure_channel(PRODUCT_SERVER_ADDRESS)
        self.ProductStub = product_service_pb2_grpc.ProductServiceStub(self.ProductChanel)

        self.UserChanel = grpc.insecure_channel(USER_SERVER_ADDRESS)
        self.UserStub = user_service_pb2_grpc.UserServiceStub(self.UserChanel)

        self.OrderChanel = grpc.insecure_channel(ORDER_SERVER_ADDRESS)
        self.OrderStub = order_service_pb2_grpc.OrderServiceStub(self.OrderChanel)

    def GetReport(self, request, context):

        order_id = random.randint(0, 64)

        order = self.OrderStub.GetOrder(order_service_pb2.OrderId(Id=order_id))
        user = self.UserStub.GetUser(user_service_pb2.UserId(Id=order.UserId))
        product = self.ProductStub.GetProduct(product_service_pb2.ProductId(Id=order.ProductId))

        response = report_service_pb2.Report(OrderName=order.Name,
                                             OrderId=order_id,
                                             UserName=user.Name,
                                             ProductName=product.Name,
                                             Count=order.Count)
        return response

    def __del__(self):
        self.UserChanel.close()
        self.ProductChanel.close()
        self.OrderChanel.close()




def serve():
    try:
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
        report_service_pb2_grpc.add_ReportServiceServicer_to_server(
            ReportServiceServer(), server)
        server.add_insecure_port('[::]' + ':50064')
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
