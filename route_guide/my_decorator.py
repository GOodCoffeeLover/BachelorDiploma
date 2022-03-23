import grpc
import grpc_interceptor

import types

# for server check https://realpython.com/python-microservices-grpc/#interceptors \/checked
def main():
  pass



def get_first(generator):
  
  first = next(generator)

  def put_back(_first, _generator):
    yield _first
    for elem in _generator:
      yield elem

  return first, put_back(first, generator)

def _set_GUID(request_or_iterator, guid):
  if( isinstance(request_or_iterator, types.GeneratorType)):
    
    def put_back(_first, _generator):
      yield _first
      for elem in _generator:
        yield elem

    first_request = next(request_or_iterator)
    first_request.GUID = guid
    request_or_iterator = put_back(first_request, request_or_iterator)

  else:
   
    request_or_iterator.GUID = guid
  
  return request_or_iterator


def _get_GUID(request_or_iterator):
  guid = ''
  print(request_or_iterator.__class__)
  if(isinstance(request_or_iterator, grpc._server._RequestIterator)):
    
    def put_back(_first, _generator):
      yield _first
      for elem in _generator:
        yield elem

    first_request = next(request_or_iterator)
    guid = first_request.GUID
    request_or_iterator = put_back(first_request, request_or_iterator)

  else:
    
    guid = request_or_iterator.GUID


  return guid, request_or_iterator


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
    #print(f'request_or_iterator.__class__ : {request_or_iterator.__class__}\n')
    
    print(f'with request_or_iterator: {request_or_iterator!r}')
    
    request_or_iterator = _set_GUID(request_or_iterator, 'MY_VERY_UNIQUE_GUID')

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


class MyServerInterceptor(grpc_interceptor.ServerInterceptor):
  def __init__(self):
    pass

  def intercept(self, method, request, context, method_name):
    # print(repr(handler_call_details))
    # print(handler_call_details._fields)
    # print(handler_call_details.GUID)


    print(f'get method {method_name}')


    guid, request_or_iterator = _get_GUID(request)
    print(guid)
    result = method(request, context)
    print(f'did method {method_name}')
    print('-'*50)
    return result



if __name__ == '__main__':
  main()
