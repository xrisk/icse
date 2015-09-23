import BaseHTTPServer
import os
import random
import urlparse
import pymongo
import sys
import logging
import tempfile
import sha
import gzip
from bs4 import BeautifulSoup as bs

def gzip_content(content):
	h = sha.new(content).hexdigest()
	if os.path.isfile(h):
		with open(h,'rb') as fin:
			return fin.read()
	with gzip.open(h, 'wb') as fout:
		fout.write(content)
	fout.close()
	with open(h, 'rb') as fin:
		return fin.read()


abbrev = {
	"COMPUTER APPLICATIONS" : "CS",
	"HISTORY CIVICS & GEOGRAPHY" : "HCG",
	"MATHEMATICS" : "MATH",
	"BIOLOGY" : "BIO"
}

mimetable = {'.html':'text/html', '.css':'text/css'}

def populate(json):
	soup = bs(open('web/results.html').read())
	headers = soup.find(id="headers")
	data = soup.find(id="data")
	for i in ['Name', 'UID', 'School', 'Score']:
		h  = soup.new_tag("th")
		h.string = i
		headers.append(h)

	for i in ['name', '_id', 'school', 'best5']:
		f = soup.new_tag("td")
		f.string = json[i]
		data.append(f)


	for j in json['marks']:
		h = soup.new_tag("th")
		
		if j in abbrev:
			h.string = abbrev[j]
		else:
			h.string = j

		headers.append(h)
		h = soup.new_tag("td")
		h.string = json['marks'][j]
		data.append(h)


	return soup.prettify()

def populate_school(json):
	subject_counts = {}
	l = []
	for i in json:
		l.append(i)
		for j in i['marks']:
			if j in subject_counts:
				subject_counts[j] += 1
			else:
				subject_counts[j] = 1
	soup = bs(open('web/results.html').read())
	headers = soup.find(id="headers")
	data = soup.find(id="data")
	for i in ['Name', 'UID', 'Score']:
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

	for i in l:
		row = soup.new_tag("tr")
		for j in ['name', '_id', 'best5']:
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
	
	return soup.prettify()
	




class Handler(BaseHTTPServer.BaseHTTPRequestHandler):
	def do_GET(self):
		if '--force-ssl' in sys.argv and self.headers['X-Forwarded-Proto'] != 'https':
			self.send_response(301, 'Must use SSL')
			self.send_header('Location', 'https://icse.herokuapp.com' + self.path)
			self.end_headers()
		else:
			path = self.path
			if path == '/':
				path = '/query.html'
			path = 'web' + path
			try:
				resp = open(path).read()
				self.send_response(200, 'OK')
				if 'Accept-Encoding' in self.headers and 'gzip' in self.headers['Accept-Encoding']:
						self.send_header('Content-Encoding', 'gzip')
						self.end_headers()
						self.wfile.write(gzip_content(resp))
				else:
					self.end_headers()
					self.wfile.write(resp)
			except IOError:
			  self.send_response(404, 'Not Found')
			  self.end_headers()

	def do_POST(self):
		if '--force-ssl' in sys.argv and self.headers['X-Forwarded-Proto'] != 'https':
			self.send_response(301, 'Must use SSL')
			self.send_response('Content')
			self.send_header('Location', 'https://icse.herokuapp.com')
			self.end_headers()
		else:
			content = self.rfile.read(int(self.headers['Content-Length']))
			content = urlparse.parse_qs(content)
			if 'pass' in content and content['pass'][0] == os.environ['PASSWORD']:
				if 'name' in content:
					self.send_response(200, 'OK')
					self.send_header('Content-type', 'text/html')
					resp = self.db.icse.processed.find_one({"name":content['name'][0].upper()})
					if resp is None:
						self.end_headers()
						self.wfile.write(open('web/404.html').read())
					else:
						if 'Accept-Encoding' in self.headers and 'gzip' in self.headers['Accept-Encoding']:
							self.send_header('Content-Encoding', 'gzip')
							self.end_headers()
							self.wfile.write(gzip_content(populate(resp).encode('utf-8')))
						else:
							self.wfile.write(populate(resp).encode('utf-8'))
					
				if 'school' in content:
					self.send_response(200, 'OK')
					self.send_header('Content-type', 'text/html')
					resp = self.db.icse.processed.find({"school":content['school'][0].upper()}).sort("name")
					if resp.count() == 0:
						self.end_headers()
						self.wfile.write(open('web/404-school.html').read())
					else:
						if 'Accept-Encoding' in self.headers and 'gzip' in self.headers['Accept-Encoding']:
							self.send_header('Content-Encoding', 'gzip')
							self.end_headers()
							self.wfile.write(gzip_content(populate_school(resp).encode('utf-8')))
						else:
							self.wfile.write(populate_school(resp).encode('utf-8'))
			else:
				self.send_response(403, 'Not authorised')
				self.send_header('Content-type', 'text/html')
				self.end_headers()
				self.wfile.write(open('web/403.html').read())




	
Handler.password = os.environ['PASSWORD']

Handler.db = pymongo.MongoClient('mongodb://xrisk:{}@ds049631.mongolab.com:49631/icse'.format(os.environ['MONGO']))
if 'PORT' in os.environ:
	PORT = int(os.environ['PORT'])
else:
	PORT = random.choice(range(5000, 10000))

httpd = BaseHTTPServer.HTTPServer(('', PORT), Handler)

print "serving at port", PORT

httpd.serve_forever()

