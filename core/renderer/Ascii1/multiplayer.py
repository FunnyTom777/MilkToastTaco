"""
MTT Multiplayer — LAN discovery (UDP broadcast) + server-authoritative TCP

Design:
  - Host broadcasts beacons via UDP to 255.255.255.255:54546 and 127.0.0.1
  - Clients run DiscoveryListener bound to 0.0.0.0:54546 to collect active hosts
  - TCP game server on port 54545 (or next free) carries reliable state
  - Packets are length-prefixed JSON (4-byte BE len + bytes)
  - Server is authoritative: clients send {t:'input', dx, dy, seq}, server applies to
    server-side Player objects and broadcasts {t:'state', players:{id:{x,y,vx,vy}}, tick}
  - Host saves world; clients don't.

This module is pygame-free — only stdlib. ascii.py drives it.

Usage:
  disc = Discovery(); disc.start(); disc.get_hosts() -> list
  host = HostSession(world, host_player, port=54545); host.start()
  client = ClientSession(host_ip, port); client.connect(); client.send_input(dx,dy); client.poll_state()
"""
from __future__ import annotations

import json
import socket
import struct
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

BROADCAST_PORT = 54546
DEFAULT_TCP_PORT = 54545
BROADCAST_INTERVAL = 0.8
DISCOVERY_TIMEOUT = 3.0
STATE_RATE = 20  # server state broadcast Hz
INPUT_RATE = 20

def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Doesn't need to succeed; trick to get interface IP
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip.startswith("127."):
            raise Exception("loopback")
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"

def find_free_tcp_port(start=DEFAULT_TCP_PORT) -> int:
    for p in range(start, start + 20):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # No REUSEADDR for TCP — need exclusive bind to avoid duplicate hosts on same port
            s.bind(("", p))
            s.close()
            return p
        except Exception:
            continue
    return start

def _send_packet(sock: socket.socket, obj: dict):
    try:
        data = json.dumps(obj).encode("utf-8")
        sock.sendall(struct.pack("!I", len(data)) + data)
    except Exception as e:
        raise

def _recv_exact(sock: socket.socket, n: int, timeout: float = 5.0) -> bytes:
    sock.settimeout(timeout)
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("closed")
        buf += chunk
    return buf

def _recv_packet(sock: socket.socket, timeout: float = 2.0):
    hdr = _recv_exact(sock, 4, timeout=timeout)
    length = struct.unpack("!I", hdr)[0]
    if length > 64 * 1024:
        raise ValueError(f"packet too large {length}")
    body = _recv_exact(sock, length, timeout=timeout)
    return json.loads(body.decode("utf-8"))

# ---------------------------------------------------------------------------
# Discovery beacons (host side) + listener (client side)
# ---------------------------------------------------------------------------

@dataclass
class DiscoveredHost:
    ip: str
    port: int
    host_name: str = "MTT Host"
    players: int = 1
    seed: int = 0
    last_seen: float = field(default_factory=time.time)

class Discovery:
    """Listens for UDP beacons. Hosts also call start_beacon separately."""
    def __init__(self, listen_port=BROADCAST_PORT):
        self.listen_port = listen_port
        self.hosts: Dict[str, DiscoveredHost] = {}  # key ip:port
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._sock: Optional[socket.socket] = None
        self._lock = threading.Lock()

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True, name="MTT-Discovery")
        self._thread.start()

    def stop(self):
        self._running = False
        try:
            if self._sock:
                self._sock.close()
        except Exception:
            pass
        if self._thread:
            self._thread.join(timeout=1.0)

    def get_hosts(self) -> List[DiscoveredHost]:
        # expire old
        now = time.time()
        with self._lock:
            dead = [k for k, v in self.hosts.items() if now - v.last_seen > DISCOVERY_TIMEOUT]
            for k in dead:
                del self.hosts[k]
            return sorted(list(self.hosts.values()), key=lambda h: h.last_seen, reverse=True)

    def _listen_loop(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # On Windows SO_REUSEADDR allows multiple binds; for linux also try REUSEPORT if available
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except Exception:
                pass
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.bind(("", self.listen_port))
            s.settimeout(1.0)
            self._sock = s
        except Exception as e:
            print(f"[mp] Discovery bind failed port {self.listen_port}: {e}")
            return
        while self._running:
            try:
                data, addr = s.recvfrom(8192)
                try:
                    msg = json.loads(data.decode("utf-8"))
                    if msg.get("type") != "mtt_host":
                        continue
                    ip = msg.get("ip") or addr[0]
                    port = int(msg.get("port", DEFAULT_TCP_PORT))
                    key = f"{ip}:{port}"
                    host = DiscoveredHost(
                        ip=ip,
                        port=port,
                        host_name=str(msg.get("host_name", "MTT Host")),
                        players=int(msg.get("players", 1)),
                        seed=int(msg.get("seed", 0)),
                        last_seen=time.time()
                    )
                    with self._lock:
                        self.hosts[key] = host
                except Exception:
                    continue
            except socket.timeout:
                continue
            except Exception:
                if not self._running:
                    break
                time.sleep(0.2)

class Beacon:
    """Host-side broadcaster."""
    def __init__(self, tcp_port: int, host_name: str = "MTT Host", get_players=None, get_seed=None):
        self.tcp_port = tcp_port
        self.host_name = host_name
        self.get_players = get_players  # callable -> int
        self.get_seed = get_seed
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="MTT-Beacon")
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)

    def _loop(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        targets = [("255.255.255.255", BROADCAST_PORT), ("127.0.0.1", BROADCAST_PORT)]
        # Also try broadcast to local subnet via get_local_ip's broadcast? For now two targets fine.
        while self._running:
            try:
                ip = get_local_ip()
                players = self.get_players() if self.get_players else 1
                seed = self.get_seed() if self.get_seed else 0
                msg = {
                    "type": "mtt_host",
                    "ip": ip,
                    "port": self.tcp_port,
                    "host_name": self.host_name,
                    "players": players,
                    "seed": seed,
                    "version": 1
                }
                data = json.dumps(msg).encode("utf-8")
                for t in targets:
                    try:
                        s.sendto(data, t)
                    except Exception:
                        pass
            except Exception as e:
                # beacon error non-fatal
                pass
            time.sleep(BROADCAST_INTERVAL)
        try:
            s.close()
        except Exception:
            pass

# ---------------------------------------------------------------------------
# Host session (server-authoritative)
# ---------------------------------------------------------------------------

class HostSession:
    """
    TCP server authoritative. Main thread (ascii.py) drives tick() to apply inputs
    and broadcast state. Network threads only handle IO queues.
    """
    def __init__(self, world, host_player, tcp_port: int = 0, host_name: str = "Host"):
        self.world = world
        self.host_player = host_player
        if not hasattr(host_player, "player_id") or not host_player.player_id:
            host_player.player_id = "host"
        self.tcp_port = tcp_port if tcp_port else find_free_tcp_port()
        self.host_name = host_name
        self._running = False
        self._listen_sock: Optional[socket.socket] = None
        self._accept_thread: Optional[threading.Thread] = None
        # client sockets -> player_id, socket
        self.clients: Dict[str, socket.socket] = {}  # player_id -> sock
        self._clients_lock = threading.Lock()
        # inbox: player_id -> latest input {dx,dy,seq}
        self.inbox: Dict[str, dict] = {}
        self._inbox_lock = threading.Lock()
        self.beacon = Beacon(self.tcp_port, host_name=self.host_name,
                             get_players=lambda: 1 + len(self.clients),
                             get_seed=self._get_seed)
        self._next_client_id = 1
        self.tick = 0

    def _get_seed(self):
        try:
            from . import terrain_generation as _tg
            return int(_tg.get_generation_config().seed)
        except Exception:
            return 0

    def start(self):
        if self._running:
            return
        # bind TCP — exclusive, no REUSEADDR to prevent duplicate hosts on same port
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("", self.tcp_port))
        except Exception as e:
            # try free port
            self.tcp_port = find_free_tcp_port(self.tcp_port + 1)
            s.bind(("", self.tcp_port))
        s.listen(8)
        s.settimeout(1.0)
        self._listen_sock = s
        self._running = True
        self.beacon.start()
        self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True, name="MTT-HostAccept")
        self._accept_thread.start()
        print(f"[mp] Host started on {get_local_ip()}:{self.tcp_port}")

    def stop(self):
        self._running = False
        self.beacon.stop()
        try:
            if self._listen_sock:
                self._listen_sock.close()
        except Exception:
            pass
        with self._clients_lock:
            for pid, sock in list(self.clients.items()):
                try:
                    sock.close()
                except Exception:
                    pass
            self.clients.clear()
        if self._accept_thread:
            self._accept_thread.join(timeout=1.0)
        print("[mp] Host stopped")

    def _accept_loop(self):
        while self._running:
            try:
                client_sock, addr = self._listen_sock.accept()  # type: ignore
                client_sock.settimeout(5.0)
                # Handshake: wait for hello
                try:
                    hello = _recv_packet(client_sock, timeout=5.0)
                    if hello.get("t") != "hello":
                        client_sock.close()
                        continue
                    req_name = str(hello.get("name", "Player"))[:16]
                except Exception as e:
                    try:
                        client_sock.close()
                    except Exception:
                        pass
                    continue
                # Assign id
                pid = f"p{self._next_client_id}"
                self._next_client_id += 1
                # Create remote player on server side
                try:
                    from .player import Player
                except Exception:
                    from core.renderer.Ascii1.player import Player
                p = Player(player_id=pid, x=float(self.host_player.x) + 1, y=float(self.host_player.y) + 1, name=req_name)
                # Register in world? Use registry via HostSession.players dict (ascii will hold registry)
                # We'll store in a simple dict and let ascii's main loop integrate.
                # For now keep reference; ascii will poll get_all_players
                # Add to clients
                with self._clients_lock:
                    self.clients[pid] = client_sock
                with self._inbox_lock:
                    self.inbox[pid] = {"dx": 0, "dy": 0, "name": req_name, "player_obj": p}
                # Send welcome with assigned spawn position
                _send_packet(client_sock, {"t": "welcome", "your_id": pid, "host_id": self.host_player.player_id, "seed": self._get_seed(), "x": float(p.x), "y": float(p.y)})
                print(f"[mp] Client {req_name} ({addr}) assigned {pid}")
                # Spawn reader thread for this client
                threading.Thread(target=self._client_reader, args=(pid, client_sock), daemon=True, name=f"MTT-Reader-{pid}").start()
            except socket.timeout:
                continue
            except Exception as e:
                if not self._running:
                    break
                time.sleep(0.1)

    def _client_reader(self, pid: str, sock: socket.socket):
        sock.settimeout(30.0)
        while self._running:
            try:
                pkt = _recv_packet(sock, timeout=10.0)
                t = pkt.get("t")
                if t == "input":
                    # expect dx,dy
                    with self._inbox_lock:
                        if pid in self.inbox:
                            self.inbox[pid]["dx"] = float(pkt.get("dx", 0))
                            self.inbox[pid]["dy"] = float(pkt.get("dy", 0))
                            self.inbox[pid]["seq"] = int(pkt.get("seq", 0))
                elif t == "ping":
                    _send_packet(sock, {"t": "pong", "ts": pkt.get("ts")})
                # ignore other
            except Exception as e:
                # disconnect
                print(f"[mp] Client {pid} disconnected: {e}")
                with self._clients_lock:
                    self.clients.pop(pid, None)
                with self._inbox_lock:
                    self.inbox.pop(pid, None)
                try:
                    sock.close()
                except Exception:
                    pass
                break

    # Called from main thread each tick
    def consume_inputs(self) -> Dict[str, dict]:
        with self._inbox_lock:
            return dict(self.inbox)

    def get_client_players(self) -> Dict[str, object]:
        with self._inbox_lock:
            return {pid: info.get("player_obj") for pid, info in self.inbox.items() if "player_obj" in info}

    def broadcast_state(self, all_players: Dict[str, dict]):
        """all_players: {player_id: {x,y,vx,vy}} authoritative"""
        if not self._running:
            return
        pkt = {"t": "state", "players": all_players, "tick": self.tick}
        self.tick += 1
        dead = []
        with self._clients_lock:
            for pid, sock in list(self.clients.items()):
                try:
                    _send_packet(sock, pkt)
                except Exception:
                    dead.append(pid)
            for pid in dead:
                try:
                    self.clients[pid].close()
                except Exception:
                    pass
                self.clients.pop(pid, None)
                with self._inbox_lock:
                    self.inbox.pop(pid, None)

    def is_running(self):
        return self._running

# ---------------------------------------------------------------------------
# Client session
# ---------------------------------------------------------------------------

class ClientSession:
    """
    Connects to host, sends inputs, receives state.
    Thread for reading state continuously.
    """
    def __init__(self, host_ip: str, host_port: int, local_player, player_name: str = "Player"):
        self.host_ip = host_ip
        self.host_port = host_port
        self.local_player = local_player
        self.player_name = player_name
        self.sock: Optional[socket.socket] = None
        self._running = False
        self._reader_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.latest_state: Optional[dict] = None
        self.my_id: Optional[str] = None
        self.host_id: Optional[str] = None
        self._seq = 0

    def connect(self, timeout=5.0) -> bool:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((self.host_ip, self.host_port))
            # hello
            _send_packet(s, {"t": "hello", "name": self.player_name})
            s.settimeout(5.0)
            welcome = _recv_packet(s, timeout=5.0)
            if welcome.get("t") != "welcome":
                s.close()
                return False
            self.my_id = welcome.get("your_id")
            self.host_id = welcome.get("host_id", "host")
            if self.my_id:
                self.local_player.player_id = self.my_id
            # Apply assigned spawn position from host (fixes same-PC same-copy spawn same spot)
            if "x" in welcome and "y" in welcome:
                try:
                    self.local_player.x = float(welcome["x"])
                    self.local_player.y = float(welcome["y"])
                    # also update name if provided
                    if "name" in welcome:
                        self.local_player.name = str(welcome["name"])[:16]
                except Exception:
                    pass
            s.settimeout(10.0)
            self.sock = s
            self._running = True
            self._reader_thread = threading.Thread(target=self._read_loop, daemon=True, name="MTT-ClientReader")
            self._reader_thread.start()
            print(f"[mp] Client connected as {self.my_id} to {self.host_ip}:{self.host_port}")
            return True
        except Exception as e:
            print(f"[mp] Client connect failed: {e}")
            try:
                s.close()
            except Exception:
                pass
            return False

    def disconnect(self):
        self._running = False
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass
        if self._reader_thread:
            self._reader_thread.join(timeout=1.0)
        print("[mp] Client disconnected")

    def is_connected(self):
        return self._running and self.sock is not None

    def _read_loop(self):
        assert self.sock is not None
        while self._running:
            try:
                pkt = _recv_packet(self.sock, timeout=10.0)
                if pkt.get("t") == "state":
                    with self._lock:
                        self.latest_state = pkt
                elif pkt.get("t") == "pong":
                    pass
            except Exception as e:
                print(f"[mp] Client read error: {e}")
                self._running = False
                break

    def send_input(self, dx: float, dy: float):
        if not self.is_connected() or self.sock is None:
            return
        self._seq += 1
        try:
            _send_packet(self.sock, {"t": "input", "dx": float(dx), "dy": float(dy), "seq": self._seq})
        except Exception:
            self._running = False

    def poll_state(self) -> Optional[dict]:
        with self._lock:
            st = self.latest_state
            self.latest_state = None
            return st

    def get_latest_state_peek(self) -> Optional[dict]:
        with self._lock:
            return self.latest_state
