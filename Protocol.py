import sys
import socket
import select
import time
import random

# TODO:
# Finish the assignment!
# Actually do work
#

MAX_GLOBAL_PATH = 15
VERSION = 2
AFI = 2
HOST = '127.0.0.1'

TIME_SCALE = 0.1

PERIODIC = 30 * TIME_SCALE
TIMEOUT = 180 * TIME_SCALE
GARBAGE_COLLECTION = 300 * TIME_SCALE
TRIGGERED_MIN = 1 * TIME_SCALE
TRIGGERED_MAX = 5 * TIME_SCALE


ROUTERID = None
inputPorts = []
outputPorts = dict()
inputSockets = []
forwardingTable = dict()


class ForwardingTableEntry:
    def __init__(self, destination, nextHop, metric, source):
        self.destination = destination
        self.nextHop = nextHop
        self.metric = metric
        self.changeFlag = False
        self.timer = time.time()
        self.source = source

    def update(self, nextHop, metric, source):
        self.nextHop = nextHop
        self.metric = metric
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
        return bytearray([
            self.command,
            VERSION,
            ROUTERID >> 8,
            ROUTERID & 0xFF
            ])


class RIPEntry:
    def __init__(self, afi, routerID, nextHop, metric):
        self.afi = afi
        self.id = routerID
        self.nextHop = nextHop
        self.metric = metric

    def makeEntry(self):
        return bytearray([
            self.afi >> 8, self.afi & 0xFF,
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

    def printEntry(self):
        print(f"Router id: {self.id}")
        print(f"Next hop: {self.nextHop}")
        print(f"Metric: {self.metric}")
        print('\n')


def loadConfig(configFileName):
    """
    Process the config file
    """
    try:
        global ROUTERID
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
                    ROUTERID = id
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
                                    if connection == port[0]:
                                        double = 1

                            if double == 1:
                                raise Exception(
                                    "Two output ports with the same number"
                                    )
                            else:
                                # entry = ForwardingTableEntry(int(port[2]), int(port[2]), int(port[1]), ROUTERID)
                                # updateForwardingTable(entry)
                                outputPorts[int(port[0])] = (
                                    int(port[1]), int(port[2]))
    except Exception as e:
        exception_type, exception_object, exception_traceback = sys.exc_info()

        print("Line Number: ", exception_traceback.tb_lineno)

        raise e


def checkConfig():
    """
    Checks if required info was provided and was correctly parsed
    """

    global ROUTERID
    global inputPorts
    global outputPorts

    if ROUTERID is None:
        raise Exception("Router ID not given")
    if len(inputPorts) == 0:
        raise Exception("No input ports given")
    if len(outputPorts) == 0:
        raise Exception("No output ports given")


def bindUDPPorts():
    try:
        for PORT in inputPorts:
            newSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            newSocket.bind((HOST, PORT))

            inputSockets.append(newSocket)
    except Exception as e:
        exception_type, exception_object, exception_traceback = sys.exc_info()

        print("Line Number: ", exception_traceback.tb_lineno)
        print(e)


def updateForwardingTable(newEntry):
    # Needs to check if the id is already in the table
    # if it is, compare the metric then update accordingly
    id = newEntry.destination
    if id in forwardingTable:
        entry = forwardingTable[id]
        if entry.metric >= newEntry.metric or entry.nextHop == newEntry.nextHop:
            forwardingTable[id] = newEntry
    else:
        forwardingTable[id] = newEntry


def printForwardingTable():
    """
    Prints out the entire forwarding table
    """
    doubleLine = "====================================================================="

    print(doubleLine)
    print(f"Routing table for {ROUTERID}")
    print(doubleLine)
    # print("| Router ID | Metric | Next Hop |")
    print("{:<10} {:<10} {:<10} {:<10}".format(
        'Router ID', 'Metric', 'Next Hop', 'Timeout in (s)'))

    for entry in forwardingTable:
        entry = forwardingTable[entry]
        print("{:<10} {:<10} {:<10} {:<10.1f}".format(
            entry.destination, entry.metric, entry.nextHop, max(0.0, TIMEOUT - (time.time() - entry.timer))))

    print(doubleLine)
    print('\n')


def ParseIncomingPacket(data):
    """
    Parse incomming packet
    Takes a bytearray as a variable
    """
    try:
        # Check for a valid header
        if len(data) < 4:
            return None

        command = data[0]
        version = data[1]
        originatingRouterID = data[2] << 8 | data[3]

        if (command not in [1, 2]) or (version != 2):
            return None

        if command == 1:
            message = RequestMessage()
        else:
            message = ResponseMessage()
        if (len(data) - 4) % 20 == 0 and (len(data) - 4) // 20 > 0:
            for i in range(4, len(data), 20):
                entryData = data[i: i + 20]
                afi = entryData[0] << 8 | entryData[1]
                routerID = ((entryData[4] << 8 | entryData[5]) << 8 | entryData[6]) << 8 | entryData[7]
                metric = ((entryData[16] << 8 | entryData[17])
                          << 8 | entryData[18]) << 8 | entryData[19]
                # if all(i == 0 for i in entryData[2:4] + entryData[8:16]) :
                message.addEntry(afi, routerID, originatingRouterID, metric)
        return message
    except Exception as e:
        exception_type, exception_object, exception_traceback = sys.exc_info()

        print("Line Number: ", exception_traceback.tb_lineno)

        raise e


def broadcastUpdate():
    """
    Sends an unsolicited Update message to all neighboring routers
    Need to check what router being broadcasted to and to not include
    routes that that router has sent to this router
    """
    try:
        command = 2
        neighbours = []
        # for id in forwardingTable:
        #     if forwardingTable[id].nextHop == forwardingTable[id].destination:
        #         neighbours.append(id)

        for port in outputPorts:
            neighbours.append(port)

        # neighbours needs to be all output ports and shid
        # Don't send forwarding table entries to output ports where routerIDs are the source id and it matches a output port

        # print(neighbours)
        # print("len of ft: ", len(forwardingTable))

        for port in neighbours:
            routerID = outputPorts[port][1]

            toSend = []
            for id in forwardingTable:
                if id != routerID and forwardingTable[id].source != routerID:
                    toSend.append(id)

            entryList = []
            for id in toSend:
                forwardingInfo = forwardingTable[id]
                newEntry = RIPEntry(
                    2, id, forwardingInfo.nextHop, forwardingInfo.metric + outputPorts[port][0])
                entryList.append(newEntry)

            newHeader = RIPHeader(2)
            packet = newHeader.makeHeader()
            # for entry in entryList:
            #     print(entry.id)
            for entry in entryList:
                packet += entry.makeEntry()

            # print(packet)
            # print(len(packet))
            # inputSockets[0].connect((HOST, port))
            inputSockets[0].sendto(packet, (HOST, port))
            # inputSockets[0].close()
    except Exception as e:
        exception_type, exception_object, exception_traceback = sys.exc_info()

        print("Line Number: ", exception_traceback.tb_lineno)

        raise e


def triggeredUpdate():
    """
    Sends an update message to neighbours with a "change flag",
    to let them know there is a dead link
    """
    try:
        command = 2
        neighbours = []

        for port in outputPorts:
            neighbours.append(port)

        # neighbours needs to be all output ports and shid
        # Don't send forwarding table entries to output ports where routerIDs are the source id and it matches a output port

        print("len of ft: ", len(forwardingTable))

        for port in neighbours:
            routerID = outputPorts[port][1]

            toSend = []
            for id in forwardingTable:
                if id != routerID and forwardingTable[id].source != routerID:
                    toSend.append(id)

            entryList = []
            for id in toSend:
                forwardingInfo = forwardingTable[id]
                if forwardingInfo.changeFlag == True:
                    newEntry = RIPEntry(
                        2, id, forwardingInfo.nextHop, 16)
                    entryList.append(newEntry)


            newHeader = RIPHeader(2)
            packet = newHeader.makeHeader()

            for entry in entryList:
                packet += entry.makeEntry()

            inputSockets[0].sendto(packet, (HOST, port))

    except Exception as e:
        exception_type, exception_object, exception_traceback = sys.exc_info()

        print("Line Number: ", exception_traceback.tb_lineno)

        raise e


def manageRequest(message):
    """
    This should never be called
    """
    pass


def manageResponse(message):
    """
    Handles the recieved response message
    """
    try:
        for entry in message.entries:
            # entry.printEntry()
            newFTEntry = ForwardingTableEntry(entry.id, entry.nextHop, entry.metric, entry.nextHop)
            if entry.metric >= 16:
                if entry.id in forwardingTable:
                    forwardingTable.pop(entry.id)
            else:
                updateForwardingTable(newFTEntry)
    except Exception as e:
        exception_type, exception_object, exception_traceback = sys.exc_info()

        print("Line Number: ", exception_traceback.tb_lineno)

        raise e
    printForwardingTable()


def main(args):
    if len(args) != 1:
        print(
            f"Invalid number of args. Expected 1, got {len(args)}\nExiting...")
        exit()

    try:
        loadConfig(args[0])
        checkConfig()

        print(ROUTERID)
        print(inputPorts)
        print(outputPorts)

        bindUDPPorts()

        updateForwardingTable(ForwardingTableEntry(
            ROUTERID, ROUTERID, 0, None))
        forwardingTable[ROUTERID].timer = float('inf')
    except Exception as e:
        exception_type, exception_object, exception_traceback = sys.exc_info()

        print("Line Number: ", exception_traceback.tb_lineno)

        print(e)
        print("\nExiting...")
        exit()

    periodicTime = time.time() + PERIODIC
    randomTime = float("inf")
    triggeredUpdates = False

    printForwardingTable()

    try:
        while True:
            readable, _, _ = select.select(inputSockets, [], [], min(periodicTime - time.time(), randomTime - time.time()))
            if len(readable) == 0:

                if periodicTime - time.time() <= 0:
                    broadcastUpdate()
                    triggeredUpdates = False
                    randomTime = float("inf")
                    periodicTime += PERIODIC

                elif triggeredUpdates:
                    if randomTime - time.time() < 0:
                        triggeredUpdate()
                        triggeredUpdates = False
                        randomTime = float("inf")


                toPop = []
                for entry in forwardingTable:

                    if (TIMEOUT - (time.time() - forwardingTable[entry].timer)) < 0:
                        if not forwardingTable[entry].changeFlag:
                            print(f"Router {entry} is unreachable")
                            forwardingTable[entry].metric = 16
                            forwardingTable[entry].changeFlag = True

                            triggeredUpdates = True
                            randomTime = time.time() + random.uniform(TRIGGERED_MIN,TRIGGERED_MAX) ## UPDATE THIS, ONLY 10% OF VALUE AAAAAAAAAAAAAAAAAAAAAA

                        if GARBAGE_COLLECTION - (time.time() - forwardingTable[entry].timer) < 0:
                            toPop.append(forwardingTable[entry].destination)

                for entry in toPop:
                    forwardingTable.pop(entry)

            else:
                for inputSocket in readable:
                    # Implement reading of incoming messages
                    data, addr = inputSocket.recvfrom(504)
                    message = ParseIncomingPacket(data)
                    # print("Valid: ", message.valid)
                    # print("Command: ", message.command)
                    # print("Num Entries: ", len(message.entries))

                    # for entry in message.entries:
                    #     print(entry.id)
                    #     print(entry.metric)
                    if message.command == 1:
                        manageRequest(message)
                    elif message.command == 2:
                        manageResponse(message)

            # printForwardingTable()

    except Exception as e:
        exception_type, exception_object, exception_traceback = sys.exc_info()

        print("Line Number: ", exception_traceback.tb_lineno)

        print(e)
        print("\nExiting...")
        exit()


if __name__ == "__main__":
    main(sys.argv[1:])
