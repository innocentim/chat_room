#!/usr/bin/env python3

import pymysql
import re
import json
en=json.JSONEncoder(ensure_ascii=False, separators=(',', ':'))

from protocol import *
from misc import *

class Scene:
	def __init__(self, name, nb):
		self.name = name
		self.channel = {}
		self.nb = set(nb)

class User:
	def __init__(self, sock, addr):
		self.request=sock
		self.request.setblocking(False)
		self.addr=addr
		self.state = LOGIN_NEEDED
		self.position = None

	def register(self, username, password, nickname):
		db_cur.execute("select * from user where username=%s or nickname=%s", (username, nickname))
		if db_cur.fetchone():
			self.request.send(bytes((REGISTER, FAILED)))
			return False
		else:
			db_cur.execute("insert into user(username, passwd, nickname) values(%s, %s, %s)", (username, crypto(password), nickname))
			db_conn.commit()
			self.request.send(bytes((REGISTER, SUCC)))
			return True

	def login(self, username, password):
		db_cur.execute("select * from user where username=%s and passwd=%s", (username, crypto(password)))
		res = db_cur.fetchone()
		if res:
			self.nickname=res[3]
			self.uid=res[0]
			self.state = LOGINED
			tragedy=channel_world.get(self.nickname);
			if tragedy:
				tragedy.logout();
			self.request.send(bytes((LOGIN, SUCC)))
			channel_world[self.nickname]=self
			self.goto(scenes['default'])
			return True
		else:
			self.request.send(bytes((LOGIN, FAILED)))
			return False

	def logout(self):
		self.state = LOGIN_NEEDED
		channel_world.pop(self.nickname)
		self.goto(None)
		try:
			self.request.send(bytes((LOGOUT, SUCC)))
		except Exception:
			pass
		self.printLog("LOGOUT")
	
	def broadCast(self, msg):
		for k in self.position.channel.values(): 
			k.request.send(bytes((BROADCAST, PUSH)) + '{0}:{1}'.format(self.nickname, msg).encode())

	def tell(self, toname, msg):
		if toname in self.position.channel.keys():
			self.position.channel[toname].request.send(bytes((TELL, PUSH)) + '{0}:{1}'.format(self.nickname, msg).encode())
			self.request.send(bytes((TELL, SUCC)))
			return True
		else:
			self.request.send(bytes((TELL, FAILED)))
			return False

	def disconnect(self):
		if self.state == LOGINED:
			self.logout()
		ep.unregister(self.request.fileno())
		clients.pop(self.request.fileno())
		self.printLog("disconnected")

	def subscribe(self, channel):
		for k in channel.values():
			k.request.send(bytes((JOINED, PUSH)) + en.encode([self.nickname]).encode())
		channel[self.nickname]=self
		self.request.send(bytes((JOINED, PUSH)) + en.encode(tuple(channel.keys())).encode())

	def unSubscribe(self, channel):
		self.request.send(bytes((LEAVED, PUSH)) + en.encode(tuple(channel.keys())).encode())
		res=channel.pop(self.nickname, None)
		if res:
			for k in channel.values():
				k.request.send(bytes((LEAVED, PUSH)) + en.encode([self.nickname]).encode())

	def goto(self, scene):
		if self.position:
			self.unSubscribe(self.position.channel)
		self.position=scene;
		if scene:
			self.subscribe(self.position.channel)

	def printLog(self, data):
		printLog("{0}: {1}".format(self.addr, data))

	def handle(self):
		data = self.request.recv(4096)
		if not data:
			self.disconnect()
			return

		operation, state = data[0], data[1]
		data = data[2:].decode()

		if self.state == LOGIN_NEEDED:
			if operation == LOGIN and state == REQUEST:
				p = re.compile(r"^(\w+@\w+(?:\.\w+)+):(\w{5,32})$")
				m = p.match(data)
				if m:
					selfname, password = m.groups()
					if self.login(selfname, password):
						self.printLog("LOGIN SUCC")
					else:
						self.printLog("LOGIN FAILED: wrong selfname or password")
				else:
					self.request.send(bytes((LOGIN, FAILED)))
					self.printLog("LOGIN FAILED: wrong input format")
			elif operation == REGISTER and state == REQUEST:
				p = re.compile(r"^(\w+@\w+(?:\.\w+)+):(\w{5,32}):(\w{5,32})$")
				m = p.match(data)
				if m:
					selfname, password, nickname = m.groups()
					if self.register(selfname, password, nickname):
						self.printLog("REGISTER SUCC")
					else:
						self.printLog("REGISTER FAILED: selfname or nickname exists")
				else:
					self.request.send(bytes((REGISTER, FAILED)))
					self.printLog("REGISTER FAILED: wrong input format")
		elif self.state == LOGINED:
			if operation == BROADCAST and state == REQUEST:
				self.broadCast(data)
				self.printLog("BROADCAST")
			elif operation == TELL and state == REQUEST:
				p = re.compile(r"^(\w{5,32}):(.*)$")
				m = p.match(data)
				if m:
					toname, msg = m.groups()
					if self.tell(toname, msg):
						self.printLog("TELL SUCC")
					else:
						self.printLog("TELL FAILED: no such nickname")
				else:
					self.request.send(bytes((TELL, FAILED)))
					self.printLog("TELL FAILED: wrong input format")
			elif operation == GOTO and state == REQUEST:
				if data in scenes.keys() and data in self.position.nb: 
					self.request.send(bytes((GOTO, SUCC)))
					self.goto(scenes[data])
					self.printLog("GOTO SUCC")
				else:
					self.request.send(bytes((GOTO, FAILED)))
					self.printLog("GOTO FAILED")
			elif operation == LOGOUT and state == REQUEST:
				self.logout()

import sys
HOST, PORT = "0.0.0.0", 9998
DB_HOST = "127.0.0.1"
DB_SOCK = "/var/run/mysqld/mysqld.sock"
DB_USER = "test"
DB_PASSWD = ""
DB_DBNAME = "chat"
clients = {}
channel_world = {}
scenes = {'default': Scene('default', ('test1', 'test2')), 'test1': Scene('test1', ('default',)), 'test2': Scene('test2', ('default',))}

if __name__ == "__main__":
	import getopt
	import os
	try:
		optarg, args = getopt.gnu_getopt(sys.argv[1:], "p:o:")
		optarg = dict(optarg)
		if "-p" in optarg.keys():
			v = optarg["-p"]
			if v.isdigit():
				PORT = int(v)
			else:
				raise Exception("invalid port")
		if "-o" in optarg.keys():
			v = optarg["-o"]
			if os.path.isfile(v):
				logfile = open(v, 'a')
	except Exception as e:
		printLog("Parse error: " + e.args[0])
		exit(1)

	try:
		db_conn = pymysql.connect(host=DB_HOST, unix_socket=DB_SOCK, user=DB_USER, passwd=DB_PASSWD, db=DB_DBNAME)
		db_cur = db_conn.cursor()
		db_cur.execute("select * from user")
	except pymysql.err.ProgrammingError as e:
		p = re.compile(r".*Table '.+' doesn't exist.*")
		if p.match(str(e.args[0])):
			db_cur.execute("create table user(id int not null auto_increment primary key, username text, passwd text, nickname text)")
			printLog("New table created")
		else:
			printLog("Database error: " + str(e.args[0]))
			exit(1)

	import socket
	import select

	listenfd=socket.socket()
	listenfd.bind((HOST, PORT))
	listenfd.listen(32)

	ep=select.epoll()
	ep.register(listenfd, select.EPOLLIN)

	while True:
		events=ep.poll()
		for fd, event in events:
			if fd==listenfd.fileno():
				client, addr=listenfd.accept()
				if client.fileno() in clients.keys():
					clients[client.fileno()].disconnect()
				clients[client.fileno()]=User(client, addr)
				ep.register(client.fileno(), select.EPOLLIN | select.EPOLLET)
				clients[client.fileno()].printLog('connected')
			else:
				clients[fd].handle()
