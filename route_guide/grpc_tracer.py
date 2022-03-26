import grpc
import grpc_interceptor

import types

# for server check https://realpython.com/python-microservices-grpc/#interceptors \/checked


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
  
  if(isinstance(request_or_iterator, grpc._server._RequestIterator)):
    
    def put_back(_first, _generator):
      yield _first
      for elem in _generator:
        yield elem

    first_request = next(request_or_iterator)
    
    guid = first_request.GUID
    first_request.GUID = ''
    
    request_or_iterator = put_back(first_request, request_or_iterator)

  else:
    
    guid = request_or_iterator.GUID


  return guid, request_or_iterator


# class ServiceStub():
  # def __init__(self):

    # import grpc_tracer
    # my_intercepotor = grpc_tracer.MyClientInterceptor()
    # channel = grpc.intercept_channel(channel, my_intercepotor)


class MyClientInterceptor(grpc.UnaryUnaryClientInterceptor,
                          grpc.StreamUnaryClientInterceptor,
                          grpc.UnaryStreamClientInterceptor,
                          grpc.StreamStreamClientInterceptor):
  def __init__(self):
    pass


  def intercept(self, continuation, client_call_details, request_or_iterator):
    
    print(f'call of : {client_call_details.method}\n\n')
    
    print(f'with request_or_iterator: {request_or_iterator!r}')
    
    request_or_iterator = _set_GUID(request_or_iterator, 'MY_VERY_UNIQUE_GUID')
    
    response = continuation(client_call_details, request_or_iterator)
    
    def callback(response):
      code = response.code()
      if ( code is grpc.StatusCode.OK):
        print(f'call of : {client_call_details.method} executed successfuly\n')
      else:
        print(f'call of : {client_call_details.method} execution failed\n')
        print(f'code = {code}')
        print(f'exception is {response.exception()}')
      # import time
      # time.sleep(0.1)

    response.add_done_callback(callback)

    
    return response
    


  def intercept_unary_unary(self, continuation, client_call_details, request):
    return self.intercept(continuation, client_call_details, request)

  def intercept_unary_stream(self, continuation, client_call_details, request):
    return self.intercept(continuation, client_call_details, request)

  def intercept_stream_unary(self, continuation, client_call_details, request_it): 
    return self.intercept(continuation, client_call_details, request_it)

  def intercept_stream_stream(self, continuation, client_call_details, request_it): 
    return self.intercept(continuation, client_call_details, request_it)



# def add_RouteGuideServicer_to_server(servicer, server):
    
#   import grpc_tracer

#   if ( server._state.interceptor_pipeline is None ) :
#     server._state.interceptor_pipeline = grpc._interceptor.service_pipeline([grpc_tracer.MyServerInterceptor()])
  
#   else:
#     list_interceptors = list(server._state.interceptor_pipeline.interceptors)
#     list_interceptors.append(grpc_tracer.MyServerInterceptor())
#     server._state.interceptor_pipeline.interceptors = tuple(list_interceptors)



class MyServerInterceptor(grpc_interceptor.ServerInterceptor):
  def __init__(self):
    pass

  def intercept(self, method, request, context, method_name):

    print(f'get method {method_name}')

    guid, request_or_iterator = _get_GUID(request)
    print(guid)
    try:
      response = method(request, context)
    except Exception as exception:
      print(f'In method {method_name} error occured : {exception!r}')
      #context.abort(grpc.StatusCode.UNKNOWN,f'Error : {exception!r}')
      #context.set_code(grpc.StatusCode.UNKNOWN)
      #context.set_details(f'Error : {exception!r}')
      raise 
    finally:
      print(f'did method {method_name}')
      print('-'*50)
    return response


