import contextlib
import datetime
import random
import os
import time
import numpy
import datetime

import grpc

import user_service_pb2
import user_service_pb2_grpc

import product_service_pb2
import product_service_pb2_grpc

import order_service_pb2
import order_service_pb2_grpc


USER_SERVER_ADDRESS = os.getenv("USER_SERVER_ADDRESS", '[::]') + ':50061'
PRODUCT_SERVER_ADDRESS = os.getenv("PRODUCT_SERVER_ADDRESS", '[::]') + ':50062'
ORDER_SERVER_ADDRESS = os.getenv("ORDER_SERVER_ADDRESS", '[::]') + ':50063'
TIMER_IN_SECONDS = os.getenv("TIMER_IN_SECONDS", 1)

def main():
    with contextlib.ExitStack() as stack:
        user_chanel = stack.enter_context(grpc.insecure_channel(USER_SERVER_ADDRESS))
        product_chanel = stack.enter_context(grpc.insecure_channel(PRODUCT_SERVER_ADDRESS))
        order_chanel = stack.enter_context(grpc.insecure_channel(ORDER_SERVER_ADDRESS))

        userStub = user_service_pb2_grpc.UserServiceStub(user_chanel)
        productStub = product_service_pb2_grpc.ProductServiceStub(product_chanel)
        orderStub = order_service_pb2_grpc.OrderServiceStub(order_chanel)

        number_of_actions = 3
        runs = [numpy.zeros(()) for _ in range(number_of_actions)]
        action_names = ['GetUser', 'GetProduct', 'GetOrder']

        while True:
            action = random.randint(0, 2)
            item_id = random.randint(0, 128)

            try:
                start = datetime.datetime.utcnow()
                if action == 0:
                    print(f'Action is GetUser')
                    print(userStub.GetUser(user_service_pb2.UserId(Id=item_id)))
                elif action == 1:
                    print(f'Action is GetProduct')
                    print(productStub.GetProduct(product_service_pb2.ProductId(Id=item_id)))
                elif action == 2:
                    print(f'Action is GetOrder')
                    print(orderStub.GetOrder(order_service_pb2.OrderId(Id=item_id)))
                end = datetime.datetime.utcnow()
                total = (end - start).total_seconds() * 1000

                runs[action] = numpy.append(runs[action], total)
                for run, name in zip(runs, action_names):
                    print(f'Action {name} take {run[run > 0].mean()} ms in average')

                print('-'*20)
            except Exception as e:
                print(f'error is {e}')
            time.sleep(TIMER_IN_SECONDS)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print('finished')