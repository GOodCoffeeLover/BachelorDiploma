import grpc

# for server check https://realpython.com/python-microservices-grpc/#interceptors

def my_decorator(decorated_function):
  def wrapper(*args, **kwargs):
    print('\n==============================\n\nmagic begins\n')
    
    if hasattr(decorated_function, '__name__'):
      print('Call of {}\n'.format(decorated_function.__name__))

    print('with args :')
    for arg in args:
      print(repr(arg))
    
    print('\nand kwargs :')
    for name, arg in zip(kwargs, kwargs.values()):
      print(f'{name!r} = {arg!r}')

    value = decorated_function(*args, **kwargs)
    print("magic ends\n\n==============================\n\n")
    return value

  return wrapper



@my_decorator
def say_something():
  print("wheeee!")



def main():
  say_something()


class MyClientInterceptor(grpc.UnaryUnaryClientInterceptor,
                          grpc.StreamUnaryClientInterceptor,
                          grpc.UnaryStreamClientInterceptor,
                          grpc.StreamStreamClientInterceptor):
  def __init__(self):
    pass


  def intercept(self, continuation, client_call_details, request_or_iterator):
    
    # print(f'continuation : {continuation.__class__} has : {dir(continuation)}\n')

    # print(f'client_call_details : {client_call_details.__class__} has : {dir(client_call_details)}\n')


    print(f'call of : {client_call_details.method}\n\n')
    
    print(f'request_or_iterator : {request_or_iterator.__class__} has : {dir(request_or_iterator)}\n')
    
    print(f'request_or_iterator: {request_or_iterator!r}')
    
    response = continuation(client_call_details, request_or_iterator)

    return response


  def intercept_unary_unary(self, continuation, client_call_details, request):
    return self.intercept(continuation, client_call_details, request)

  def intercept_unary_stream(self, continuation, client_call_details, request):
    return self.intercept(continuation, client_call_details, request)

  def intercept_stream_unary(self, continuation, client_call_details, request_it): 
    return self.intercept(continuation, client_call_details, request_it)

  def intercept_stream_stream(self, continuation, client_call_details, request_it): 
    return self.intercept(continuation, client_call_details, request_it)


if __name__ == '__main__':
  main()
