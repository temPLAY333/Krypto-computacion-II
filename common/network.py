import socket
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("NetworkManager")

class NetworkManager:
    @staticmethod
    def is_ipv6_available():
        """Comprueba si IPv6 está disponible en esta máquina."""
        try:
            # Intentamos crear un socket IPv6
            sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
            sock.close()
            return True
        except Exception:
            return False
    
    @staticmethod
    def create_server_socket(port, hostname=None):
        """Crea un socket para servidor que soporte IPv6 si está disponible, o IPv4 en caso contrario."""
        use_ipv6 = NetworkManager.is_ipv6_available()
        
        if use_ipv6:
            sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            # Permite reutilizar la dirección y puerto
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Configurar para aceptar también conexiones IPv4 (dual-stack)
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            binding_address = hostname if hostname else '::'
            logger.info(f"Servidor usando IPv6 en {binding_address}:{port}")
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            binding_address = hostname if hostname else '0.0.0.0'
            logger.info(f"Servidor usando IPv4 en {binding_address}:{port}")
        
        sock.bind((binding_address, port))
        return sock, use_ipv6
    
    @staticmethod
    def create_client_socket(server_address, port):
        """
        Crea un socket cliente que usa IPv6 si tanto cliente como servidor lo soportan,
        o IPv4 en caso contrario.
        """
        local_ipv6 = NetworkManager.is_ipv6_available()
        
        # Primero intentamos una conexión IPv6 si está disponible localmente
        if local_ipv6:
            try:
                # Intentar conectar por IPv6
                sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                sock.connect((server_address, port, 0, 0))  # Formato (host, port, flowinfo, scopeid)
                logger.info(f"Cliente conectado a {server_address}:{port} usando IPv6")
                return sock, True
            except Exception as e:
                logger.info(f"No se pudo conectar por IPv6: {e}")
                sock.close()
        
        # Si IPv6 falla o no está disponible, intentamos IPv4
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((server_address, port))
        logger.info(f"Cliente conectado a {server_address}:{port} usando IPv4")
        return sock, False