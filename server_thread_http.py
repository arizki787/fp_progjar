from socket import *
import socket
import threading
import time
import sys
import logging
from http import HttpServer

httpserver = HttpServer()


class ProcessTheClient(threading.Thread):
	def __init__(self, connection, address):
		self.connection = connection
		self.address = address
		threading.Thread.__init__(self)

	def run(self):
		rcv=""
		while True:
			try:
				data = self.connection.recv(32)
				if data:
					#merubah input dari socket (berupa bytes) ke dalam string
					#agar bisa mendeteksi \r\n
					d = data.decode()
					rcv=rcv+d
					if rcv[-2:]=='\r\n':
						#end of command, proses string
						method = None
						path = None
						
						# Log hanya informasi penting saja (method dan path)
						try:
							request_line = rcv.split('\r\n')[0]
							method, path, _ = request_line.split(' ')
							logging.info(f"{method} request to {path}")
						except:
							logging.info("Request received (format unknown)")
						
						hasil = httpserver.proses(rcv)
						#hasil akan berupa bytes
						#untuk bisa ditambahi dengan string, maka string harus di encode
						hasil=hasil+"\r\n\r\n".encode()
						
						# Log hanya kode status response
						try:
							status_line = hasil.decode().split('\r\n')[0]
							logging.info(f"Response: {status_line}")
						except:
							pass
						
						#hasil sudah dalam bentuk bytes
						self.connection.sendall(hasil)
						rcv=""
						self.connection.close()
				else:
					break
			except OSError as e:
				pass
		self.connection.close()



class Server(threading.Thread):
	def __init__(self):
		self.the_clients = []
		self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		threading.Thread.__init__(self)

	def run(self):
		self.my_socket.bind(('0.0.0.0', 8889))
		self.my_socket.listen(1)
		logging.warning("Server running on 0.0.0.0:8889")
		while True:
			self.connection, self.client_address = self.my_socket.accept()
			client_ip = self.client_address
			logging.info(f"New connection from {client_ip}")

			clt = ProcessTheClient(self.connection, self.client_address)
			clt.start()
			self.the_clients.append(clt)



def main():
	# Gunakan INFO level untuk log penting saja dan format yang lebih ringkas
	logging.basicConfig(
		level=logging.INFO, 
		format='[%(asctime)s] %(levelname)s: %(message)s',
		datefmt='%H:%M:%S'  # Format waktu singkat (jam:menit:detik)
	)
	
	# Tampilkan banner saat server start
	print("="*50)
	print("   Hangman Multiplayer Game Server")
	print("   HTTP server running on port 8889")
	print("="*50)
	print("\nServer log:")
	
	# Matikan log debug dari modul lain
	logging.getLogger('asyncio').setLevel(logging.WARNING)
	logging.getLogger('matplotlib').setLevel(logging.WARNING)
	
	svr = Server()
	svr.start()

if __name__=="__main__":
	main()

