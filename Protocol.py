import sys

MAX_GLOBAL_PATH = 15
ROUTER_LIST = []


class Router:
    def __init__(self, id):
        self.id = id
        self.input_ports = []
        self.output_ports = []
    def addInputPort(self, port):
        self.input_ports.append( port )
    def addOutputPort(self, port, cost):
        self.output_ports.append( (port, cost) )




def loadConfig(configFileName):
    """
    Process the config file
    """

    cfg = open(configFileName, "r")
    lines = cfg.readlines()
    count = 0


    for line in lines:
        line = line.split(" ") #input-ports 6110, 6201, 7345

        # Checks the router ID
        if line[0] == "router-id":
            try:
                id = int(line[1])
            except:
                raise Exception("Given router ID is not a number.")

            if lid > 0 and id <= 64000:
                if routerIdExists(id):
                    newRouter = Router(id)
                    ROUTER_LIST.append(newRouter)
                else:
                    raise Exception(f"Router already with ID {id} already exists")
            else:
                raise Exception("Invalid router ID")


        # Adds the input ports to the router if it exists.
        else if line[0] == 'input-ports':
            ports = []
            for i in range(1, len(line)):
                ports.append(int(line[i].strip(",")))
            for port in ports:
                addInputPort(port)

        else if line[0] == 'output-ports':
            ports = []
            for i in range(1, len(line)):
                ports.append(int(line[i].strip(",")))
            for port in ports:
                port = port.split('-')


def parseConfig(file):
    pass


def routerIdExists(id):
    """
    Returns true if
    """
    for router in ROUTER_LIST:
        if router.id == id:
            return true
    return false

def updateRoutingTable(newEntry):
    pass






def main(args):
    if len(args) != 1:
        print(f`Invalid number of args. Expected 1, got {len(args)}\nExiting...`)
        exit()

    try:
        loadConfig(args[0])
    except Exception as e:
        print(e)
        print("\nExiting...")




if __name__ == "__main__":
    main(sys.argv[1:])
