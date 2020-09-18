DESCRIPTION = """
Takes a halo stat .json input and updates a database.json.
Then outputs an html file with the stats
Written by: ChieFsteR
"""

import json
import argparse
import os
import re
from tabulate import tabulate

DATABASE = '.\\database.json'

PLAYER_DICTIONARY = {
    'DISCORD'     : None,
    'KILLS'       : 0,
    'DEATHS'      : 0,
    'ASSISTS'     : 0,
    'SCORE'       : 0,
    'TOTAL_SHOTS' : 0,
    'SHOTS_REG'   : 0,
    'WIN'         : 0,
    'LOSS'        : 0
}

PLAYER_KEYS = ['DISCORD', 'KILLS', 'DEATHS', 'ASSISTS', 'SCORE', 'TOTAL_SHOTS', 'SHOTS_REG', 'WIN', 'LOSS']

def read(data):
    """
    Read the halo json file and parse it to a more desireable format
    """
    #DEBUG: print(json.dumps(data, indent = 4, sort_keys=True))

    players = {}

    for UUID in data.keys():
        # if "discord" value is shorter than 4 characters then the stat update should be ignored for the UUID
        if len(data[UUID]['discord']) >= 4:
            #create a new player
            player = {}
            player['DISCORD'] = data[UUID]['discord']
            player['KILLS'] = data[UUID]['kills']
            player['DEATHS'] = data[UUID]['deaths']
            player['ASSISTS'] = data[UUID]['assists']
            if data[UUID]['mode'] == 'ctf':
                player['SCORE'] = int(data[UUID]['score'])*5
            else:
                player['SCORE'] = int(data[UUID]['score'])/2
            # read all weapons and add the total shots vs. shots reg
            weapons = re.findall(r'\[\d+, \d+\]', str(data[UUID]))
            player['TOTAL_SHOTS'] = 0
            player['SHOTS_REG'] = 0
            for weapon in weapons:
                #convert string representation of a list to a python list object
                weapon_list = weapon.strip('][').split(', ')
                player['TOTAL_SHOTS'] = player['TOTAL_SHOTS'] + int(weapon_list[0])
                player['SHOTS_REG'] = player['SHOTS_REG'] + int(weapon_list[1])
            if int(data[UUID]['won']) > 0:
                player['WIN'] = 1
                player['LOSS'] = 0
            else:
                player['WIN'] = 0
                player['LOSS'] = 1
            players[UUID] = player

    return players

def update(players, database=DATABASE):
    """Update players in the players database"""

    db_players = {}

    try:
        #open the database if it exists
        with open(database) as f:
            db_players = json.load(f)
    except Exception:
        #create a new database if one doesn't exist
        with open(database, 'w') as f: 
            db_players = {}

    for player_key in players.keys():
        #let's test to see if the player UUID exists
        try:
            db_players[player_key]
        except KeyError:
            #if the player doesn't exist, create them
            db_players[player_key] = players[player_key]
        else:
            #if the player does exist, update their data
            for key in PLAYER_KEYS:
                if key == 'DISCORD':
                    db_players[player_key][key] = int(players[player_key][key])
                else:
                    db_players[player_key][key] = int(db_players[player_key][key]) + int(players[player_key][key])

    #save the database
    with open(database, 'w') as f:
        json.dump(db_players, f, indent = 4, sort_keys=True)

def player_rank(player):
    """Calculate a rank value for a player"""

    return float(((player['WIN'] * 25.0) + player['SCORE']) - (player['LOSS'] * 10.0))

def output_html(database):
    """Take a database file and create an HTML file"""

    db_players = {}
    with open(database) as f:
        db_players = json.load(f)

    #first, rank the players
    ranks = []
    for db_player_key in db_players.keys():
        rank = player_rank(db_players[db_player_key])
        ranks.append((rank, db_player_key))

    #second, sort the players by highest rank first
    ranks.sort(key=lambda ranks: ranks[0], reverse=True)

    #third, create a list of players to output
    player_output = [PLAYER_KEYS]
    for rank in ranks:
        player = []
        for key in PLAYER_KEYS:
            player.append(db_players[rank[1]][key])
        player_output.append(player)

    #fourth, output an html file
    with open('stats.html', 'w') as f:
        f.write(tabulate(player_output, tablefmt='html'))

def main():
    """main program entry point"""

    parser = argparse.ArgumentParser(description=DESCRIPTION)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-f', '--file', help='The data is in a file')
    group.add_argument('-a', '--arg', help='The data is a command line argument')
    args = parser.parse_args()

    players = None
    if args.file is not None:
        with open(args.file) as f:
            data = json.load(f)
            players = read(data)
    elif args.arg is not None:
        players = read(json.loads(args.arg))

    update(players)
    output_html(DATABASE)


if __name__=="__main__":
    main()
