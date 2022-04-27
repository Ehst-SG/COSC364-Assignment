import sys
import socket
import select
import time

# TODO:
#

MAX_GLOBAL_PATH = 15
VERSION = 2
AFI = 2
HOST = '127.0.0.1'

PERIODIC = 3
TIMEOUT = 18
GARBAGE_COLLECTION = 12

routerId = None
inputPorts = []
outputPorts = dict()
inputSockets = []

forwardingTable = dict()


class ForwardingTableEntry:
    def __init__(self, destination, nextHop, weight, source):
        self.destination = destination
        self.nextHop = nextHop
        self.weight = weight
        self.timer = time.time()
        self.source = source

    def update(self, nextHop, weight, source):
        self.nextHop = nextHop
        self.weight = weight
        self.timer = time.time()
        self.source = source


class RequestMessage:
    def __init__(self):
        self.valid = True
        self.command = 1
        self.version = 2
        self.entries = []

    def addEntry(self, afi, routerID, nextHop, metric):
        self.entries.append(RIPEntry(afi, routerID, nextHop, metric))


class ResponseMessage:
    def __init__(self):
        self.valid = True
        self.command = 2
        self.version = 2
        self.entries = []

    def addEntry(self, afi, routerID, nextHop, metric):
        self.entries.append(RIPEntry(afi, routerID, nextHop, metric))


class RIPHeader:

    def __init__(self, command):
        self.command = command

    def makeHeader(self):
        outPacket = bytearray([
            self.command,
            VERSION,
            0, 0
            ])


class RIPEntry:
    def __init__(self, afi, routerID, nextHop, metric):
        self.afi = afi
        self.id = routerId
        self.nextHop = nextHop
        self.metric = metric

    def makeEntry(self):
        entry = bytearray([

                            self.afi,
                            0, 0,
                            self.id >> 24,
                            self.id >> 16 & 0xFF,
                            self.id >> 8 & 0xFF,
                            self.id & 0xFF,
                            0, 0, 0, 0,
                            self.nextHop >> 24,
                            self.nextHop >> 16 & 0xFF,
                            self.nextHop >> 8 & 0xFF,
                            self.nextHop & 0xFF,
                            self.metric >> 24,
                            self.metric >> 16 & 0xFF,
                            self.metric >> 8 & 0xFF,
                            self.metric & 0xFF
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
                id = int(line[1])
            except Exception:
                raise Exception("Given router ID is not a number.")

            if id > 0 and id <= 64000:
                routerId = id
            else:
                raise Exception("Invalid router ID")

        # Adds the input ports to the router if it exists.
        elif line[0] == 'input-ports':
            ports = []
            for i in range(1, len(line)):
                ports.append(int(line[i].strip(",")))
            for port in ports:
                if port in inputPorts:
                    raise Exception(
                        "Two input ports with the same number"
                    )
                else:
                    inputPorts.append(port)

        # Adds input ports
        # TODO
        #   - do something with the ids?
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
                else:

                    if port[0] in inputPorts:
                        raise Exception(
                            "Tried to add an input port that is already used as an output port"
                            )

                    else:

                        # Checks that there are no ports using the same number in the output ports
                        double = 0
                        for router in outputPorts:
                            for connection in outputPorts[router]:
                                if connection[0] == port[0]:
                                    double = 1

                        if double == 1:
                            raise Exception(
                                "Two output ports with the same number"
                                )
                        else:
                            outputPorts[int(port[2])] = (
                                int(port[0]), int(port[1]))


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
    for PORT in inputPorts:
        newSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        newSocket.bind((HOST, PORT))

        inputSockets.append(newSocket)


def updateforwardingTable(newEntry):
    # Needs to check if the id is already in the table
    # if it is, compare the metric then update accordingly
    id = newEntry.destination
    if forwardingTable[id] is not None:
        entry = forwardingTable[id]
        if entry.metric > newEntry.metric:
            forwardingTable[id] = newEntry


def ParseIncomingPacket(data):
    if len(data) < 4:
        return None

    command = data[0]
    version = data[1]

    if (command not in [1, 2]) or (version != 2) or (data[2] | data[3] != 0):
        return None

    if command == 0:
        message = RequestMessage()
        if (len(data) - 4) % 20 == 0 and (len(data) - 4) // 20 > 0:
            for i in range(4, len(data), 20):
                entryData = data[i, i + 20]
                afi = entryData[0] << 8 | entryData[1]
                routerID = ((entryData[4] << 8 | entryData[5])
                            << 8 | entryData[6]) << 8 | entryData[7]
                nextHop = 0  # ?????
                metric = ((entryData[16] << 8 | entryData[17])
                          << 8 | entryData[18]) << 8 | entryData[19]
                message.addEntry(afi, routerID, nextHop, metric)
    elif command == 1:
        return ResponseMessage(data)
    else:
        return None


def broadcastUpdate():
    """
    Sends an unsolicited Update message to all neighboring routers
    Need to check what router being broadcasted to and to not include
    routes that that router has sent to this router
    """
    command = 2
    neighbours = []
    for id in forwardingTable:
        if forwardingTable[id].nextHop == forwardingTable[id].destination:
            neighbours.append(id)

    for router in neighbours:
        toSend = []
        for id in forwardingTable:
            if id != router:
                if forwardingTable[id].source != router:
                    toSend.append(id)

        entryList = []
        for id in toSend:
            forwardingInfo = forwardingTable[id]
            newEntry = RIPEntry(forwardingInfo.nextHop, forwardingInfo.metric)
            entryList.append(newEntry)

        newHeader = RIPHeader(2)
        packet = newHeader.makeHeader()
        for entry in entryList:
            packet += entry

        inputPorts[0].connect((HOST, outputPorts[router][0]))
        inputPorts[0].sendall(packet)
        inputPorts[0].close()


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
