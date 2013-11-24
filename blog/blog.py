# coding: utf-8
#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#	 http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

#this demo is modified by EleChen @2013.11.17
#contact me by elechen@outlook.com
#changed the database from MySQL to MongoDB
#and there is no need to create database first
#Don't worry, MongoDB just worked

import os.path
import re

import markdown
import pymongo

import tornado.auth
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import unicodedata

from bson import ObjectId
import datetime

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)
define("mongodb_host", default="127.0.0.1:27017", help="blog database host")
define("mongodb_database", default="blog_db", help="blog database name")
define("mongodb_blogs", default="blogs", help="blogs collection name")
define("mongodb_authors", default="authors", help="authors collection name")
define("mongodb_user", default="blog", help="blog database user")
define("mongodb_password", default="blog", help="blog database password")

class Application(tornado.web.Application):
	def __init__(self):
		handlers = [
			(r"/", HomeHandler),
			(r"/archive", ArchiveHandler),
			(r"/feed", FeedHandler),
			(r"/entry/([^/]+)", EntryHandler),
			(r"/compose", ComposeHandler),
			(r"/del", DeleteHandler),
			(r"/auth/login", AuthLoginHandler),
			(r"/auth/logout", AuthLogoutHandler),
		]
		settings = dict(
			blog_title=u"EleChen's Blog",
			template_path=os.path.join(os.path.dirname(__file__), "templates"),
			static_path=os.path.join(os.path.dirname(__file__), "static"),
			ui_modules={"Entry": EntryModule},
			xsrf_cookies=True,
			cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
			login_url="/auth/login",
			debug=True,
		)
		tornado.web.Application.__init__(self, handlers, **settings)

		# Have one global connection to the blog DB across all handlers
		self.db = pymongo.Connection()[options.mongodb_database]


class BaseHandler(tornado.web.RequestHandler):
	@property
	def db(self):
		return self.application.db

	def get_current_user(self):
		user_id = self.get_secure_cookie("blogdemo_user")
		if not user_id: return None
		return self.db[options.mongodb_authors].find_one({"_id": ObjectId(user_id)})
# 		return self.db.get("SELECT * FROM authors WHERE id = %s", int(user_id))


class HomeHandler(BaseHandler):
	def get(self):
		result = self.db[options.mongodb_blogs].find().limit(5).sort("updated", pymongo.DESCENDING)
		entries = []
		for entery in result: #因为mongodb的find函数返回的游标，直到使用到结果的时候才会返回真正的结果——所以和MySQL有点区别
			entries.append(entery)
# 		entries = self.db.query("SELECT * FROM entries ORDER BY published "
# 								"DESC LIMIT 5")
		if not entries:
			self.redirect("/compose")
			return
		self.render("home.html", entries=entries)


class EntryHandler(BaseHandler):
	def get(self, slug):
		entry = self.db[options.mongodb_blogs].find_one({"slug": slug})
# 		entry = self.db.get("SELECT * FROM entries WHERE slug = %s", slug)
		if not entry: raise tornado.web.HTTPError(404)
		self.render("entry.html", entry=entry)

class ArchiveHandler(BaseHandler):
	def get(self):
		result = self.db[options.mongodb_blogs].find()
		entries = []
		for entery in result:
			entries.append(entery)
# 		entries = self.db.query("SELECT * FROM entries ORDER BY published "
# 								"DESC")
		self.render("archive.html", entries=entries)

class FeedHandler(BaseHandler):
	def get(self):
		result = self.db[options.mongodb_blogs].find()
		entries = []
		for entery in result:
			entries.append(entery)
# 		entries = self.db.query("SELECT * FROM entries ORDER BY published "
# 								"DESC LIMIT 10")
			
		self.set_header("Content-Type", "application/atom+xml")
		self.render("feed.xml", entries=entries)

class DeleteHandler(BaseHandler):
	def get(self):
		idx = self.get_argument("_id", None)
		if idx:
			self.db[options.mongodb_blogs].remove({"_id": ObjectId(idx)})
			self.redirect("/")
		
class ComposeHandler(BaseHandler):
# 	@tornado.web.authenticated
	def get(self):
		idx = self.get_argument("_id", None)
		entry = None
		if idx:
			#entry = self.db.get("SELECT * FROM entries WHERE id = %s", int(idx))
			entry = self.db[options.mongodb_blogs].find_one({"_id": ObjectId(idx)})
		self.render("compose.html", entry=entry)

# 	@tornado.web.authenticated
	def post(self):
		idx = self.get_argument("_id", None)
		title = self.get_argument("title")
		text = self.get_argument("markdown")
		html = markdown.markdown(text)
		if idx:
# 			entry = self.db.get("SELECT * FROM entries WHERE id = %s", int(idx))
			entry = self.db[options.mongodb_blogs].find_one({"_id": ObjectId(idx)})
			if not entry: raise tornado.web.HTTPError(404)
			slug = entry["slug"]
			blog = {}
			blog["title"] = title
			blog["markdown"] = text
			blog["html"] = html
			blog["updated"] = datetime.datetime.now()
			
			self.db[options.mongodb_blogs].update({"_id": ObjectId(idx)}, {"$set": blog})
# 			self.db.execute(
# 				"UPDATE entries SET title = %s, markdown = %s, html = %s "
# 				"WHERE id = %s", title, text, html, int(idx))
		else:
			slug = unicodedata.normalize("NFKD", title).encode(
				"ascii", "ignore")
			slug = re.sub(r"[^\w]+", " ", slug)
			slug = "-".join(slug.lower().strip().split())
			if not slug: slug = "entry"
			while True:
# 				e = self.db.get("SELECT * FROM entries WHERE slug = %s", slug)
				e = self.db[options.mongodb_blogs].find_one({"slug": slug})
				if not e: break
				slug += "-2"
# 			self.db.execute(
# 				"INSERT INTO entries (author_id,title,slug,markdown,html,"
# 				"published) VALUES (%s,%s,%s,%s,%s,UTC_TIMESTAMP())",
# 				self.current_user.id, title, slug, text, html)
			blog = {}
			blog["author_id"] = self.current_user["_id"]
			blog["title"] = title
			blog["slug"] = slug
			blog["markdown"] = text
			blog["html"] = html
			blog["published"] = datetime.datetime.now()
			blog["updated"] = datetime.datetime.now()
			self.db[options.mongodb_blogs].insert(blog)
			
		self.redirect("/entry/" + slug)


testUser = {"name":"elechen", "email":"elechen@outlook.com"}
class AuthLoginHandler(BaseHandler, tornado.auth.GoogleMixin):
	@tornado.web.asynchronous
	def get(self):
# 		if self.get_argument("openid.mode", None):
# 			self.get_authenticated_user(self.async_callback(self._on_auth))
# 			return
# 		self.authenticate_redirect()
		self._on_auth(testUser)

	def _on_auth(self, user):
		if not user:
			raise tornado.web.HTTPError(500, "Google auth failed")
# 		author = self.db.get("SELECT * FROM authors WHERE email = %s",
# 							 user["email"])
		author = self.db[options.mongodb_authors].find_one({"email": user["email"]})
		if not author:
			# Auto-create first author
# 			any_author = self.db.get("SELECT * FROM authors LIMIT 1")
			any_author = self.db[options.mongodb_authors].find_one()
			if not any_author:
# 				author_id = self.db.execute(
# 					"INSERT INTO authors (email,name) VALUES (%s,%s)",
# 					user["email"], user["name"])
				newAuthor = {}
				newAuthor["email"] = user["email"]
				newAuthor["name"] = user["name"]
				self.db[options.mongodb_authors].insert(newAuthor)
				self.redirect("/auth/login")
				return
			else:
				self.redirect("/")
				return
		else:
			author_id = author["_id"]
		self.set_secure_cookie("blogdemo_user", str(author_id))
		self.redirect(self.get_argument("next", "/"))


class AuthLogoutHandler(BaseHandler):
	def get(self):
		self.clear_cookie("blogdemo_user")
		self.redirect(self.get_argument("next", "/"))


class EntryModule(tornado.web.UIModule):
	def render(self, entry):
		return self.render_string("modules/entry.html", entry=entry)

def main():
	print("srv is established ...")
	tornado.options.parse_command_line()
	http_server = tornado.httpserver.HTTPServer(Application())
	http_server.listen(options.port)
	tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
	main()
