from concurrent import futures
import grpc
from api import network_pb2_grpc
import network

def run():
    # ポート8081でサーバーを起動
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
    network_pb2_grpc.add_NetworkServicer_to_server(network.Network(), server)
    server.add_insecure_port('[::]:8081')
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    run()