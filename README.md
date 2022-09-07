First, run following commands.

```sh
$ sudo apt install network-manager
$ nmcli con add type bridge ifname wataame-br0
# If you wanna set bridge to eth0
$ nmcli con add type bridge-slave ifname eth0 master wataame-br0
$ nmcli con up bridge-slave-eth0
```