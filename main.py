import BaseHTTPServer, base64, os, random
from firebase import firebase


data = ''
pwd = ''

class Handler(BaseHTTPServer.BaseHTTPRequestHandler):
	def do_GET(self):
		if 'Authorization' not in self.headers:

			self.send_response(401, 'Not authorized')
			self.send_header('Content-type', 'text/html')
			self.send_header('WWW-Authenticate', 'Basic realm="Enter a username and password"')
			self.end_headers()
		else:
			try:
				u = base64.b64decode(self.headers['Authorization'].split()[1])
				print u
				if u == pwd:
					self.send_response(200, 'OK')
					self.send_header('Content-type', 'text/html')
					self.end_headers()
					self.wfile.write(data)
				else:
					raise Exception
			except Exception, e:
				print e
				self.send_response(401, 'Not authorized')
				self.send_header('Content-type', 'text/html')
				self.send_header('WWW-Authenticate', 'Basic realm="Enter a username and password"')
				self.end_headers()


if 'PORT' in os.environ:
	PORT = int(os.environ['PORT'])
else:
	PORT = random.choice(range(5000, 10000))

httpd = BaseHTTPServer.HTTPServer(('', PORT), Handler)

auth = firebase.FirebaseAuthentication(os.environ['FIREBASE_SECRET'],'icse:db', admin=True)
db = firebase.FirebaseApplication('https://icse.firebaseio.com', authentication=auth)

data = db.get('/data', '')
pwd = db.get('/pwd', '')

if pwd == '':
	raise Exception

print "serving at port", PORT

httpd.serve_forever()

