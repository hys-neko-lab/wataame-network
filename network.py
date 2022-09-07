from api import network_pb2
from api import network_pb2_grpc
import libvirt
import docker
import string
import ipaddress, ipget

class Network(network_pb2_grpc.NetworkServicer):
    # README.mdに従って予めインタフェースを作成のこと
    interface="wataame-br0"

    def __init__(self):
        self.conn = libvirt.open('qemu:///system')
        self.client = docker.from_env()
    
    def createVN(self, request, context):
        if self.conn == None:
            message = "conn failed."
            return network_pb2.CreateVNReply(message=message)
        
        # gRPC経由で送信されたcidrから、XMLに必要な情報を計算
        net = ipaddress.ip_network(request.cidr)
        ipaddr = str(list(net.hosts())[0])
        netmask = str(net.netmask)
        ipstart = str(list(net.hosts())[1])
        ipend = str(list(net.hosts())[-1])

        # XMLのテンプレートを元にネットワーク定義を作成
        with open('templates/network.xml') as f:
            t = string.Template(f.read())
        xmldefine = t.substitute(
            name=request.name,
            uuid=request.uuid,
            mac=request.mac,
            ipaddr=ipaddr,
            netmask=netmask,
            ipstart=ipstart,
            ipend=ipend
        )
        print(xmldefine)

        # ネットワークを定義、自動スタート設定、作成まで行う
        network = self.conn.networkDefineXML(xmldefine)
        if network == None:
            message = "define network failed"
            return network_pb2.CreateVNReply(message=message)

        if network.setAutostart(1) != 0:
            message = "set network to autostart failed"
            return network_pb2.CreateVNReply(message=message)

        if network.create() != 0:
            message = "create network failed"
            return network_pb2.CreateVNReply(message=message)
        
        # Dockerネットワークを作成
        # macvlanで、親はlibvirtで作成したネットワークとする
        ipam_pool = docker.types.IPAMPool(subnet=request.cidr)
        ipam_config = docker.types.IPAMConfig(pool_configs=[ipam_pool])
        docknet = self.client.networks.create(
            request.name+'-docker',
            driver='macvlan',
            ipam=ipam_config,
            options={
                'parent': 'br'+request.name
            })

        message = "UUID:" + request.uuid + " created."
        return network_pb2.CreateVNReply(message=message, docknetid=docknet.id)

    def deleteVN(self, request, context):
        if self.conn == None:
            message = "conn failed."
            return network_pb2.DeleteVNReply(message=message)
        
        # UUIDでネットワークを探す
        network = self.conn.networkLookupByUUIDString(request.uuid)
        if network == None:
            message = "find network failed."
            return network_pb2.DeleteVNReply(message=message)
        
        # 消す前に停止する
        if network.destroy() != 0:
            message = "destroy network failed."
            return network_pb2.DeleteVNReply(message=message)

        # 停止したら削除
        if network.undefine() != 0:
            message = "delete network failed."
            return network_pb2.DeleteVNReply(message=message)
        
        # DockerネットワークもIDを元に探してから削除する
        docknet = self.client.networks.get(request.docknetid)
        docknet.remove()

        message = "UUID:" + request.uuid + " deleted."
        return network_pb2.DeleteVNReply(message=message)
    
    def createBridge(self, request, context):
        if self.conn == None:
            message = "conn failed."
            return network_pb2.CreateBridgeReply(message=message)
        
        # wataame-br0に対してブリッジネットワークを作成
        with open('templates/bridge.xml') as f:
            t = string.Template(f.read())
        xmldefine = t.substitute(
            name=request.name,
            uuid=request.uuid,
            interface=self.interface
        )
        print(xmldefine)

        network = self.conn.networkDefineXML(xmldefine)
        if network == None:
            message = "define network failed"
            return network_pb2.CreateBridgeReply(message=message)

        if network.setAutostart(1) != 0:
            message = "set network to autostart failed"
            return network_pb2.CreateBridgeReply(message=message)

        if network.create() != 0:
            message = "create network failed"
            return network_pb2.CreateBridgeReply(message=message)
        
        # LAN内のIPを取得
        ipgetter = ipget.ipget()
        ip = ipgetter.ipaddr(self.interface)
        int = ipaddress.IPv4Interface(ip)
        cidr = int.network.exploded

        # Dockerネットワーク作成
        ipam_pool = docker.types.IPAMPool(subnet=cidr)
        ipam_config = docker.types.IPAMConfig(pool_configs=[ipam_pool])
        docknet = self.client.networks.create(
            request.name+'-docker',
            driver='macvlan',
            ipam=ipam_config,
            options={
                'parent': self.interface
            })

        message = cidr
        return network_pb2.CreateBridgeReply(message=message, docknetid=docknet.id)