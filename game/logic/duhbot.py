from game.logic.base import BaseLogic
from game.models import Board, GameObject
from collections import deque
import random

class DuhBot(BaseLogic):
    def __init__(self):
        super().__init__()
        self.directions = [(1, 0), (0, 1), (-1, 0), (0, -1)]
        self.status = "BERBURU"
        self.last_direction = None
        self.danger_zone = []
        self.data_enemy = {}

    def hitung_jarak(self, pos1, pos2):
        """Menghitung jarak antara dua titik (Manhattan distance)"""
        return abs(pos1.x - pos2.x) + abs(pos1.y - pos2.y)

    def menentukan_arah(self, pos_sekarang, pos_tujuan):
        """Memilih arah menuju tujuan"""
        selisih_x = pos_tujuan.x - pos_sekarang.x
        selisih_y = pos_tujuan.y - pos_sekarang.y

        if abs(selisih_x) > abs(selisih_y):
            return (1 if selisih_x > 0 else -1, 0)  # memprioritaskan gerak horizontal
        else:
            return (0, 1 if selisih_y > 0 else -1)  # memprioritaskan gerak vertikal

    def cari_teleport(self, board, pos_sekarang):
        """Mencari teleporter terdekat menggunakan BFS"""
        if not hasattr(board, 'teleporters') or len(board.teleporters) < 2:
            return None

        antrian = deque([(pos_sekarang.x, pos_sekarang.y, [])])
        sudah_dilewati = set()
        sudah_dilewati.add((pos_sekarang.x, pos_sekarang.y))

        while antrian:
            x, y, jalur = antrian.popleft()
            
            for tele in board.teleporters:
                if (x, y) == (tele.position.x, tele.position.y):
                    return tele.position, jalur[0] if jalur else None

            for dx, dy in self.directions:
                x_baru, y_baru = x + dx, y + dy
                if (0 <= x_baru < board.width and 
                    0 <= y_baru < board.height and 
                    (x_baru, y_baru) not in sudah_dilewati and
                    (x_baru, y_baru) not in self.danger_zone):
                    sudah_dilewati.add((x_baru, y_baru))
                    antrian.append((x_baru, y_baru, jalur + [(dx, dy)]))
        return None

    def harus_menyerang(self, bot_saya, board):
        """Memutuskan apakah akan menyerang bot lawan"""
        if bot_saya.properties.diamonds == 0:  # hanya menyerang jika tidak membawa berlian
            for enemy in board.bots:
                if (enemy.id != bot_saya.id and 
                    enemy.properties.diamonds > 0 and
                    self.hitung_jarak(bot_saya.position, enemy.position) <= 2):
                    return True
        return False

    def next_move(self, bot_saya: GameObject, board: Board):
        base = bot_saya.properties.base
        berlian_dibawa = bot_saya.properties.diamonds
        posisi_sekarang = bot_saya.position
        waktu_tersisa = bot_saya.properties.milliseconds_left / 1000
        self.danger_zone = []

        # 1. mode cepat pulang jika waktu tersisa kurang dari 10 detik
        if waktu_tersisa < 10 and berlian_dibawa > 0:
            waktu_ke_base = self.hitung_jarak(posisi_sekarang, base) * 0.3
            if waktu_tersisa < waktu_ke_base + 1:
                self.status = "CEPAT_PULANG"
                return self.menentukan_arah(posisi_sekarang, base)

        # 2. mode menyerang lawan
        if self.harus_menyerang(bot_saya, board):
            for enemy in board.bots:
                if (enemy.id != bot_saya.id and 
                    enemy.properties.diamonds > 0 and
                    self.hitung_jarak(posisi_sekarang, enemy.position) <= 2):
                    self.status = "SERANG"
                    return self.menentukan_arah(posisi_sekarang, enemy.position)

        # 3. kembali ke base jika membawa berlian
        if (berlian_dibawa >= 5 or 
            (berlian_dibawa == 4 and any(d.properties.points == 2 for d in board.diamonds)) or
            (berlian_dibawa >= 3 and waktu_tersisa < 20)):
            self.status = "PULANG"
            return self.menentukan_arah(posisi_sekarang, base)

        # 4. menghindari bot lawan
        if berlian_dibawa > 0:
            for enemy in board.bots:
                if (enemy.id != bot_saya.id and 
                    self.hitung_jarak(posisi_sekarang, enemy.position) <= 2):
                    self.status = "MENGHINDAR"
                    self.danger_zone.append((enemy.position.x, enemy.position.y))
                    selisih_x = posisi_sekarang.x - enemy.position.x
                    selisih_y = posisi_sekarang.y - enemy.position.y
                    arah = (1 if selisih_x < 0 else -1, 0) if abs(selisih_x) > abs(selisih_y) else (0, 1 if selisih_y < 0 else -1)
                    return arah

        # 5. memanfaatkan teleportasi
        info_teleport = self.cari_teleport(board, posisi_sekarang)
        if info_teleport and self.status != "MENGHINDAR":
            posisi_tele, jalur = info_teleport
            if jalur and self.hitung_jarak(posisi_sekarang, posisi_tele) < 4:
                return jalur

        # 6. memilih berlian terbaik
        nilai_tertinggi = -float('inf')
        berlian_terbaik = None
        
        for diamond in board.diamonds:
            jarak = self.hitung_jarak(posisi_sekarang, diamond.position)
            nilai_berlian = diamond.properties.points
            
            if berlian_dibawa + nilai_berlian > 5:
                continue
                
            skor = nilai_berlian / (jarak + 1)
            
            if nilai_berlian == 2: 
                skor *= 1.5
            
            if (diamond.position.x, diamond.position.y) in self.danger_zone:
                skor *= 0.3
                
            if skor > nilai_tertinggi:
                nilai_tertinggi = skor
                berlian_terbaik = diamond

        if berlian_terbaik:
            self.status = "MENGUMPULKAN"
            return self.menentukan_arah(posisi_sekarang, berlian_terbaik.position)

        # 7. mencari tombol untuk teleportasi
        if hasattr(board, 'buttons'):
            for button in board.buttons:
                if (self.hitung_jarak(posisi_sekarang, button.position) < 3 and
                    (button.position.x, button.position.y) not in self.danger_zone):
                    return self.menentukan_arah(posisi_sekarang, button.position)

        # 8. kembali ke base jika membawa berlian
        if berlian_dibawa > 0:
            self.status = "KEMBALI"
            return self.menentukan_arah(posisi_sekarang, base)
            
        # 9. gerak acak jika tidak ada pilihan lain
        arah_mungkin = [
            (dx, dy) for dx, dy in self.directions
            if (0 <= posisi_sekarang.x + dx < board.width and 
                0 <= posisi_sekarang.y + dy < board.height and
                (dx, dy) != (0, 0))
        ]
        if arah_mungkin:
            return random.choice(arah_mungkin)
                
        return (0, 0)