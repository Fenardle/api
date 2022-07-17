import time
import traceback
import json
from web3 import Web3
import pandas as pd
from flask_apscheduler import APScheduler
from datetime import datetime

from flask import Flask, request

app = Flask(__name__)
app.config['SCHEDULER_API_ENABLED'] = True
scheduler = APScheduler()
scheduler.init_app(app)

rooms = []
rooms_id = []

infura_url = 'https://ropsten.infura.io/v3/22930adbaf9b4b7491baa4420d92ba1d'
web3 = Web3(Web3.HTTPProvider(infura_url))

# Battle address and abi
w3 = Web3(Web3.HTTPProvider("https://ropsten.infura.io/v3/22930adbaf9b4b7491baa4420d92ba1d"))
uni_address = "0x691ffce59E67561D20e82d1894f1cD84D9Ca5E22"
abi_str = open("Battle.abi.json")
abi = json.load(abi_str)
contract = w3.eth.contract(address=w3.toChecksumAddress(uni_address), abi=abi)

stake_event_filter = contract.events.Stake.createFilter(fromBlock='latest')
cancel_event_filter = contract.events.Cancel.createFilter(fromBlock='latest')


@app.route('/get_rooms', methods=['GET'])
def get_rooms():
    try:
        start_position = int(request.args['page']) * int(request.args['page_size'])

        if len(rooms) == 0:
            return {'code': 50002, 'message': 'is empty'}

        if start_position >= len(rooms):
            return {'code': 50002, 'message': 'out of data range'}

        end_position = start_position + int(request.args['page_size'])

        if end_position >= len(rooms):
            return {
                'code': 200,
                'data': {
                    'next_page': None,
                    'room_list': rooms[start_position:end_position]
                }
            }

        return {
            'code': 200,
            'data': {
                'next_page': int(request.args['page']) + 1,
                'room_list': rooms[start_position:end_position]
            }
        }

    except:
        return {'code': 50001, 'message': traceback.format_exc()}


@app.route('/search_room', methods=['GET'])
def search_room():
    try:
        for r in rooms:
            if r['room_id'] == str(request.args['room_id']):
                return {'code': 200, 'data': {'room_information': r}}

        return {'code': 50002, 'message': 'no such room id'}

    except:
        return {'code': 50001, 'message': traceback.format_exc()}


@app.route('/make_room', methods=['POST'])
def make_room():
    try:
        end = 17
        room_information = {
            'room_id': str(time.time())[11:end - len(str(len(rooms_id)))] + str(len(rooms_id)),
            'game_type': str(request.form['game_type']),
            'game_area': str(request.form['game_area']),
            'stake_amount': str(request.form['stake_amount']),
            'player_1_id': str(request.form['play_1_id']),
            'player_2_id': None,
            'player_1_status': 0,
            'player_2_status': 0,
            'player_1_address': str(request.form['player_1_address']),
            'player_2_address': None,
        }
        rooms.append(room_information)
        rooms_id.append((str(len(rooms_id)).zfill(5)))
        return {'code': 200, 'room_id': room_information['room_id']}

    except:
        return {'code': 50001, 'message': traceback.format_exc()}


@app.route('/enter_room', methods=['POST'])
def enter_room():
    try:
        entered_room_id = request.form['room_id']
        for i in rooms:
            if i['room_id'] == entered_room_id:
                i['player_2_id'] = str(request.form['player_2_id'])
                i['player_2_address'] = str(request.form['player_2_address'])
                return {'code': 200}

        return {'code': 50002, 'message': 'no such room id'}

    except:
        return {'code': 50001, 'message': traceback.format_exc()}


@app.route('/leave_room', methods=['POST'])
def leave_room():
    try:
        leaved_room_id = request.form['room_id']
        for i in rooms:
            if i['room_id'] == leaved_room_id:
                i['player_2_id'] = None
                i['player_2_address'] = None
                return {'code': 200}

        return {'code': 50002, 'message': 'no such room id'}

    except:
        return {'code': 50001, 'message': traceback.format_exc()}


@app.route('/delete_room', methods=['POST'])
def delete_room():
    try:
        deleted_room_id = request.form['deleted_room_id']
        for i in rooms:
            if i['room_id'] == deleted_room_id:
                rooms.remove(i)
                return {'code': 200}

        return {'code': 50002, 'message': 'no such room id'}

    except:
        return {'code': 50001, 'message': traceback.format_exc()}


@app.route('/set_winner', methods=['POST'])
def set_winner():
    try:
        winner_address = request.form['winner_address']
        for i in rooms:
            if i['player_1_address'] == winner_address:
                pd.DataFrame({'time': [str(datetime.now())], 'winner': [str(winner_address)], 'loser': [str(i['player_2_address'])]}).to_csv('result.csv', mode='a', header=False, index=False)
                rooms.remove(i)
                return {'code': 200}
            elif i['player_2_address'] == winner_address:
                pd.DataFrame({'time': [str(datetime.now())], 'winner': [str(winner_address)], 'loser': [str(i['player_1_address'])]}).to_csv('result.csv', mode='a', header=False, index=False)
                rooms.remove(i)
                return {'code': 200}

        return {'code': 50002, 'message': 'no such room id'}

    except:
        return {'code': 50001, 'message': traceback.format_exc()}


@scheduler.task('cron', id='get_stake', second='0/2')
def get_stake():
    for PairCreated in stake_event_filter.get_new_entries():
        for i in rooms:
            if i['player_1_address'] == PairCreated["args"]["player"] \
                    and i['stake_amount'] == str(PairCreated["args"]["stake_amount"]) \
                    and i['player_2_address'] == PairCreated["args"]["player_opponent"]:
                i['player_1_status'] = 1
                print(i)
                with open('set.txt', 'a+') as f:
                    f.write(str(datetime.now()) + " " + i['room_id'] + " player_1: " + PairCreated["args"]["player"])
            elif i['player_2_address'] == PairCreated["args"]["player"] \
                    and i['stake_amount'] == str(PairCreated["args"]["stake_amount"]) \
                    and i['player_1_address'] == PairCreated["args"]["player_opponent"]:
                i['player_1_status'] = 1
                print(i)
                with open('set.txt', 'a+') as f:
                    f.write(str(datetime.now())+" "+i['room_id']+" player_2: "+PairCreated["args"]["player"])
                print(i)



@scheduler.task('cron', id='get_cancel', second='1/2')
def get_cancel():
    for PairCreated in cancel_event_filter.get_new_entries():
        for i in rooms:
            if i['player_1_address'] == PairCreated["args"]["player"]:
                i['player_1_status'] = 0
                print(i)
                with open('cancel.txt', 'a+') as f:
                    f.write(str(datetime.now())+" "+i['room_id']+" player_1: "+PairCreated["args"]["player"])
            elif i['player_2_address'] == PairCreated["args"]["player"]:
                i['player_1_status'] = 0
                print(i)
                with open('cancel.txt', 'a+') as f:
                    f.write(str(datetime.now())+" "+i['room_id']+" player_2: "+PairCreated["args"]["player"])
                print(i)

scheduler.start()


if __name__ == "__main__":
    app.run(host="0.0.0.0")
