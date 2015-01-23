import WebDB                            # provided as starting code base
import nltk                             # need to install using pip
from PorterStemmer import PorterStemmer

import os, sys, cookielib, urllib2,re   # standard libraries
from HTMLParser import HTMLParser


VERBOSITY = 2

# code to strip HTML tags from HTML fil
# found at http://stackoverflow.com/questions/753052/strip-html-from-strings-in-python
class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)
        

class Spider:
	"""
	Store the cache directory, a cookiejar, and a reference to a MusicDB
	object for caching and retrieving web pages.
	"""

	def __init__(self, cachedir, db, cookiejar=None):
		"""
		Initialize the Spider.
		
		The cachedir is the directory where cached pages will be stored.
		  The code will create three sub directories (header/, raw/, clean/)
		The db is an instance of the MusicDB class.
		The cookie jar is the name of the file that will store cookies. 
		If cookiejar is None, the local file 'cookies.lwp' will be used. 
		"""
		
	
		print "Initializing spider."
		self.p = PorterStemmer()		
		
		# Store info.
		self.cachedir = cachedir
		if cookiejar == None:
		    self.cookiefile = cachedir+'cookies.lwp' # the name of the cookie file
		self.db = db
		
		# Create directory structure
		if not os.path.exists(cachedir):
		  os.mkdir(cachedir)
		if not os.path.exists(cachedir+'raw'):
		  os.mkdir(cachedir+'raw')
		if not os.path.exists(cachedir+'clean'):
		  os.mkdir(cachedir+'clean')
		if not os.path.exists(cachedir+'header'):
		  os.mkdir(cachedir+'header')
		
		# Open cookie jar.
		self.cookiejar = cookielib.LWPCookieJar() # create an empty cookie jar 
		if os.path.isfile(self.cookiefile): # if the cookie jar file exists   
		    #sys.stderr.write("Can't find cookie file: %s. Will be created.\n" % self.cookiefile)
		    self.cookiejar.load(self.cookiefile) # load cookies into cookiejar

		# Tell urllib2 to use cookiejar when fetching web pages.
		opener = urllib2.build_opener( \
			urllib2.HTTPCookieProcessor(self.cookiejar))
		urllib2.install_opener(opener)
		self.cookiejar.save(self.cookiefile) # save cookies into cookie file 

	def _get_docType(self, header):
		"""
		Return the document type given a header, or None if it can't be
		determined.
		"""
		content_type_matches = re.findall(r'Content-Type: (.+);', header)
		n_matches = len(content_type_matches)
		if n_matches == 1:
			content_type = content_type_matches[0]
		else:
			content_type = None # Don't know
		return content_type
			
	def _get_title(self, page):
	  """
	  Return the value between the <title></title> tags of the html page
	  """
	  title_matches = re.findall(r'<title>(.+)</title>', page)
	  n_matches = len(title_matches)
	  if n_matches == 1:
	    title = title_matches[0]
	  else:
	    title = None # Don't know
	  return title
			
	def fetch(self, url, usecache=True, offline=False): 
		""" 
		Return the database url id, the page header, and the web page 
		specified by the url. 
		If usecache is True, the cachedir is consulted to see if it 
		already contains the information. If the page is stored in the 
		cache, it is returned. If the page is not stored in the cache, 
		the web page is downloaded and both the header and the web page are 
		stored in the cache. 
		If usecache is False, the cache is not consulted or written to. 
		If offline is True, results will only be returned if the page has 
		previously been cached. If offline is True and usecache is False, 
		no results will be returned, i.e., header and page will be None.
		""" 
		
		# Initialize return values.
		urlid = None
		header = None
		page = None		

		# Try the cache first.
		if usecache or offline:
			urlid = self.cacheID(url)
			if urlid is not None:
				page_file = open("%sraw/%06d.html" % (self.cachedir, urlid), "r")
				page = page_file.read()
				page_file.close()
				header_file = open("%sheader/%06d.txt" % \
								   (self.cachedir, urlid), "r")
				header = header_file.read()
				header_file.close()
				
				if VERBOSITY > 1:
					print "\tUsing cached version of the page."
				return (urlid, header, page)

		# If that didn't work, download from the web.
		if not offline:
			# Include User-agent information in your request for the url:
			request = urllib2.Request(url, None, headers={'User-agent':'Firefox/3.05'})
			try:
				response = urllib2.urlopen(request) # get the server's response
				page = response.read() # get the page (a string)
				
				if VERBOSITY > 1:
					print "\tDownloaded page. Its first characters are %s." % \
					      page[:30]
					
				header = str(response.info()) # get the header (a string)
				
				# The below line is commented out because it causes problems
				# with dogpile.com.
				#self.cookiejar.save(self.cookiefile) # save cookies			
				
				# Add url to db.
				urlid = self.db.insertCachedURL( \
					url, docType=self._get_docType(header), title=self._get_title(page))
				
				# Save html file.
				page_name = "%sraw/%06d.html" % (self.cachedir, urlid)
				page_file = open(page_name, "w")
				page_file.write(page)
				page_file.close()
				header_name = "%sheader/%06d.txt" % (self.cachedir, urlid)
				header_file = open(header_name, "w")
				header_file.write(header)
				header_file.close()
								
				if VERBOSITY > 1:
					print "\tSaved page as %s and header as %s." % (page_name,
																	header_name)
			except urllib2.URLError, e: # socket timeout or web-server error
				print 'Error: %s' % (e)
				
		return (urlid, header, page)
	
		
	def parse(self, page):
	  """
	   strips HTML tags and tokenizes webpage
	   
	   returns a list of words
	   page is a raw html web page
	  """
	  
	  # 
	  s = MLStripper()
	  s.feed(page)
	  text = s.get_data()
	  badChar = ['!','?',',','.','"', '*','(',')','"','[',']','/','\\',';',':','{','}',\
	             '<','>','|','$','='];
	  for bChar in badChar: 
	    text = text.replace(bChar," ")
        
	  wordList = nltk.word_tokenize(text)
	  return wordList
    	   
	def stemList(self, words):
	  pass
	  
	def lower(self, words):
	  lowerList = list()
	  for word in words:
	    lowerList.append(word.lower())
	  return lowerList
	  
	def stem(self, words):
	  stemList = list()
	  for word in words:
	    stemList.append(self.p.stem(word, 0, len(word)-1))
	  return stemList

	
	def cacheID(self, url): 
		""" 
		Returns the integer ID of URL in the cache, or None if the page is 
		not in the cache. 
		"""
		return self.db.lookupCachedURL_byURL(url)
	
	def getDB(self):
		""" 
		Returns the database.
		"""
		return self.db

# end Spider class



def main(url):
	# Initialize values.
	BASEDIR = "/Users/dturnbull/Work/Teaching/IthacaCollege/CS490_InfoRet/lab/01_Tokenizer/data/"
	db = WebDB.WebDB("%slab1.db" % BASEDIR)

	spider = Spider(BASEDIR, db)
	
	#url = 'http://www.wired.com/wired/archive/12.10/tail_pr.html'
	
	#TODO: URL below has a problem with HTML PARSER
	#url = 'http://www.amazon.com/Tale-Two-Cities-Signet-Classics/dp/0451526562'
	
	(urlID, header, page) = spider.fetch(url)
	
	title = spider._get_title(page)
	print "Page Title:",title
	tokens = spider.parse(page)	
	for token in tokens:
	  print token
	
	print "Number of Tokens:", len(tokens)
	print "Number of Terms:", len(set(tokens))
	lowerTokens = spider.lower(tokens)
	print "Number of Terms after lowercase:", len(set(lowerTokens))
	porterTokens = spider.stem(tokens)
	print "Number of Terms after Porter Stemmer:", len(set(porterTokens))
	
	
	
	#dbInfo = db.lookupCachedURL_byID(urlID)
	#print "DB Info:",dbInfo
	
	
if __name__ == '__main__':

  #url = 'http://www.wired.com/wired/archive/12.10/tail_pr.html'
  url = 'http://jimi.ithaca.edu/index.html'
  print sys.argv[1]
  if len(sys.argv) > 1:
	url = sys.argv[1]
	
  main(url)
