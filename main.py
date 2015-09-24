import BaseHTTPServer
import gzip
import logging
import os
import pymongo
import random
import sha
import sys
import tempfile
import urlparse
from bs4 import BeautifulSoup as bs

def sha_hash(content):
	return sha.new(content).hexdigest()

def mime(path):
	for i in mimetable:
		if path.endswith(i):
			return mimetable[i]
	logging.warn('Mime type not found for' + path)
	return 'text/plain'

def gzip_content(content):
	h = sha_hash(content) + '.gzip'
	if os.path.isfile(h):
		with open(h,'rb') as fin:
			return fin.read()
	with gzip.open(h, 'wb') as fout:
		fout.write(content)
	fout.close()
	with open(h, 'rb') as fin:
		return fin.read()

def has_gzip(self):
	if 'Accept-Encoding' in self.headers and 'gzip' in self.headers['Accept-Encoding']:
		return True
	else:
		return False

def smart_reply(self, resp):
	if self.has_gzip():
		self.send_header('Content-Encoding', 'gzip')
		self.end_headers()
		self.wfile.write(gzip_content(resp))
	else:
		self.end_headers()
		self.wfile.write(resp)

abbrev = {
	"COMPUTER APPLICATIONS" : "CS",
	"HISTORY CIVICS & GEOGRAPHY" : "HCG",
	"MATHEMATICS" : "MATH",
	"BIOLOGY" : "BIO"
}

# let's be a nice compliant server
mimetable = {
	".css" : "text/css",
	".eot" : "application/octet-stream",
	".html" : "text/html",
	".png" : "image/png",
	".svg" : "image/svg+xml",
	".ttf" : "application/x-font-ttf",
	".woff" : "application/octet-stream",
	".woff2" : "application/octet-stream",
}

hash_lookup = {}

def populate(json, school=False):
	subject_counts = {}
	l = []
	for i in json:
		l.append(i)
		for j in i['marks']:
			if j in subject_counts:
				subject_counts[j] += 1
			else:
				subject_counts[j] = 1
	soup = bs(open('web/results.html').read(), 'lxml')
	headers = soup.find(id="headers")
	data = soup.find(id="data")
	meta = ['Name', 'UID', 'Score']
	if school:
		meta.append('School')
	for i in meta:
		h  = soup.new_tag("th")
		h.string = i
		headers.append(h)
	pairs = []
	for i in subject_counts:
		pairs.append( (subject_counts[i], i) )
	pairs.sort(key = lambda x: (-x[0], x[1]))

	for j in pairs:
		h = soup.new_tag("th")
		if j[1] in abbrev:
			h.string = abbrev[j[1]]
		else:
			h.string = j[1]
		headers.append(h)
	meta = ['name', '_id', 'best5']
	if school:
		meta.append('school') 
	for i in l:
		row = soup.new_tag("tr")
		for j in meta:
			f = soup.new_tag("td")
			f.string = i[j]
			row.append(f)
		for j in pairs:
			f = soup.new_tag("td")
			if j[1] in i["marks"]:
				f.string = i["marks"][j[1]]
			else:
				f.string = ''
			row.append(f)
				
		data.append(row)	
	
	return soup.prettify().encode('utf-8')
	


class Handler(BaseHTTPServer.BaseHTTPRequestHandler):
	def do_GET(self):
		if '--force-ssl' in sys.argv and self.headers['X-Forwarded-Proto'] != 'https':
			self.send_response(301, 'Must use SSL')
			self.send_header('Location', 'https://icse.herokuapp.com' + self.path)
			self.end_headers()
			return 
		
		if self.path == '/':
			path = os.path.join('web', 'query.html')
		else:
			if self.path.startswith('/'):
				path = os.path.join('web', self.path[1:])
			else:
				path = os.path.join('web', self.path)
		
		if not os.path.isfile(path):
			self.send_response(404)
			self.send_header('Content-Type', 'text/html')
			with open('web/404-generic.html') as fin:
				resp = fin.read()
			self.write(resp)
			return

		if path in hash_lookup:
			h = hash_lookup[path]
		else:
			with open(path) as fin:
				resp = fin.read()
			h = sha_hash(resp)
			hash_lookup[path] = h

		if 'If-None-Match' in self.headers:
			if h == self.headers['If-None-Match']:
				self.send_response(304, "Unchanged")
				self.send_header("Cache-Control", "no-cache, max-age=604800")
				self.send_header("ETag", h)
				self.end_headers()
				return

		self.send_response(200, 'OK')
		self.send_header("Cache-Control", "no-cache, max-age=604800")
		self.send_header("Content-type", mime(path))
		self.send_header("ETag", h)
		self.write(resp)

	def do_POST(self):
		if '--force-ssl' in sys.argv and self.headers['X-Forwarded-Proto'] != 'https':
			self.send_response(301, 'Must use SSL')
			self.send_response('Content')
			self.send_header('Location', 'https://icse.herokuapp.com')
			self.end_headers()
			return

		content = self.rfile.read(int(self.headers['Content-Length']))
		content = urlparse.parse_qs(content)
		
		if not ('pass' in content) and (('school' in content) ^ ('name' in content)):
			
			# since a browser wont generate a malformed POST,
			# this must be someone using cURL or something similar
			# dont serve error page

			self.send_response(400, "Bad POST request.")
			self.end_headers()
			return

		if content['pass'][0] not in self.password:
			self.send_response(403, 'Forbidden')
			self.send_header('Content-Type', "text/html")
			with open('web/403.html') as fin:
				resp = fin.read()
			self.write(resp)
			return
			
		if 'name' in content:
			resp = self.db.icse.processed.find({"name":content['name'][0].upper()})
		elif 'school' in content:
			resp = self.db.icse.processed.find({"school":content['school'][0].upper()}).sort("name")
		else:
			logging.critical('Malformed POST.')
	
		if resp.count() == 0:
			self.send_response(404)
			if 'name' in content:
				with open('web/404-name.html') as fin:
					resp = fin.read()
			else:
				with open('web/404-school.html') as fin:
					resp = fin.read()
			self.send_header('Content-type', 'text/html')
			self.write(resp)
			return

		resp = populate(resp, school=('name' in content))
		self.send_response(200, 'OK')
		self.send_header('Content-type','text/html')
		self.send_header('Cache-Control', 'no-store')
		self.write(resp)

Handler.password = [os.environ['PASSWORD']]
Handler.has_gzip = has_gzip
Handler.write = smart_reply

Handler.db = pymongo.MongoClient('mongodb://xrisk:{}@ds049631.mongolab.com:49631/icse'.format(os.environ['MONGO']))
if 'PORT' in os.environ:
	PORT = int(os.environ['PORT'])
else:
	PORT = random.choice(range(5000, 10000))

httpd = BaseHTTPServer.HTTPServer(('', PORT), Handler)

print "serving at port", PORT

httpd.serve_forever()

