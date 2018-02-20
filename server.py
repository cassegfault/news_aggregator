from flask import Flask, request, redirect, url_for, session
import sys, json, base64, time
import mysql.connector

config = {}
with open('config.json','r') as config_file:
	config = json.loads(config_file.read())

c = None
cnx = None
last_db_conn = 0

def reconnect():
	global cnx, c, last_db_conn
	cnx = mysql.connector.connect(host=config['database']['host'], user=config['database']['user'], db=config['database']['database'])
	c = cnx.cursor()
	last_db_conn = time.time()

reconnect()

# Easy function to maintain connection to db
def db_route(func):
	@wraps(func)
	def func_wrapper():
		global c, cnx, last_db_conn
		now = time.time()
		if now - last_db_conn > 3600:
			reconnect()
	return func

# All routes prefixed /api

def get_param(name):
	res = request.args.get(name, None)
	if res is None:
		res = request.form.get(name, None)
	return res

@app.route('/rate', methods=['POST'])
@db_route
def rate_route():
	global c, cnx
	link_id = get_param('post_id',None)
	score_modifier = get_param('score', None)

	c.execute("INSERT INTO posts_scores (post_id, score) VALUES (%s, %s)", [link_id, score_modifier])
	cnx.commit()

@app.route('/list', methods=['GET'])
@db_route
def rate_route():
	global c, cnx
	c.execute("SELECT id, title, body, url, date_created FROM posts")
	posts = []
	for row in c.fetchall():
		posts.append({
			'id': row[0],
			'title': row[1],
			'body': row[2],
			'url': row[3],
			'date_created': row[4]
			})
	return Response(response=json.dumps(post), status=200, mimetype='application/json')

if __name__ == "__main__":
	app.run(port=config['port'])