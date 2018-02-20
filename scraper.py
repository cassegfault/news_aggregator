import urllib2, json, time, sys, datetime
import mysql.connector
import xml.etree.ElementTree as ET

#setup urllib to open with browser headers
opener = urllib2.build_opener()
opener.addheaders = [('User-Agent', 'Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11')]

# pull sources from the db once every 30 min
UPDATE_SOURCES_INTERVAL = 30 * 60

# update posts for a source every 5 minutes
UPDATE_POSTS_INTERVAL = 5 * 60

# run tick twice a minute
TICK_INTERVAL = 30

sources_list = []
last_tick = 0
cnx = None

config = {}
with open('config.json','r') as config_file:
	config = json.loads(config_file.read())

DB_HOST=config['database']['host']
DB_USER=config['database']['user']
DB_DB=config['database']['database']

def get_cursor():
	global cnx
	cnx = mysql.connector.connect(host=DB_HOST, user=DB_USER, db=DB_DB)
	sql=cnx.cursor()
	return cnx.cursor()

def build_sources_list():
	global sources_list
	sources_list = []
	cnx = mysql.connector.connect(host=DB_HOST, user=DB_USER, db=DB_DB)
	sql=cnx.cursor()
	sql.execute(""" SELECT sources.id, link, type, (SELECT UNIX_TIMESTAMP(date_created) FROM posts 
														WHERE posts.source_id=sources.id ORDER BY date_created DESC LIMIT 1) 
														AS last_updated FROM sources """)
	for row in sql.fetchall():
		source = {}
		source['id']            = row[0]
		source['link']          = row[1]
		source['type']          = row[2]
		source['last_updated']  = row[3] or 0
		sources_list.append(source)


post_query  = "INSERT IGNORE INTO posts (body, media, description, url, title, date_created, source_id) VALUES (%s, %s, %s, %s, %s, %s, %s)"

def mysql_ts(in_ts):
	return datetime.datetime.fromtimestamp(in_ts).strftime('%Y-%m-%d %H:%M:%S')

def parse_reddit_source(data, source):
	response_list = []
	jd = json.loads(data)
	for cdoc in jd['data']['children']:
		c = cdoc['data']
		body = c['selftext'] or c['url']
		perma = 'http://reddit.com' + c['permalink']
		media = None
		
		if body[0:4] == 'http' and ('imgur' in body or body[-4:] in ['.jpg','jpeg','.gif','.png', 'gifv']):
			if body[-4:] == 'gifv':
				body = body[:-1]
			try:
				imgres = opener.open(body)
				extension = body[body.rfind('.'):]
				if body.rfind('.') < (len(body) - 4):
					extension = '.jpg'
				res_info = imgres.info()
				if 'image/' in res_info.type:
					media = 'images/img_' + str(time.time()) + extension
					with open(media, 'w+') as img_file:
						img_file.write(imgres.read())
			except:
				print "error writing image", body
		

		response_list.append( (body, media, None, perma, c['title'].encode('utf-8').strip(), mysql_ts(int(c['created'])), source['id']) )
	return response_list

def parse_hn_timestamp(ts):
	return time.mktime(datetime.datetime.strptime(ts, '%a, %d %b %Y %H:%M:%S +0000').timetuple())

def parse_nyt_timestamp(ts):
	return time.mktime(datetime.datetime.strptime(ts, '%a, %d %b %Y %H:%M:%S GMT').timetuple())

def parse_hacker_news(data, source):
	tree = ET.fromstring(data)
	result_list = []
	for child in tree[0]:
		if child.tag == 'item':
			item = {}
			for c in child:
				item[c.tag] = c.text
			result_list.append( [item['link'], None, None, item['comments'], item['title'], mysql_ts(parse_hn_timestamp(item['pubDate'])), source['id']] )
	return result_list

def parse_ny_times(data, source):
	result_list = []
	tree = ET.fromstring(data)
	for child in tree[0]:
		if child.tag == 'item':
			item = {}
			for c in child:
				if c.tag in ['pubDate', 'title', 'link', 'description']:
					item[c.tag] = c.text
				result_list.append( [item['link'], None, item['description'], item['link'], item['title'],  mysql_ts(parse_nyt_timestamp(item['pubDate'])), source['id']] )
	return result_list

def tick():
	global last_tick, sources_list, post_query
	cnx = mysql.connector.connect(host=DB_HOST, user=DB_USER, db=DB_DB)
	sql=cnx.cursor()
	sql.execute('SET NAMES utf8')
	sql.execute('SET CHARACTER SET utf8')

	if last_tick == 0 or (time.time() - last_tick) >= UPDATE_SOURCES_INTERVAL:
		build_sources_list()

	last_tick = time.time()

	param_sets = []
	for source in sources_list:
		if (time.time() - source['last_updated']) >= UPDATE_POSTS_INTERVAL:
			try:
				res = opener.open(source['link'])
			except:
				continue
			data = res.read()
			result_list = []

			# switch based on source type
			if source['type'] == 'reddit':
				result_list = parse_reddit_source(data, source)
			elif source['type'] == 'hacker_news':
				result_list = parse_hacker_news(data, source)
			elif source['type'] == 'new_york_times':
				result_list = parse_ny_times(data, source)

			for params in result_list:
				sql.execute(post_query, params)
			cnx.commit()
			
			source['last_updated'] = time.time()
		else:
			print source['id'], 'already updated'

	
	time.sleep(TICK_INTERVAL)
	tick()


tick()
