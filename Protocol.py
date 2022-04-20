import sys, socket, select, threading

MAX_GLOBAL_PATH = 15

timer = threading.timer()

routerId = None
inputPorts = []
outputPorts = []
routingTable = []


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
                outputPorts.append((int(port[0]), int(port[1]), int(port[2]))) # Need the router id to check where the port is coming from when sending an update
                routingTable.append([int(port[0]), int(port[1]), int(port[2])])


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


def updateRoutingTable(newEntry):
    # Needs to check if the port is already in the table
    # if it is, compare the metric then update accordingly
    
    global routingTable

    for route in routingTable:
        if route[0]



def sendUpdate(id, port):
    global outputPorts
    # Need to check if what router is being sent to and to not include
    # routes that that router has sent to this router
    for i in outputPorts:
        if i[2] != id:
            updatePacket = [2, 2, 0, 0, AFI, AFI, 0, 0, id, id, id, id, 0, 0 ,0, 0, next hop, next hop, next hop, next hop, metric, metric, metric, metric]
            updatePacket = bytearray(updatePacket)
            conn.sendall(updatePacket)
    pass


def parseUpdate():
    pass



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


    try:
        while true:
            break;
    except Exception as e:
        print(e)
        print("\nExiting...")
        exit()



if __name__ == "__main__":
    main(sys.argv[1:])
