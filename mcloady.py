from mcrcon import MCRcon
from time import sleep
import configparser
import os
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
                - Password and IP are the same in server.properties and config.ini")
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
        radius = config['PARAMETERS']['radius']
        altitude = config['PARAMETERS']['altitude']
        last_tp = [-abs(int(radius)), int(altitude), -abs(int(radius))]
        with open(save_file, 'w') as f:
            f.write(str(last_tp[0]) + "," + str(last_tp[1]) + "," + str(last_tp[2]))
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
    resp = mcr.command("/tp " + player + " " + str(x) + " " +
                       str(y) + " " + str(z) + " " + str(a) + " " + str(b))
    return resp


def calculate_time_remaining(i, j, radius, increments, first_wait, second_wait):
    """
    Function to calculate the time remaining on the script.
    This can be done by checking the current position of
    the player against the total radius.
    i = number of iterations passed in the x axis
    j = number of iterations passed in the z axis
    """
    number_of_iterations_per_row = (radius*2)/increments
    remaining_iterations_in_current_row = \
        number_of_iterations_per_row - j

    # Minus one because we need to count out the current row
    remaining_total_rows = number_of_iterations_per_row \
        - i-1
    time_per_iteration = first_wait + second_wait*3

    total_time_remaining = \
        remaining_iterations_in_current_row*time_per_iteration + \
        remaining_total_rows*number_of_iterations_per_row*time_per_iteration

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

    x = int(last_tp[0])
    z = int(last_tp[2])

    for i, x in enumerate(range(x, radius+increments, increments)):
        for j, z in enumerate(range(z, radius+increments, increments)):
            send_tp(mcr, x, y, z, -90, 20, player)
            sleep(first_wait)
            send_tp(mcr, x, y, z, 0, 20, player)
            sleep(second_wait)
            send_tp(mcr, x, y, z, 90, 20, player)
            sleep(second_wait)
            send_tp(mcr, x, y, z, 180, 20, player)
            sleep(second_wait)
            with open(save_file, 'w') as f:
                f.write(str(x) + "," + str(y) + "," + str(z))
            remaining_time = calculate_time_remaining(i,
                                                      j,
                                                      radius,
                                                      increments,
                                                      first_wait,
                                                      second_wait)
            print("Player teleported to position:", str(x), str(y), str(z))
            print("Approximate remaining time:", remaining_time)

        z = int(-abs(radius))
    mcr.disconnect()
    print("All finished!")


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read("config.ini")
    main(config)
