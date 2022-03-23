import grpc
import types

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

def _set_GUID(request_or_iterator, guid):
  if(isinstance(request_or_iterator, types.GeneratorType)):
    print('ITERATOR')
  else:
    print('NOT ITERATOR')
    request_or_iterator.GUID = guid


def _get_GUID(request_or_iterator):
  if( isinstance(request_or_iterator, types.GeneratorType)):
    print('ITERATOR')
  else:
    print('NOT ITERATOR')
    print(request_or_iterator.GUID)


# class ServiceStub():
  # def __init__(self):

    # import my_decorator
    # my_intercepotor = my_decorator.MyClientInterceptor()
    # channel = grpc.intercept_channel(channel, my_intercepotor)


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
    
    #print(f'request_or_iterator : {request_or_iterator.__class__} has : {dir(request_or_iterator)}\n')
    print(f'request_or_iterator.__class__ : {request_or_iterator.__class__}\n')
    
    print(f'with request_or_iterator: {request_or_iterator!r}')
    
    _set_GUID(request_or_iterator, 'MY_VERY_UNIQUE_GUID')

    response = continuation(client_call_details, request_or_iterator)
    print(f'call of : {client_call_details.method} executed\n')
    return response


  def intercept_unary_unary(self, continuation, client_call_details, request):
    return self.intercept(continuation, client_call_details, request)

  def intercept_unary_stream(self, continuation, client_call_details, request):
    return self.intercept(continuation, client_call_details, request)

  def intercept_stream_unary(self, continuation, client_call_details, request_it): 
    return self.intercept(continuation, client_call_details, request_it)

  def intercept_stream_stream(self, continuation, client_call_details, request_it): 
    return self.intercept(continuation, client_call_details, request_it)



# run():
# interceptors = [my_decorator.MyServerInterceptor()]
# server = grpc.server( futures.ThreadPoolExecutor(max_workers=10), 
#                       interceptors = interceptors)


class MyServerInterceptor(grpc.ServerInterceptor):
  def __init__(self):
    pass

  def intercept_service(self, continuation, handler_call_details):
    print('='*60)
    print(f'\n\nhandler_call_details methods : \n{dir(handler_call_details)}\n\n')
    # print(repr(handler_call_details))
    # print(handler_call_details._fields)
    # print(handler_call_details.GUID)

    for key, value in handler_call_details.invocation_metadata :
      print(f'{key} = {value}')

    print('='*60)

    print(f'get method {handler_call_details.method}')

    result = continuation(handler_call_details)
    print(f'did method {handler_call_details.method}')
    print('-'*50)
    return result



if __name__ == '__main__':
  main()
