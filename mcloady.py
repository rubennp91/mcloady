import configparser
import os
from mcrcon import MCRcon
from time import sleep
from datetime import timedelta


def mcrcon(config):
    """
    Establish connection to mcrcon using MCRcon
    return the object mcr so commands can be
    sent from other functions
    """
    mcr = MCRcon(config['RCON']['server_ip'], config['RCON']['password'])
    try:
        mcr.connect()
    except Exception:
        print("Could not connect to RCON. Check the following:\n \
                - Server is online\n \
                - enable-rcon = true in server.properties\n \
                - Password and IP are the same in server.properties and \
                    config.ini")
        exit()
    return mcr


def player_spawn(config, mcr):
    """
    If carpet mod is to be used (set to 'yes' in
    configuration), spawn a player using it.
    Otherwise set the name to player to be used
    as the one set in configuration.
    """
    player = config['PLAYER']['name']
    use_carpet = config['PLAYER']['use_carpet']
    if 'y' in use_carpet.lower():
        resp = mcr.command("/player spawn " + player)
        print(resp)
        resp = mcr.command("/gamemode spectator " + player)
        print(resp)
    else:
        resp = mcr.command("/gamemode spectator " + player)
        print(resp)
    return player


def read_last_tp(config):
    """
    If program was executed previously, a 'last_tp.txt'
    file will exist. Use the coordinates inside to
    start iterating from there. If it doesnt exist,
    set the initial coordinates using the parameters
    in the configuration file.
    """
    save_file = config['FILE']['last_tp']
    if not os.path.isfile(save_file):
        altitude = config['PARAMETERS']['altitude']
        # X, Z, dX, dZ, start_i
        last_tp = [0, 0, 0, -1, 0]
        with open(save_file, 'w') as f:
            f.write(','.join(str(x) for x in last_tp))
    else:
        with open(save_file, 'r') as f:
            last_tp = f.read()
        last_tp = last_tp.split(',')
    return last_tp, save_file


def send_tp(mcr, x, y, z, a, b, player):
    """
    Send the telepor command using mcr. 'x', 'y' 'z'
    are cartesian coordinates, 'a' and 'b' are angles.
    """
    tp_parameters = [str(i) for i in ["/tp", player, x, y, z, a, b]]
    mc_command = ' '.join(tp_parameters)
    resp = mcr.command(mc_command)
    return resp


def generate_node(mcr, x, y, z, first_wait, second_wait, player):
    """
    Generate a node using the coordinates and angles. Take in the
    Minecraft RCON object, the coordinates, the primary and secondary
    wait times, and the player object.
    """
    send_tp(mcr, x, y, z, -90, 20, player)
    sleep(first_wait)
    send_tp(mcr, x, y, z, 0, 20, player)
    sleep(second_wait)
    send_tp(mcr, x, y, z, 90, 20, player)
    sleep(second_wait)
    send_tp(mcr, x, y, z, 180, 20, player)
    sleep(second_wait)


def calculate_time_remaining(i, normalized_nodes, first_wait, second_wait):
    """
    Function to calculate the time remaining on the script.
    This can be done by checking the iteration number of
    and the total number of nodes to be generated. Subtracting
    the two gives the increments left to be generated. Multiplying by the
    time required for each node to be generated gives the time left.
    """
    total_iterations_left = normalized_nodes - i
    time_per_iteration = first_wait + second_wait*3

    total_time_remaining = total_iterations_left*time_per_iteration

    return str(timedelta(seconds=total_time_remaining))


def main(config):
    """
    The main function is used to read config, start
    up the MCRcon connection as well as to iterate
    between all the positions and save those to a file.
    """
    last_tp, save_file = read_last_tp(config)
    mcr = mcrcon(config)
    player = player_spawn(config, mcr)

    radius = int(config['PARAMETERS']['radius'])
    increments = int(config['PARAMETERS']['increments'])
    y = int(config['PARAMETERS']['altitude'])
    first_wait = int(config['PARAMETERS']['first_wait'])
    second_wait = int(config['PARAMETERS']['second_wait'])

    # Load last saved tp coordinates, next increment, and current iteration.
    x = int(last_tp[0])
    z = int(last_tp[1])
    dx = int(last_tp[2])
    dz = int(last_tp[3])
    start_i = int(last_tp[4])

    # 2D Spiral Algorithm
    # https://stackoverflow.com/questions/398299/looping-in-a-spiral
    normalized_radius = radius / increments
    normalized_diameter = normalized_radius * 2
    normalized_nodes = round(normalized_diameter ** 2)
    iterator = start_i

    while iterator < normalized_nodes:
        if (-normalized_radius <= x <= normalized_radius) and \
           (-normalized_radius <= z <= normalized_radius):
            actual_x = int(x * increments)
            actual_z = int(z * increments)
            generate_node(mcr,
                          actual_x,
                          y,
                          actual_z,
                          first_wait,
                          second_wait,
                          player)

            with open(save_file, 'w') as f:
                # Write position and next step to file
                f.write("{0},{1},{2},{3},{4}\n".format(x, z, dx, dz, iterator))

            remaining_time = calculate_time_remaining(iterator,
                                                      normalized_nodes,
                                                      first_wait,
                                                      second_wait)

            print("Player teleported to position:", str(actual_x), str(y), str(actual_z))
            print("Player teleported to normalized position:", x, str(y), z)
            print("{0}/{1} nodes completed. {2} left."
                  .format(iterator, normalized_nodes,
                          (normalized_nodes - iterator)))
            print("Approximate remaining time:", remaining_time)

            if x == z or (x < 0 and x == -z) or (x > 0 and x == 1-z):
                dx, dz = -dz, dx

            x, z = x+dx, z+dz

        iterator += 1

    mcr.disconnect()
    print("All finished!")


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read("config.ini")
    attempts = 0

    while attempts < 3:
        try:
            main(config)
        # Exit if Ctrl+C or Del is pressed
        except KeyboardInterrupt:
            print("\nExiting...")
            exit(0)

        # Reattempt 3 times if MCRcon fails
        # Exit after third time
        except mcrcon.exceptions.MCRconException as e:
            print("\nMCRcon Error: ", e)
            if attempts < 3:
                attempts += 1
                print("Will reattempt in 5 seconds...")
                sleep(5)
            else:
                print("Failed 3 times. Exiting...")
                exit(1)
