import sys
import os.path
import uuid
import logging
from glob import glob
from datetime import datetime
import json
import random

class HttpServer:
	def __init__(self):
		self.sessions={}
		self.types={}
		self.types['.pdf']='application/pdf'
		self.types['.jpg']='image/jpeg'
		self.types['.txt']='text/plain'
		self.types['.html']='text/html'
		self.types['.json']='application/json'
		
		self.last_polling_log = {}  
		self.log_interval = 10 
		
		self.rooms = {}
		self.car_brands = [
			{'word': 'TOYOTA', 'clue': 'Merk mobil asal Jepang yang terkenal dengan Avanza dan Innova'},
			{'word': 'HONDA', 'clue': 'Merk mobil Jepang pembuat Civic dan CR-V'},
			{'word': 'FERRARI', 'clue': 'Merk mobil sport mewah asal Italia dengan logo kuda jingkrak'},
			{'word': 'BMW', 'clue': 'Merk mobil mewah Jerman yang dikenal sebagai "The Ultimate Driving Machine"'},
			{'word': 'MERCEDES', 'clue': 'Merk mobil mewah Jerman dengan logo bintang tiga'},
			{'word': 'LAMBORGHINI', 'clue': 'Merk supercar Italia dengan logo banteng'},
			{'word': 'PORSCHE', 'clue': 'Merk mobil sport Jerman pembuat 911'},
			{'word': 'AUDI', 'clue': 'Merk mobil Jerman dengan logo empat cincin'},
			{'word': 'NISSAN', 'clue': 'Merk mobil Jepang pembuat GT-R dan X-Trail'},
			{'word': 'HYUNDAI', 'clue': 'Merk mobil Korea Selatan yang populer di Indonesia'},
			{'word': 'MAZDA', 'clue': 'Merk mobil Jepang dengan teknologi SkyActiv'},
			{'word': 'VOLKSWAGEN', 'clue': 'Merk mobil Jerman yang berarti "mobil rakyat"'},
			{'word': 'FORD', 'clue': 'Merk mobil Amerika pembuat Mustang dan Ranger'},
			{'word': 'CHEVROLET', 'clue': 'Merk mobil Amerika dengan logo bowtie'},
			{'word': 'MITSUBISHI', 'clue': 'Merk mobil Jepang pembuat Pajero dan Outlander'}
		]
	def response(self,kode=404,message='Not Found',messagebody=bytes(),headers={}):
		tanggal = datetime.now().strftime('%c')
		resp=[]
		resp.append("HTTP/1.0 {} {}\r\n" . format(kode,message))
		resp.append("Date: {}\r\n" . format(tanggal))
		resp.append("Connection: close\r\n")
		resp.append("Server: myserver/1.0\r\n")
		resp.append("Content-Length: {}\r\n" . format(len(messagebody)))
		for kk in headers:
			resp.append("{}:{}\r\n" . format(kk,headers[kk]))
		resp.append("\r\n")

		response_headers=''
		for i in resp:
			response_headers="{}{}" . format(response_headers,i)
		
		# Log response (hanya kode status)
		# Cek apakah ini response untuk error (4xx atau 5xx)
		if kode >= 400:
			logging.warning(f"Error response: {kode} {message}")
		
		#menggabungkan resp menjadi satu string dan menggabungkan dengan messagebody yang berupa bytes
		#response harus berupa bytes
		#message body harus diubah dulu menjadi bytes
		if (type(messagebody) is not bytes):
			messagebody = messagebody.encode()

		response = response_headers.encode() + messagebody
		#response adalah bytes
		return response

	def should_log_request(self, method, path):
		# Jangan log terlalu sering untuk polling endpoints
		now = datetime.now().timestamp()
		
		# Polling endpoint patterns
		polling_patterns = ['/room/', '/rooms']
		
		# Cek apakah path termasuk polling
		is_polling = False
		for pattern in polling_patterns:
			if pattern in path:
				is_polling = True
				break
				
		if is_polling:
			# Hanya log polling request dengan interval tertentu
			last_log = self.last_polling_log.get(path, 0)
			if now - last_log < self.log_interval:
				return False
			
			# Update waktu log terakhir
			self.last_polling_log[path] = now
				
		return True
			
	def proses(self,data):
		
		requests = data.split("\r\n")
		baris = requests[0]
		all_headers = [n for n in requests[1:] if n!='']

		j = baris.split(" ")
		try:
			method=j[0].upper().strip()
			object_address = j[1].strip()
			
			# Log request jika perlu
			if self.should_log_request(method, object_address):
				if method == 'GET':
					logging.info(f"Processing {method} request to {object_address}")
				else:
					logging.info(f"Processing {method} request to {object_address}")
					
			# Proses request berdasarkan method
			if (method=='GET'):	
				return self.http_get(object_address, all_headers)
			if (method=='POST'):
				return self.http_post(object_address, all_headers)
			else:
				return self.response(400,'Bad Request','',{})
		except IndexError:
			return self.response(400,'Bad Request','',{})
	def http_get(self,object_address,headers):
		if object_address == '/':
			# Return main menu HTML
			html_content = self.get_main_menu_html()
			return self.response(200, 'OK', html_content, {'Content-Type': 'text/html'})
		
		elif object_address == '/rooms':
			# Return available rooms as JSON
			rooms_data = {
				'rooms': [
					{
						'id': room_id,
						'players': len(room['players']),
						'max_players': 2,
						'status': room['status']
					}
					for room_id, room in self.rooms.items()
				]
			}
			return self.response(200, 'OK', json.dumps(rooms_data), {'Content-Type': 'application/json'})
		
		elif object_address.startswith('/room/'):
			# Get room status
			room_id = object_address.split('/')[-1]
			if room_id in self.rooms:
				room_data = self.rooms[room_id]
				return self.response(200, 'OK', json.dumps(room_data), {'Content-Type': 'application/json'})
			else:
				return self.response(404, 'Not Found', json.dumps({'error': 'Room not found'}), {'Content-Type': 'application/json'})
		
		else:
			return self.response(404, 'Not Found', 'Page not found', {})

	def http_post(self,object_address,headers):
		# Extract POST data from headers (simplified parsing)
		post_data = {}
		for header in headers:
			if header.strip() == '':
				break
		
		# Parse JSON body if available
		content_length = 0
		for header in headers:
			if header.lower().startswith('content-length:'):
				content_length = int(header.split(':')[1].strip())
				break
		
		if object_address == '/create_room':
			# Create new room
			room_id = str(uuid.uuid4())[:8]
			player_id = str(uuid.uuid4())[:8]  # Generate player ID for creator
			car_data = random.choice(self.car_brands)
			word = car_data['word']
			clue = car_data['clue']
			self.rooms[room_id] = {
				'id': room_id,
				'word': word,
				'clue': clue,
				'guessed_word': ['_'] * len(word),
				'guessed_letters': [],
				'wrong_guesses': 0,
				'max_wrong_guesses': 6,
				'players': [{
					'id': player_id,
					'name': 'Player1'
				}],
				'current_turn': 0,
				'status': 'waiting',
				'winner': None
			}
			
			# Log aksi penting
			logging.warning(f"🎮 NEW ROOM: Room {room_id} created (word: {word})")
			
			return self.response(200, 'OK', json.dumps({'room_id': room_id, 'player_id': player_id, 'room': self.rooms[room_id]}), {'Content-Type': 'application/json'})
		
		elif object_address.startswith('/join/'):
			# Join room
			room_id = object_address.split('/')[-1]
			if room_id in self.rooms:
				room = self.rooms[room_id]
				if len(room['players']) < 2:
					player_id = str(uuid.uuid4())[:8]
					player_name = f'Player{len(room["players"]) + 1}'  # Player2 untuk yang bergabung
					room['players'].append({
						'id': player_id,
						'name': player_name
					})
					if len(room['players']) == 2:
						room['status'] = 'playing'
						# Log aksi penting
						logging.warning(f"🎮 GAME START: Room {room_id} - Game started with 2 players")
					else:
						# Log aksi penting
						logging.info(f"🎮 PLAYER JOIN: Player joined room {room_id}")
						
					return self.response(200, 'OK', json.dumps({'player_id': player_id, 'room': room}), {'Content-Type': 'application/json'})
				else:
					return self.response(400, 'Bad Request', json.dumps({'error': 'Room is full'}), {'Content-Type': 'application/json'})
			else:
				return self.response(404, 'Not Found', json.dumps({'error': 'Room not found'}), {'Content-Type': 'application/json'})
		
		elif object_address.startswith('/guess/'):
			# Make a guess
			parts = object_address.split('/')
			room_id = parts[2]
			letter = parts[3].upper() if len(parts) > 3 else ''
			
			if room_id in self.rooms and letter:
				room = self.rooms[room_id]
				if room['status'] == 'playing':
					if letter not in room['guessed_letters']:
						room['guessed_letters'].append(letter)
						
						if letter in room['word']:
							# Correct guess - update guessed_word
							for i, char in enumerate(room['word']):
								if char == letter:
									room['guessed_word'][i] = char
							
							# Log aksi penting
							current_player = room['players'][room['current_turn']]['name']
							logging.info(f"🎮 GOOD GUESS: Room {room_id} - {current_player} guessed '{letter}' correctly")
							
							# Check if word is complete
							if '_' not in room['guessed_word']:
								room['status'] = 'finished'
								room['winner'] = room['players'][room['current_turn']]['id']
								winner_name = room['players'][room['current_turn']]['name']
								# Log aksi penting
								logging.warning(f"🎮 GAME WON: Room {room_id} - {winner_name} won! Word: {room['word']}")
						else:
							# Wrong guess
							room['wrong_guesses'] += 1
							current_player = room['players'][room['current_turn']]['name']
							logging.info(f"🎮 WRONG GUESS: Room {room_id} - {current_player} guessed '{letter}' incorrectly ({room['wrong_guesses']}/{room['max_wrong_guesses']} wrong guesses)")
							
							if room['wrong_guesses'] >= room['max_wrong_guesses']:
								room['status'] = 'finished'
								room['winner'] = 'none'  # Both players lose
								# Log aksi penting
								logging.warning(f"🎮 GAME OVER: Room {room_id} - Players lost. Word was: {room['word']}")
						
						# Switch turn
						room['current_turn'] = (room['current_turn'] + 1) % len(room['players'])
					
					return self.response(200, 'OK', json.dumps(room), {'Content-Type': 'application/json'})
				else:
					return self.response(400, 'Bad Request', json.dumps({'error': 'Game not in progress'}), {'Content-Type': 'application/json'})
			else:
				return self.response(404, 'Not Found', json.dumps({'error': 'Invalid request'}), {'Content-Type': 'application/json'})
		
		else:
			return self.response(404, 'Not Found', json.dumps({'error': 'Endpoint not found'}), {'Content-Type': 'application/json'})

	def get_main_menu_html(self):
		"""Return HTML for main menu"""
		return """
		<!DOCTYPE html>
		<html>
		<head>
			<title>Hangman Multiplayer</title>
		</head>
		<body>
			<h1>Hangman Multiplayer</h1>
			<p>Use the pygame client to play the game!</p>
			<h2>Available Endpoints:</h2>
			<ul>
				<li>POST /create_room - Create a new room</li>
				<li>POST /join/[room_id] - Join a room</li>
				<li>GET /rooms - List all rooms</li>
				<li>GET /room/[room_id] - Get room status</li>
				<li>POST /guess/[room_id]/[letter] - Make a guess</li>
			</ul>
		</body>
		</html>
		"""
		
			 	
#>>> import os.path
#>>> ext = os.path.splitext('/ak/52.png')

if __name__=="__main__":
	httpserver = HttpServer()
	d = httpserver.proses('GET testing.txt HTTP/1.0')
	print(d)
	d = httpserver.proses('GET donalbebek.jpg HTTP/1.0')
	print(d)
	#d = httpserver.http_get('testing2.txt',{})
	#print(d)
#	d = httpserver.http_get('testing.txt')
#	print(d)















