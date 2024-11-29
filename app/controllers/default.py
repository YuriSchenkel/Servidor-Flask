import RPi.GPIO as gpio 
import time as delay
from app import app
from flask import render_template
from datetime import datetime
import requests
from urllib.request import urlopen
import Adafruit_DHT as dht
import os

gpio.setmode(gpio.BOARD)
gpio.setwarnings(False)

global listTampa
global abrindoLixeira 
global fechandoLixeira

listTampa = []
abrindoLixeira = False
fechandoLixeira = False
ledVermelho, ledVerde = 11, 12
pin_t = 15
pin_e = 16
lixeira_v = 20
ocupa_num = 0
status_lixeira = 'Disponível' 
status_tampa = False
urlBase = 'https://api.thingspeak.com/update?api_key='
keyWrite = 'S6WGUMYV9F6QR6XR'
sensorDistancia = '&field1='

gpio.setup(ledVermelho, gpio.OUT)
gpio.setup(ledVerde, gpio.OUT)
gpio.output(ledVermelho, gpio.LOW)
gpio.output(ledVerde, gpio.LOW)
gpio.setup(pin_t, gpio.OUT)
gpio.setup(pin_e, gpio.IN)

@app.before_request
def before_first_request():
    carregar_listTampa_de_txt()

def testaConexao():
    try:
        urlopen('https://www.materdei.edu.br/pt', timeout=1)
        return True
    except:
        return False

def distancia():
    gpio.output(pin_t, True)
    delay.sleep(0.000001) 
    gpio.output(pin_t, False)
    tempo_i = delay.time()
    tempo_f = delay.time()
    while gpio.input(pin_e) == 0:
        tempo_i = delay.time()
    while gpio.input(pin_e) == 1:
        tempo_f = delay.time()
    tempo_d = tempo_f - tempo_i
    distancia = (tempo_d * 34300) / 2  
    ocupacao_l = (distancia / lixeira_v) * 100
    ocupacao_f = 100 - ocupacao_l
    if ocupacao_f < 0:
        ocupacao_f = 0
    ocupacao_lixeira = ("{0:0.0f}%".format(ocupacao_f))
    
    if testaConexao() == True:

        urlDados = (urlBase + keyWrite + sensorDistancia + str(ocupacao_lixeira))
        retorno = requests.post(urlDados)
        if retorno.status_code == 200:
            print('Dados enviados com sucesso!')
        else:
            print('Erro ao enviar dados: ' + retorno.status_code)

    return ocupacao_lixeira   

@app.route("/")
def index():
    templateData = {
        'ocup_lixeira': distancia(),
        'controle_tampa': 'Aberta' if status_tampa else 'Fechada',
        'status_lixeira': statusLixeira(),
        'abrindoLixeira': abrindoLixeira,
        'fechandoLixeira': fechandoLixeira,
        'listTampa': listTampa
    }
    return render_template('index.html', **templateData)

@app.route("/controle_tampa/<action>")
def controleTampaLixeira(action):
    global status_tampa, abrindoLixeira, fechandoLixeira
    status_tampa = action == 'abrir'

    if action == 'abrir':
        abrindoLixeira = True
        fechandoLixeira = False
        if statusLixeira() == 'Disponível':
            for i in range(3):
                gpio.output(ledVerde, gpio.HIGH)
                delay.sleep(0.5)
                gpio.output(ledVerde, gpio.LOW)
                delay.sleep(0.5)
            gpio.output(ledVerde, gpio.HIGH)
        else:
            for i in range(3):
                gpio.output(ledVermelho, gpio.HIGH)
                delay.sleep(0.5)
                gpio.output(ledVermelho, gpio.LOW)
                delay.sleep(0.5)
            gpio.output(ledVermelho, gpio.HIGH) 

        listTampa.append({'evento': 'Tampa Aberta', 'data': datetime.now()})
        with open("logTampa.txt", "a", encoding="utf-8") as file:
            evento = 'Tampa Aberta'
            data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            file.write(f"{evento} - {data}\n")
            print("Dados salvos em listTampa.txt")
    elif action == 'fechar':
        fechandoLixeira = True
        abrindoLixeira = False
        listTampa.append({'evento': 'Tampa Fechada', 'data': datetime.now()})
        with open("logTampa.txt", "a", encoding="utf-8") as file:
            evento = 'Tampa Fechada'
            data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            file.write(f"{evento} - {data}\n")
            print("Dados salvos em listTampa.txt")        
    return index()

@app.route("/status_lixeira")
def statusLixeira():
    ocupacao = distancia()
    ocupacao_num = float(ocupacao.replace('%', ''))
    
    global status_lixeira
    if 0 <= ocupacao_num < 100:
        status_lixeira = 'Disponível'
        gpio.output(ledVerde, gpio.HIGH) 
        gpio.output(ledVermelho, gpio.LOW)
    else:
        status_lixeira = 'Cheia'
        gpio.output(ledVerde, gpio.LOW)
        gpio.output(ledVermelho, gpio.HIGH)  

    return status_lixeira

def carregar_listTampa_de_txt():
    global listTampa
    listTampa = []
    try:
        with open("logTampa.txt", "r", encoding="utf-8") as file:
            lines = file.readlines()
            for line in lines:
                evento, data = line.strip().split(" - ")
                data = datetime.strptime(data, "%Y-%m-%d %H:%M:%S")
                listTampa.append({'evento': evento, 'data': data})
    except FileNotFoundError:
        listTampa = []

