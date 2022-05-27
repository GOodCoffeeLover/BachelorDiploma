import contextlib
import datetime
import random
import os
import time
import numpy

import grpc

import report_service_pb2
import report_service_pb2_grpc

import user_service_pb2
import user_service_pb2_grpc


USER_SERVER_ADDRESS = os.getenv("USER_SERVER_ADDRESS", '[::]') + ':50061'
REPORT_SERVER_ADDRESS = os.getenv("REPORT_SERVER_ADDRESS", '[::]') + ':50064'
TIMER_IN_SECONDS = float(os.getenv("TIMER_IN_SECONDS", 1))

def main():
    with contextlib.ExitStack() as stack:
        user_chanel = stack.enter_context(grpc.insecure_channel(USER_SERVER_ADDRESS))
        report_chanel = stack.enter_context(grpc.insecure_channel(REPORT_SERVER_ADDRESS))

        userStub = user_service_pb2_grpc.UserServiceStub(user_chanel)
        reportStub = report_service_pb2_grpc.ReportServiceStub(report_chanel)

        number_of_actions = 3
        runs = [numpy.zeros(()) for _ in range(number_of_actions)]
        action_names = ['GetUser', 'GetReport']

        while True:
            action = random.randint(0, 1)
            item_id = random.randint(0, 128)
            try:
                start = datetime.datetime.utcnow()
                if action == 0:
                    print(f'Action is GetUser')
                    print(userStub.GetUser(user_service_pb2.UserId(Id=item_id)))
                elif action == 1:
                    print(f'Action is GetReport')
                    print(reportStub.GetReport(report_service_pb2.ReportId(Id=item_id)))
                end = datetime.datetime.utcnow()
                total = (end - start).total_seconds()*1000

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