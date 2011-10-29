#!/usr/bin/env python3

from protocol import *
import json
de=json.JSONDecoder()

def poll():
	global users
	while True:
		data=s.recv(4096)
		operation, state=data[0], data[1]
		data=data[2:].decode()
		if operation==BROADCAST and state==PUSH:
			print(data)
		elif operation==TELL:
			if state==PUSH:
				print(data)
			elif state==SUCC:
				global tell_cache
				print("tell {0}: {1}".format(tell_cache[0], tell_cache[1]))
			elif state==FAILED:
				print("TELL FAILED")
		elif operation==REGISTER:
			if state==SUCC:
				print("REGISTER SUCC")
			else:
				print("REGISTER FAILED")
		elif operation==LOGIN:
			if state==SUCC:
				print("LOGIN SUCC")
			else:
				print("LOGIN FAILED")
		elif operation==JOINED:
			users|=set(de.decode(data))
			print(data+' joined')
		elif operation==LEAVED:
			users-=set(de.decode(data))
			print(data+' leaved')
		elif operation==GOTO:
			if state==SUCC:
				global position
				position=goto_cache
		elif operation==LOGOUT:
			print('Oops...kicked...')
			users=set()

def register(username, password, nickname):
	s.send(bytes((REGISTER, REQUEST))+"{0}:{1}:{2}".format(username, password, nickname).encode())

def login(username, password):
	s.send(bytes((LOGIN, REQUEST))+"{0}:{1}".format(username, password).encode())

def logout():
	s.send(bytes((LOGOUT, REQUEST)))

def broadCast(msg):
	s.send(bytes((BROADCAST, REQUEST))+msg.encode())
	
def tell(target, msg):
	global tell_cache
	tell_cache=(target, msg)
	s.send(bytes((TELL, REQUEST))+"{0}:{1}".format(target, msg).encode())

def goto(scene):
	global goto_cache
	goto_cache=(scene)
	s.send(bytes((GOTO, REQUEST))+scene.encode())

def showUser():
	print(users)

import socket
import sys
HOST="127.0.0.1"
PORT=9998
if len(sys.argv)>=2:
	HOST=sys.argv[1]
	if len(sys.argv)>2 and sys.argv[2].isdigit():
		PORT=int(sys.argv[2])

s=socket.socket()
s.connect((HOST, PORT))

users=set()

import threading
threading.Thread(target=poll).start()

if __name__=='__main__':
	while True:
		try:
			arg=input().split()
			exec(arg[0]+str(tuple(arg[1:])))
		except Exception as e:
			print(e)


