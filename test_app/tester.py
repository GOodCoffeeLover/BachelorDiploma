import grpc
import user_service_pb2
import user_service_pb2_grpc
import product_service_pb2
import product_service_pb2_grpc
import order_service_pb2
import order_service_pb2_grpc

import report_service_pb2
import report_service_pb2_grpc


def get(stub):
    for i in range(7):
        print(stub.GetReport(report_service_pb2.ReportId(Id=i)))


def main():
    with grpc.insecure_channel("[::]:50064") as chan:
        stub = report_service_pb2_grpc.ReportServiceStub(chan)
        get(stub)


if __name__ == "__main__":
    main()

