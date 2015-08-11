import BaseHTTPServer
import sys, random, os, socket, urllib, json, urlparse, cgi




class Handler(BaseHTTPServer.BaseHTTPRequestHandler):
  
  def do_GET(self):
      print self.path
      print self.headers 
      self.send_response(200, 'OK')
      self.send_header('Content-type', 'text/html')
      self.end_headers()
      
      self.wfile.write('HELLO WORLD')
        
   
  
 
    
    
def main():
  
  if 'PORT' in os.environ:
    HOST, PORT = socket.gethostname(), int(os.environ['PORT'])
  else:
    HOST, PORT = "localhost", random.choice(range(5000, 10000))
  httpd = BaseHTTPServer.HTTPServer(("", PORT), Handler)
  print "serving at port", PORT
  httpd.serve_forever()
  
main()