import pygame
import sys
import socket
import json
import threading
import time

# Initialize Pygame
pygame.init()

# Constants
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 100, 200)
GREEN = (0, 200, 0)
RED = (200, 0, 0)
GRAY = (128, 128, 128)

# Server configuration
SERVER_HOST = 'localhost'
SERVER_PORT = 8889

class HangmanClient:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Hangman Multiplayer")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
        # Game state
        self.state = "MENU"  # MENU, CREATE_ROOM, JOIN_ROOM, WAITING, PLAYING
        self.room_id = None
        self.player_id = None
        self.game_data = None
        self.rooms_list = []
        self.selected_room = None
        self.message = ""
        self.message_timer = 0
        
        # UI elements
        self.buttons = {}
        self.create_buttons()

    def create_buttons(self):
        self.buttons = {
            'create_room': pygame.Rect(300, 200, 200, 50),
            'join_room': pygame.Rect(300, 280, 200, 50),
            'back': pygame.Rect(50, 50, 100, 40),
            'guess': pygame.Rect(350, 500, 100, 40)
        }

    def send_http_request(self, method, path, data=None):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((SERVER_HOST, SERVER_PORT))
            
            if method == "GET":
                request = f"GET {path} HTTP/1.0\r\n\r\n"
            else:  # POST
                body = json.dumps(data) if data else ""
                request = f"POST {path} HTTP/1.0\r\n"
                request += f"Content-Length: {len(body)}\r\n"
                request += f"Content-Type: application/json\r\n\r\n"
                request += body
            
            sock.send(request.encode())
            
            # Receive response
            response = b""
            while True:
                chunk = sock.recv(1024)
                if not chunk:
                    break
                response += chunk
            
            sock.close()
            
            # Parse response
            response_str = response.decode()
            if "\r\n\r\n" in response_str:
                headers, body = response_str.split("\r\n\r\n", 1)
                status_line = headers.split("\r\n")[0]
                status_code = int(status_line.split()[1])
                
                if status_code == 200:
                    try:
                        return json.loads(body)
                    except:
                        return body
                else:
                    self.message = f"Error: {status_code}"
                    return None
            
        except Exception as e:
            self.message = f"Connection error: {str(e)}"
            return None

    def handle_menu_events(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            
            if self.buttons['create_room'].collidepoint(mouse_pos):
                self.create_room()
            elif self.buttons['join_room'].collidepoint(mouse_pos):
                self.refresh_rooms()
                self.state = "JOIN_ROOM"

    def handle_join_room_events(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            
            if self.buttons['back'].collidepoint(mouse_pos):
                self.state = "MENU"
            else:
                # Check if clicked on a room
                for i, room in enumerate(self.rooms_list):
                    room_rect = pygame.Rect(250, 150 + i * 60, 300, 50)
                    if room_rect.collidepoint(mouse_pos) and room['players'] < 2:
                        self.join_room(room['id'])

    def handle_playing_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.unicode.isalpha():
                letter = event.unicode.upper()
                self.make_guess(letter)

    def create_room(self):
        response = self.send_http_request("POST", "/create_room")
        if response:
            self.room_id = response['room_id']
            self.player_id = response['player_id']  # Creator gets player_id
            self.game_data = response['room']  # Get initial room data
            self.state = "WAITING"
            self.message = f"Room created: {self.room_id}. You are Player 1. Waiting for Player 2..."
            self.wait_for_players()

    def join_room(self, room_id):
        response = self.send_http_request("POST", f"/join/{room_id}")
        if response:
            self.room_id = room_id
            self.player_id = response['player_id']
            self.game_data = response['room']
            
            if self.game_data['status'] == 'playing':
                self.state = "PLAYING"
                self.message = "Game started! Your turn to play!"
            else:
                self.state = "WAITING"
                # Find player name
                player_name = "Player2"  # Default
                for player in self.game_data['players']:
                    if player['id'] == self.player_id:
                        player_name = player['name']
                        break
                self.message = f"Joined as {player_name}. Waiting for game to start..."
                self.wait_for_players()

    def refresh_rooms(self):
        response = self.send_http_request("GET", "/rooms")
        if response:
            self.rooms_list = response['rooms']

    def wait_for_players(self):
        def check_room_status():
            while self.state == "WAITING":
                response = self.send_http_request("GET", f"/room/{self.room_id}")
                if response:
                    old_status = self.game_data['status'] if self.game_data else 'waiting'
                    self.game_data = response
                    if response['status'] == 'playing' and old_status == 'waiting':
                        self.state = "PLAYING"
                        self.message = "Game started! Let's play!"
                        self.message_timer = 0
                        break
                time.sleep(1)
        
        threading.Thread(target=check_room_status, daemon=True).start()

    def make_guess(self, letter):
        if self.game_data and self.game_data['status'] == 'playing':
            # Check if letter already guessed
            if letter in self.game_data['guessed_letters']:
                self.message = f"Letter '{letter}' already guessed!"
                self.message_timer = 0
                return
            
            # Check if it's player's turn
            current_player = self.game_data['players'][self.game_data['current_turn']]
            if current_player['id'] == self.player_id:
                response = self.send_http_request("POST", f"/guess/{self.room_id}/{letter}")
                if response:
                    old_wrong_guesses = self.game_data['wrong_guesses']
                    self.game_data = response
                    
                    # Give feedback
                    if letter in self.game_data['word']:
                        self.message = f"Good guess! '{letter}' is in the word!"
                    else:
                        self.message = f"Sorry, '{letter}' is not in the word."
                    self.message_timer = 0  # Reset timer for new message
            else:
                self.message = "Wait for your turn!"
                self.message_timer = 0

    def update_game_state(self):
        if self.state == "PLAYING" and self.room_id:
            response = self.send_http_request("GET", f"/room/{self.room_id}")
            if response:
                self.game_data = response

    def draw_menu(self):
        self.screen.fill(WHITE)
        
        title = self.font.render("Hangman Multiplayer", True, BLACK)
        title_rect = title.get_rect(center=(WINDOW_WIDTH//2, 100))
        self.screen.blit(title, title_rect)
        
        # Draw buttons
        pygame.draw.rect(self.screen, BLUE, self.buttons['create_room'])
        pygame.draw.rect(self.screen, BLUE, self.buttons['join_room'])
        
        # Button text
        create_text = self.font.render("Create Room", True, WHITE)
        join_text = self.font.render("Join Room", True, WHITE)
        
        self.screen.blit(create_text, (320, 215))
        self.screen.blit(join_text, (335, 295))
        
        # Show message
        if self.message:
            msg_text = self.small_font.render(self.message, True, RED)
            self.screen.blit(msg_text, (50, 500))

    def draw_join_room(self):
        self.screen.fill(WHITE)
        
        title = self.font.render("Available Rooms", True, BLACK)
        self.screen.blit(title, (50, 20))
        
        # Back button
        pygame.draw.rect(self.screen, GRAY, self.buttons['back'])
        back_text = self.small_font.render("Back", True, WHITE)
        self.screen.blit(back_text, (75, 65))
        
        # Draw rooms list
        for i, room in enumerate(self.rooms_list):
            y = 150 + i * 60
            color = GREEN if room['players'] < 2 else RED
            room_rect = pygame.Rect(250, y, 300, 50)
            pygame.draw.rect(self.screen, color, room_rect)
            
            room_text = self.small_font.render(f"Room {room['id']} ({room['players']}/2)", True, WHITE)
            self.screen.blit(room_text, (260, y + 15))

    def draw_waiting(self):
        self.screen.fill(WHITE)
        
        title = self.font.render("Waiting for Players...", True, BLACK)
        title_rect = title.get_rect(center=(WINDOW_WIDTH//2, 200))
        self.screen.blit(title, title_rect)
        
        room_text = self.font.render(f"Room ID: {self.room_id}", True, BLACK)
        room_rect = room_text.get_rect(center=(WINDOW_WIDTH//2, 250))
        self.screen.blit(room_text, room_rect)
        
        if self.game_data:
            players_text = self.font.render(f"Players: {len(self.game_data['players'])}/2", True, BLACK)
            players_rect = players_text.get_rect(center=(WINDOW_WIDTH//2, 300))
            self.screen.blit(players_text, players_rect)
            
            # Show current players
            for i, player in enumerate(self.game_data['players']):
                player_name = player['name']
                if player['id'] == self.player_id:
                    player_name += " (YOU)"
                player_surface = self.small_font.render(player_name, True, BLUE)
                player_rect = player_surface.get_rect(center=(WINDOW_WIDTH//2, 330 + i * 30))
                self.screen.blit(player_surface, player_rect)
            
            # Show what we're waiting for
            if len(self.game_data['players']) == 1:
                waiting_text = "Waiting for Player 2 to join..."
                waiting_surface = self.small_font.render(waiting_text, True, RED)
                waiting_rect = waiting_surface.get_rect(center=(WINDOW_WIDTH//2, 420))
                self.screen.blit(waiting_surface, waiting_rect)
        
        # Show message
        if self.message:
            msg_text = self.small_font.render(self.message, True, GREEN)
            msg_rect = msg_text.get_rect(center=(WINDOW_WIDTH//2, 480))
            self.screen.blit(msg_text, msg_rect)

    def draw_playing(self):
        self.screen.fill(WHITE)
        
        if not self.game_data:
            return
        
        # Draw hangman
        self.draw_hangman()
        
        # Draw clue
        if 'clue' in self.game_data:
            clue_text = f"Clue: {self.game_data['clue']}"
            # Bagi clue menjadi beberapa baris jika terlalu panjang
            max_width = WINDOW_WIDTH - 100
            words = clue_text.split()
            lines = []
            current_line = ""
            
            for word in words:
                test_line = current_line + word + " "
                test_surface = self.small_font.render(test_line, True, BLACK)
                if test_surface.get_width() > max_width and current_line:
                    lines.append(current_line.strip())
                    current_line = word + " "
                else:
                    current_line = test_line
            
            if current_line:
                lines.append(current_line.strip())
            
            # Tampilkan clue
            for i, line in enumerate(lines):
                clue_surface = self.small_font.render(line, True, BLUE)
                self.screen.blit(clue_surface, (50, 50 + i * 25))
        
        # Draw word
        word_display = ' '.join(self.game_data['guessed_word'])
        word_text = self.font.render(word_display, True, BLACK)
        word_rect = word_text.get_rect(center=(WINDOW_WIDTH//2, 400))
        self.screen.blit(word_text, word_rect)
        
        # Draw guessed letters
        guessed_text = f"Guessed: {', '.join(self.game_data['guessed_letters'])}"
        guessed_surface = self.small_font.render(guessed_text, True, BLACK)
        self.screen.blit(guessed_surface, (50, 450))
        
        # Draw wrong guesses
        wrong_text = f"Wrong guesses: {self.game_data['wrong_guesses']}/{self.game_data['max_wrong_guesses']}"
        wrong_surface = self.small_font.render(wrong_text, True, RED)
        self.screen.blit(wrong_surface, (50, 480))
        
        # Draw current turn
        current_player = self.game_data['players'][self.game_data['current_turn']]
        turn_text = f"Current turn: {current_player['name']}"
        if current_player['id'] == self.player_id:
            turn_text += " (YOUR TURN - Press a letter key!)"
        turn_surface = self.small_font.render(turn_text, True, BLUE)
        self.screen.blit(turn_surface, (50, 510))
        
        # Draw game status
        if self.game_data['status'] == 'finished':
            if self.game_data['winner'] == self.player_id:
                status_text = "YOU WIN!"
                color = GREEN
            elif self.game_data['winner'] == 'none':
                status_text = "GAME OVER - Nobody wins!"
                color = RED
            else:
                status_text = "YOU LOSE!"
                color = RED
            
            status_surface = self.font.render(status_text, True, color)
            status_rect = status_surface.get_rect(center=(WINDOW_WIDTH//2, 150))
            self.screen.blit(status_surface, status_rect)
            
            # Show the correct answer
            answer_text = f"The answer was: {self.game_data['word']}"
            answer_surface = self.small_font.render(answer_text, True, BLACK)
            answer_rect = answer_surface.get_rect(center=(WINDOW_WIDTH//2, 180))
            self.screen.blit(answer_surface, answer_rect)

    def draw_hangman(self):
        wrong_guesses = self.game_data['wrong_guesses']

        # Gallows (selalu digambar)
        # Base
        pygame.draw.line(self.screen, BLACK, (100, 350), (200, 350), 5)
        # Vertical pole
        pygame.draw.line(self.screen, BLACK, (150, 350), (150, 100), 5)
        # Horizontal beam
        pygame.draw.line(self.screen, BLACK, (150, 100), (220, 100), 5)
        # Noose
        pygame.draw.line(self.screen, BLACK, (220, 100), (220, 130), 5)

        # 1. Head
        if wrong_guesses >= 1:
            pygame.draw.circle(self.screen, BLACK, (220, 150), 20, 3)

        # 2. Body
        if wrong_guesses >= 2:
            pygame.draw.line(self.screen, BLACK, (220, 170), (220, 250), 5)

        # 3. Left arm
        if wrong_guesses >= 3:
            pygame.draw.line(self.screen, BLACK, (220, 190), (190, 220), 5)

        # 4. Right arm
        if wrong_guesses >= 4:
            pygame.draw.line(self.screen, BLACK, (220, 190), (250, 220), 5)

        # 5. Left leg
        if wrong_guesses >= 5:
            pygame.draw.line(self.screen, BLACK, (220, 250), (190, 290), 5)

        # 6. Right leg
        if wrong_guesses >= 6:
            pygame.draw.line(self.screen, BLACK, (220, 250), (250, 290), 5)


    def run(self):
        running = True
        update_timer = 0
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                if self.state == "MENU":
                    self.handle_menu_events(event)
                elif self.state == "JOIN_ROOM":
                    self.handle_join_room_events(event)
                elif self.state == "PLAYING":
                    self.handle_playing_events(event)
            
            # Update timers
            delta_time = self.clock.get_time()
            update_timer += delta_time
            self.message_timer += delta_time
            
            # Clear message after 3 seconds
            if self.message_timer > 3000:
                self.message = ""
                self.message_timer = 0

            
            # Update game state periodically
            if update_timer > 2000:  # Update every 2 seconds
                if self.state == "PLAYING":
                    self.update_game_state()
                update_timer = 0
            
            # Draw based on current state
            if self.state == "MENU":
                self.draw_menu()
            elif self.state == "JOIN_ROOM":
                self.draw_join_room()
            elif self.state == "WAITING":
                self.draw_waiting()
            elif self.state == "PLAYING":
                self.draw_playing()
            
            pygame.display.flip()
            self.clock.tick(60)
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    client = HangmanClient()
    client.run()
