import os, sys, time
from flask import Flask, render_template, request, url_for, redirect
from valclient.client import Client
from backend.player import Player
from backend.server_module import *


# creates client and player object
client = ''
player = ''

# initialization variables
firstReq = True # variable to keep track if GET / has been seen before

# path for files for front-end
guiDir = os.path.join(os.path.dirname(__file__), '..', 'frontend')

if getattr(sys, 'frozen', False):
    # update the frontend path accordingly if running the compiled version
    guiDir = os.path.join(sys._MEIPASS, 'src', 'frontend')

server = Flask(__name__, static_folder=guiDir, template_folder=guiDir)
server.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # disable caching

data = get_user_settings()

def init_player():
    global client, player

    client = Client(region=data['region'].lower())
    client.activate()
    player = Player(client=client)

@server.context_processor
def inject_name():
    try:
        return dict(name=player.name) #makes it so we dont have to pass name every time
    except:
        return dict(name='Set Region')


@server.route("/region", methods=('GET', 'POST'))
def regionPopup():
    if request.method == 'POST':
        region = request.form['region']
        data['region'] = region
        write_user_settings(data)
        return redirect('/')
    return render_template('region.html', regions=get_regions())

@server.route("/", methods=('GET', 'POST'))
def home():
    global firstReq

    if data['region'] == None:
        return redirect('region')
    elif (firstReq == True) and (data['region'] != None):
        init_player()
    
    firstReq = False

    if request.method == 'POST':
        allsettings = get_user_settings()
        mapsettings = allsettings['mapPreferences']
        for _map in mapsettings.keys():
            req = request.form[_map]
            if req.lower() == "none":
                req = None
            mapsettings[_map] = req
        write_user_settings(allsettings)
    settings = get_user_settings()['mapPreferences'].items()
    return render_template(
        'index.html', 
        settings=settings,
        agents=get_agents(), 
        maps=get_maps(), 
    )

@server.route("/settings", methods=('GET', 'POST'))
def settings():
    settings = data.items()
    if request.method == 'POST':
        # get new settings from post request then update data
        checkUpdates = request.form['checkUpdates'] #need to make this a checkbox or dropdown | True or False
        hoverDelay = int(request.form['hoverDelay'])
        lockDelay = int(request.form['lockDelay'])
        data['checkUpdates'] = True if checkUpdates.lower() == "true" else False
        data['hoverDelay'] = hoverDelay if hoverDelay != '' else data['hoverDelay']
        data['lockDelay'] = lockDelay if lockDelay != '' else data['lockDelay']
        write_user_settings(data)
    return render_template("settings.html", settings=settings, regions=get_regions())

@server.route("/info")
def info():
    return render_template("info.html")

#equested endpoint when websocket encounters pregame
@server.route("/pregame_found", methods=['GET'])
def pregame_found():
    settings = get_user_settings()
    agents = get_agents()
    player.acknowledge_current_match()
    preferredAgent = agents[settings['mapPreferences'][player.currentMatch['map']]]

    print(preferredAgent)
    time.sleep(settings['hoverDelay'])
    player.hover_agent(preferredAgent)
    time.sleep(settings['lockDelay'])
    player.lock_agent(preferredAgent)

    print("the websocket has encountered pregame")
    return '', 200

@server.route("/get_match_info", methods=['GET'])
def get_match_info():
    return [player.currentMatch, player.seenMatches]

