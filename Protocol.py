import sys
import socket
import select
import threading
import time

MAX_GLOBAL_PATH = 15

PERIODIC = 3
TIMEOUT = 18
GARBAGE_COLLECTION = 12

routerId = None
inputPorts = []
outputPorts = dict()
inputSockets = []

forwardingTable = dict()


class ForwardingTableEntry:
    def __init__(self, destination, nextHop, weight, port, source):
        self.destination = destination
        self.nextHop = nextHop
        self.weight = weight
        self.timer = time.time()
        self.source = source

    def update(self, nextHop, weight, port, source):
        self.nextHop = nextHop
        self.weight = weight
        self.timer = time.time()
        self.source = source



class ParseIncomingPacket:
    def __init__(self, data):
        self.valid = True
        if len(data) > 24:
            parseHeader(data)
        else:
            self.valid = False

    def parseHeader(self, data):
        self.command = data[0]
        self.version = data[1]

        if (not command in [1, 2]) or (self.version != 2) or (data[2] || data[3] != 0):
            self.valid = False
            return

        if self.command == 0
        self.entries = []
        if (len(data) - 4) % 20 == 0 and (len(data) - 4) / 20 <= 25:
            for i in range(4, len(data), 20):
                entry.append(parseEntry(data[i:i+20]))

    def parseEntry(self, data):
        return None



class RIPOUTPacket:
    VERSION = 2
    AFI = 2

    def __init__(self, command, nextHop, metric):
        self.command = command
        self.version = VERSION
        self.afi = AFI
        self.id = routerId
        self.nextHop = nextHop
        self.metric = metric

    def makePacket():
        idByte = bytearray(routerId)
        nextHopByte = bytearray(nextHop)
        metricByte = bytearray(metric)
        outPacket = bytearray([
                                self.command,
                                self.version,
                                0, 0,
                                self.afi,
                                0, 0,
                                idByte >> 24,
                                idByte >> 16 & 0xFF,
                                idByte >> 8 & 0xFF,
                                idByte & 0xFF,
                                0, 0, 0, 0,
                                nextHopByte >> 24,
                                nextHopByte >> 16 & 0xFF,
                                nextHopByte >> 8 & 0xFF,
                                nextHopByte & 0xFF,
                                metricByte >> 24,
                                metricByte >> 16 & 0xFF,
                                metricByte >> 8 & 0xFF,
                                metricByte & 0xFF
                                ])

def loadConfig(configFileName):
    """
    Process the config file
    """

    global routerId
    global inputPorts
    global outputPorts

    cfg = open(configFileName, "r")
    lines = cfg.readlines()

    for line in lines:
        line = line.split(" ")  # input-ports 6110, 6201, 7345

        # Checks the router ID
        if line[0] == "router-id":
            try:
                id = int(line[1])repository
            except Exception:
                raise Exception("Given router ID is not a number.")

            if id > 0 and id <= 64000:
                routerId = id
            else:
                raise Exception("Invalid router ID")

        # Adds the input ports to the router if it exists.
        # TODO
        #   - Check if doubles
        elif line[0] == 'input-ports':
            ports = []
            for i in range(1, len(line)):
                ports.append(int(line[i].strip(",")))
            for port in ports:
                inputPorts.append(port)

        # Adds input ports
        # TODO
        #   - Check output ports are not input ports
        #   - do something with the ids?
        #   - Check if doubles
        elif line[0] == 'output-ports':
            ports = []
            for i in range(1, len(line)):
                ports.append(line[i].strip(","))
            for port in ports:
                port = port.split('-')
                if len(port) != 3:
                    raise Exception(
                        "Incorrect output port format given. Expected: output-ports port-cost-id"
                    )
                # outputPorts.append((int(port[0]), int(port[1]), int(port[2]))) # Need the router id to check where the port is coming from when sending an update
                # routingTable.append([int(port[0]), int(port[1]), int(port[2])])
                outputPorts[int(port[0])] = int(port[1])


def checkConfig():
    """
    Checks if required info was provided and was correctly parsed
    """

    global routerId
    global inputPorts
    global outputPorts

    if routerId is None:
        raise Exception("Router ID not given")
    if len(inputPorts) == 0:
        raise Exception("No input ports given")
    if len(outputPorts) == 0:
        raise Exception("No output ports given")


def bindUDPPorts():
    global inputPorts
    global outputPorts

    HOST = '127.0.0.1'

    for PORT in inputPorts:
        newSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        newSocket.bind((HOST, PORT))

        inputSockets.append(newSocket)


def updateRoutingTable(newEntry):
    # Needs to check if the id is already in the table
    # if it is, compare the metric then update accordingly
    id = newEntry.destination
    if routingTable[id] is not None:
        entry = routingTable[id]
        if entry.metric > newEntry.metric:
            routingTable[id] = newEntry




# def sendUpdate(id, port):
#     global outputPortsnewEntry
#     # Need to check if what router is being sent to and to not include
#     # routes that that router has sent to this router
#     for i in outputPorts:
#         if i[2] != id:
#             updatePacket = [2, 2, 0, 0, AFI, AFI, 0, 0, id, id, id, id, 0, 0 ,0, 0, next hop, next hop, next hop, next hop, metric, metric, metric, metric]
#             updatePacket = bytearray(updatePacket)
#             conn.sendall(updatePacket)
#     pass


def broadcastUpdate():
    """
    Sends an unsolicited Update message to all neighboring routers
    broadcast these nuts
    Need to check what router being broadcasted to and to not include
    routes that that router has sent to this router
    """
    command = 2
    neighbours = []
    for id in routingTable:
        if routingTable[id].nextHop == routingTable[id].destination:
            neighbours.append(id)

    for router in neighbours:
        toSend = []
        for id in routingTable:
            if id != router:
                if routingTable[id].source != router:
                    toSend.append(id)

        # Need to create a packet to send to "router" that includes the
        # contents of "toSend"
        entryList = []
        for id in toSend:
            forwardingInfo = forwardingTable[id]
            entryList.append(RIPEntry(AFI, forwardingInfo.destination, forwardingInfo.weight))








def main(args):
    if len(args) != 1:
        print(
            f"Invalid number of args. Expected 1, got {len(args)}\nExiting...")
        exit()

    try:
        loadConfig(args[0])
        checkConfig()

        # print(routerId)
        # print(inputPorts)
        # print(outputPorts)

        bindUDPPorts()
    except Exception as e:
        print(e)
        print("\nExiting...")
        exit()

    periodicTime = time.time() + PERIODIC

    try:
        while True:
            readable, _, _ = select.select(
                inputSockets, [], [], periodicTime - time.time())
            if len(readable) == 0:
                broadcastUpdate()

                for entry in forwardingTable:
                    if entry.timer + TIMEOUT + GARBAGE_COLLECTION <= time.time():
                        forwardingTable.pop(forwardingTable[entry].destination)
                periodicTime = time.time() + PERIODIC
            else:
                for inputSocket in readable:
                    # Implement reading of incoming messages
                    pass
    except Exception as e:
        print(e)
        print("\nExiting...")
        exit()



if __name__ == "__main__":
    main(sys.argv[1:])
