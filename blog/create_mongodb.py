#coding: utf-8

import pymongo
import time

def InsertNewBlogs():
	coll = pymongo.Connection().blog_db.blogs
	blogs = []
	for x in range(20): #暂时保存20条数据
		blog = {}
		blog["id"] = x
		blog["author_id"] = 1000 + x
		blog["slug"] = "slug%d" % x 
		blog["title"] = "Title%d" % x
		blog["markdown"] = "markdown Source...Don't know what"
		blog["html"] = "html Source--也就是正文内容了"
		blog["published"] = time.time()
		blog["updated"] = time.time()
		
		blogs.append(blog)
	
	coll.insert(blogs)
	
# InsertNewBlogs()

def FindAllDocs():
	coll = pymongo.Connection().blog_db.blogs
	for x in coll.find({}, {"_id": 0}):
		print x

# FindAllDocs()

def InsertNewAuthors():
	coll = pymongo.Connection().blog_db.authors
	coll.remove()
	
	author = {}
	authors = []
	author["id"] = 1000
	author["name"] = "陈晓峰"
	author["mail"] = "elechen@outlook.com"
	authors.append(author)
	
	author = {}
	author["id"] = 1001
	author["name"] = "风晓尘"
	author["mail"] = "976372771@qq.com"
	authors.append(author)
	
	coll.insert(authors)
	
	for x in coll.find({}, {"_id": 0}):
		print x
	
InsertNewAuthors()



	
	