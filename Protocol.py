import sys
import socket
import select
import time
import random

# TODO:
# Finish the assignment!
# Actually do work
# ADD TIMERS TO CONFIG  - DONE
# Make recieving a 16 metric trigger triggered update  - DONE
# make shid tidy
# delete the todo list

MAX_GLOBAL_PATH = 16
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
portMetrics = dict()
inputSockets = []
forwardingTable = dict()


class ForwardingTableEntry:
    """
    Represents a single entry in the forwarding table
    """

    def __init__(self, destination, nextHop, metric, source):
        self.destination = destination
        self.nextHop = nextHop
        self.metric = metric
        self.changeFlag = False
        self.source = source
        if metric < MAX_GLOBAL_PATH:
            self.timer = time.time()
        else:
            self.timer = time.time() - TIMEOUT

    def update(self, nextHop, metric, source):
        self.nextHop = nextHop
        self.metric = metric
        self.source = source
        if metric < MAX_GLOBAL_PATH:
            self.timer = time.time()
        else:
            self.timer = time.time() - TIMEOUT


class RIPMessage:
    """
    Represents a RIP Message
    """

    def __init__(self, command, version, source):
        self.valid = True
        self.header = RIPHeader(command, version, source)
        self.entries = []

    def addEntry(self, afi, routerID, metric):
        self.entries.append(RIPEntry(afi, routerID, metric))

    def makePacket(self):
        packet = self.header.makeHeader()
        for entry in self.entries:
            packet += entry.makeEntry()
        return packet


class RIPHeader:
    """
    Represents a RIP Header
    """

    def __init__(self, command, version, source):
        self.command = command
        self.version = version
        self.source = source

    def makeHeader(self):
        return bytearray([
            self.command,
            self.version,
            self.source >> 8,
            self.source & 0xFF
            ])


class RIPEntry:
    """
    Represents a single RIP entry
    """

    def __init__(self, afi, routerID, metric):
        self.afi = afi
        self.id = routerID
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
            0, 0, 0, 0,
            self.metric >> 24,
            self.metric >> 16 & 0xFF,
            self.metric >> 8 & 0xFF,
            self.metric & 0xFF
            ])


def loadConfig(configFileName):
    """
    Process the config file and tests the given information to make sure that
    it is all correct.
    """
    global ROUTERID
    global inputPorts
    global outputPorts
    global portMetrics
    global TIME_SCALE

    try:
        cfg = open(configFileName, "r")
        lines = cfg.readlines()

        for line in lines:
            line = line.split(" ")

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
                for portEntry in ports:
                    if portEntry in inputPorts:
                        raise Exception(
                            "Two input ports with the same number")
                    else:
                        inputPorts.append(portEntry)

            # Adds output ports
            elif line[0] == 'output-ports':
                ports = []

                for i in range(1, len(line)):
                    ports.append(line[i].strip(","))

                for portEntry in ports:
                    portEntry = portEntry.split('-')
                    if len(portEntry) != 3:
                        raise Exception(
                            "Incorrect output port format given.\n"
                            + "Expected: output-ports port-cost-id")
                    else:
                        if portEntry[0] in inputPorts:
                            raise Exception(
                                "Tried to add an input port that is already used as an output port")
                        else:
                            # Checks that there are no ports using the same number in the output ports
                            hasDouble = False
                            for router in outputPorts:
                                if router == portEntry[0]:
                                    hasDouble = 1

                            if hasDouble == 1:
                                raise Exception(
                                    "Two output ports with the same number"
                                    )
                            else:
                                outputPorts[int(portEntry[0])] = int(
                                    portEntry[2])
                                portMetrics[int(portEntry[2])] = int(
                                    portEntry[1])
            elif line[0] == 'timer-scale':
                if len(line) != 2:
                    raise Exception(
                        "Incorrect timer-scale format given.\n"
                        + "Expected: timer-scale float")
                try:
                    TIME_SCALE = float(line[1])
                except ValueError:
                    raise Exception(
                        "Given timer-scale value is not a valid float.")

    except Exception as e:
        raise e


def checkConfig():
    """
    Checks if required info was provided and was correctly parsed
    """

    if ROUTERID is None:
        raise Exception("Router ID not given")
    if len(inputPorts) == 0:
        raise Exception("No input ports given")
    if len(outputPorts) == 0:
        raise Exception("No output ports given")


def bindUDPPorts():
    """
    Creates UDP sockets and binds them to the input ports
    """
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
    """
    Needs to check if the id is already in the table
    if it is, compare the metric then update accordingly
    """
    id = newEntry.destination
    if id in forwardingTable:
        entry = forwardingTable[id]
        if entry.metric > newEntry.metric or entry.nextHop == newEntry.nextHop:
            if entry.nextHop in forwardingTable:
                forwardingTable[id].update(
                    newEntry.nextHop, newEntry.metric, newEntry.source)
    else:
        forwardingTable[id] = newEntry


def printForwardingTable():
    """
    Prints out the entire forwarding table
    """
    doubleLine = "=" * 60

    print(doubleLine)
    print(f"Routing table for Router {ROUTERID}")
    print(doubleLine)
    # print("| Router ID | Metric | Next Hop |")
    print("{:<10} {:<10} {:<10} {:<10}".format(
        'Router ID', 'Metric', 'Next Hop', 'Timeout in (s)'))

    sortedTable = [i for i in forwardingTable]
    sortedTable.sort()
    for entry in sortedTable:
        entry = forwardingTable[entry]
        print("{:<10} {:<10} {:<10} {:<10.1f}".format(
            entry.destination, entry.metric, entry.nextHop, max(0.0, TIMEOUT - (time.time() - entry.timer))))

    print(doubleLine + "\n")


def broadcastUpdate(bType):
    """
    Sends an update message to all neighboring routers.
    bType, either B or T, determines whether or not the update
    type is a unsolicited broadcast update or a triggered update
    caused by a link failing.
    """
    try:
        command = 2
        afi = 2
        neighbours = []

        for port in outputPorts:
            neighbours.append(port)

        for port in neighbours:
            routerID = outputPorts[port]

            toSend = []
            for id in forwardingTable:
                if id != routerID and forwardingTable[id].source != routerID:
                    toSend.append(id)

            updateMessage = RIPMessage(command, VERSION, ROUTERID)

            for id in toSend:
                forwardingInfo = forwardingTable[id]

                if bType == 'T':
                    if forwardingInfo.changeFlag:
                        updateMessage.addEntry(afi, id, MAX_GLOBAL_PATH)

                elif bType == 'B':
                    updateMessage.addEntry(afi, id, forwardingInfo.metric)

            packet = updateMessage.makePacket()

            inputSockets[0].sendto(packet, (HOST, port))

    except Exception as e:
        exception_type, exception_object, exception_traceback = sys.exc_info()

        print("Line Number: ", exception_traceback.tb_lineno)

        raise e


def parseIncomingPacket(data):
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
            message = RIPMessage(1, VERSION, originatingRouterID)
        else:
            message = RIPMessage(2, VERSION, originatingRouterID)
        if (len(data) - 4) % 20 == 0 and (len(data) - 4) // 20 > 0:
            for i in range(4, len(data), 20):
                entryData = data[i: i + 20]
                afi = entryData[0] << 8 | entryData[1]
                routerID = ((entryData[4] << 8 | entryData[5])
                            << 8 | entryData[6]) << 8 | entryData[7]
                metric = ((entryData[16] << 8 | entryData[17])
                          << 8 | entryData[18]) << 8 | entryData[19]
                if all(j == 0 for j in (entryData[2:4] + entryData[8:16])) and metric <= MAX_GLOBAL_PATH:
                    message.addEntry(
                        afi, routerID, metric)
        return message
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
            if entry.metric == MAX_GLOBAL_PATH:
                newFTEntry = ForwardingTableEntry(
                    entry.id, message.header.source, entry.metric, message.header.source)
                newFTEntry.changeFlag = True
            else:
                newFTEntry = ForwardingTableEntry(
                    entry.id, message.header.source, entry.metric + portMetrics[message.header.source], message.header.source)

            if newFTEntry.metric < MAX_GLOBAL_PATH:
                updateForwardingTable(newFTEntry)
            elif entry.metric == MAX_GLOBAL_PATH and newFTEntry.destination in forwardingTable and newFTEntry.source == forwardingTable[entry.id].source:
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
        bindUDPPorts()

        print("Router ID: ", ROUTERID)
        print("Listening on ports: ", ", ".join(
            [str(int) for int in inputPorts]))
        print("Outputting to ports: ", ", ".join(
            [str(int) for int in outputPorts]))

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
            readable, _, _ = select.select(inputSockets, [], [], min(
                periodicTime - time.time(), randomTime - time.time()))
            if len(readable) == 0:

                if periodicTime - time.time() <= 0:
                    broadcastUpdate('B')
                    triggeredUpdates = False
                    randomTime = float("inf")
                    periodicTime += PERIODIC

                elif triggeredUpdates and randomTime - time.time() <= 0:
                    broadcastUpdate('T')
                    triggeredUpdates = False
                    randomTime = float("inf")

            else:
                for inputSocket in readable:
                    # Implement reading of incoming messages
                    data, addr = inputSocket.recvfrom(504)
                    message = parseIncomingPacket(data)

                    if message.header.command == 1:
                        manageRequest(message)
                    elif message.header.command == 2:
                        manageResponse(message)

            toPop = []
            for entry in forwardingTable:
                if (TIMEOUT - (time.time() - forwardingTable[entry].timer)) <= 0:
                    if not forwardingTable[entry].changeFlag:
                        print(f"Router {entry} is unreachable")
                        forwardingTable[entry].metric = 16
                        forwardingTable[entry].changeFlag = True

                        triggeredUpdates = True
                        randomTime = time.time() + random.uniform(TRIGGERED_MIN, TRIGGERED_MAX)

                    if GARBAGE_COLLECTION - (time.time() - forwardingTable[entry].timer) <= 0:
                        toPop.append(forwardingTable[entry].destination)

            for entry in toPop:
                forwardingTable.pop(entry)

    except Exception as e:
        exception_type, exception_object, exception_traceback = sys.exc_info()

        print("Line Number: ", exception_traceback.tb_lineno)

        print(e)
        print("\nExiting...")
        exit()


if __name__ == "__main__":
    main(sys.argv[1:])

#hello
#hello
#hello
#hello
#hello
#hello
