#!/usr/bin/env python

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

#HTML_PAGE = 'C:\\xampp\\htdocs\\index.html'
HTML_PAGE = '.\\index.html'
DATABASE = '.\\database.json'

PLAYER_KEYS = ['NAME', 'CTF_SCORE', 'SLAYER_SCORE', 'WIN', 'LOSS', 'KILLS', 'DEATHS', 'ASSISTS', 'TOTAL_SHOTS', 'SHOTS_REG']

HTML_STATS = """
<html>
<head>
<style>
h1 {text-align: center;}
p {text-align: center;}
div {text-align: center;}
</style>
<title>Halo Statistics</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<h1><center>Halo Statistics</center></h1>
%s
</body>
<footer>
<p>Designed by: ChieFsteR & Devieth</p>
</footer>
</html>
"""

def read(data):
    """
    Read the halo json file and parse it to a more desireable format
    """
    #DEBUG: print(json.dumps(data, indent = 4, sort_keys=True))

    players = {}

    for UUID in data.keys():
        #create a new player
        player = {}
        player['NAME'] = data[UUID]['name']
        player['DISCORD'] = data[UUID]['discord']
        player['KILLS'] = data[UUID]['kills']
        player['DEATHS'] = data[UUID]['deaths']
        player['ASSISTS'] = data[UUID]['assists']
        if data[UUID]['mode'] == 'ctf':
            player['CTF_SCORE'] = int(data[UUID]['score'])
            player['SLAYER_SCORE'] = 0
        else:
            player['CTF_SCORE'] = 0
            player['SLAYER_SCORE'] = int(data[UUID]['score'])
        # read all weapons and add the total shots vs. shots reg
        weapons = re.findall(r'\[\d+,.*?\d+\]', str(data[UUID]))
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

    for uuid in players.keys():
        #let's test to see if the player UUID exists
        try:
            db_players[uuid]
        except KeyError:
            #if the player doesn't exist, create them
            db_players[uuid] = players[uuid]
        else:
            #if the player does exist, update their data
            db_players[uuid]['DISCORD'] = players[uuid]['DISCORD']
            for key in PLAYER_KEYS:
                if ((key == 'DISCORD') or (key == 'NAME')):
                    db_players[uuid][key] = players[uuid][key]
                else:
                    db_players[uuid][key] = int(db_players[uuid][key]) + int(players[uuid][key])

    #save the database
    with open(database, 'w') as f:
        json.dump(db_players, f, indent = 4, sort_keys=True)

def player_rank(player):
    """Calculate a rank value for a player"""

    rank = float(((player['WIN'] * 25.0) + (player['CTF_SCORE'] * 5.0) + (player['SLAYER_SCORE'] / 2.0)) - (player['LOSS'] * 30.0))
    if rank < 0:
        rank = 0
    return rank

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

    #third, create a list of player stats to output
    player_output = []
    for rank in ranks:
        player = []
        player.append(rank[1])  #uuid are at element 1
        player.append(rank[0])  #ranks are at element 0
        player.append(db_players[rank[1]]['NAME'])
        player.append(db_players[rank[1]]['CTF_SCORE'])
        player.append(db_players[rank[1]]['SLAYER_SCORE'])
        player.append(db_players[rank[1]]['WIN'])
        player.append(db_players[rank[1]]['LOSS'])
        try:
            kdr = float(db_players[rank[1]]['KILLS'])/float(db_players[rank[1]]['DEATHS'])
        except ZeroDivisionError:
            kdr = db_players[rank[1]]['KILLS']/1
        player.append(kdr)
        try:
            accuracy = (float(db_players[rank[1]]['SHOTS_REG'])/float(db_players[rank[1]]['TOTAL_SHOTS']))*100
        except ZeroDivisionError:
            accuracy = 0
        player.append(str(int(accuracy))+'%')
        player_output.append(player)

    #fourth, output an html file
    table_header = ['UUID', 'Rank Score', 'Alias', 'CTF Score', 'Slayer Score', 'Win', 'Loss', 'KDR', 'Accuracy']
    html_output = HTML_STATS % tabulate(player_output, table_header, tablefmt='html', numalign="center", stralign="center")
    with open(HTML_PAGE, 'w') as f:
        f.write(html_output)

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
        #convert php special characters
        json_input = re.sub('%22', '"', args.arg)
        json_input = re.sub('%20', ' ', json_input)
        players = read(json.loads(json_input))

    update(players)
    output_html(DATABASE)


if __name__=="__main__":
    main()
