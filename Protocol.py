import sys

MAX_GLOBAL_PATH = 15

routerId = None
inputPorts = []
outputPorts = {}


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
                inputPorts.append(port)

        # Adds input ports
        elif line[0] == 'output-ports':
            ports = []
            for i in range(1, len(line)):
                ports.append(int(line[i].strip(",")))
            for port in ports:
                port = port.split('-')
                if len(port) != 3:
                    raise Exception(
                        "Incorrect output port format given. Expected: output-ports port-cost-id")
                outputPorts.update({int(port[0]), int(port[1])})


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


def updateRoutingTable(newEntry):
    pass


def main(args):
    if len(args) != 1:
        print(
            f"Invalid number of args. Expected 1, got {len(args)}\nExiting...")
        exit()

    try:
        loadConfig(args[0])
        checkConfig()
    except Exception as e:
        print(e)
        print("\nExiting...")


if __name__ == "__main__":
    main(sys.argv[1:])
