import contextlib
import random
import os
import time

import grpc

import user_service_pb2
import user_service_pb2_grpc

import product_service_pb2
import product_service_pb2_grpc

import order_service_pb2
import order_service_pb2_grpc


PRODUCT_SERVER_ADDRESS = os.getenv("PRODUCT_SERVER_ADDRESS", '[::]') + ':50062'
TIMER_IN_SECONDS = os.getenv("TIMER_IN_SECONDS", 1)

def main():
    with contextlib.ExitStack() as stack:
        product_chanel = stack.enter_context(grpc.insecure_channel(PRODUCT_SERVER_ADDRESS))

        product_stub = product_service_pb2_grpc.ProductServiceStub(product_chanel)

        while True:
            action = random.randint(0, 0)
            item_id = random.randint(0, 128)
            try:
                if action == 0:
                    print(f'Action is GetProduct')
                    print(product_stub.GetProduct(product_service_pb2.ProductId(Id=item_id)))
                print('-'*20)
            except Exception as e:
                print(f'error is {e}')
            time.sleep(TIMER_IN_SECONDS)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print('finished')