# Servidor Web Flask Para Controle de uma Lixeira

Este sistema implementa um servidor web com Flask integrado a um Raspberry Pi, que gerencia uma lixeira inteligente equipada com sensores, LEDs e mecanismos para controle de tampa. Além disso, o sistema envia dados de ocupação para a nuvem através do ThingSpeak.

## Objetivo 
Monitorar a ocupação da lixeira, controlar a tampa remotamente e registrar eventos.

## Funções

### `before_first_request()`

```
@app.before_request
def before_first_request():
    carregar_listTampa_de_txt()
```

Executada antes da primeira requisição ao servidor. Carrega o histórico de eventos de abertura e fechamento da tampa da lixeira a partir de um arquivo de texto.

---

### `testaConexao()`

```
def testaConexao():
    try:
        urlopen('https://www.materdei.edu.br/pt', timeout=1)
        return True
    except:
        return False
```

Testa a conexão com a internet, tentando acessar um site especificado. Retorna `True` se a conexão for bem-sucedida e `False` caso contrário.

---

### `distancia()`

```
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
```

Calcula a distância do sensor ultrassônico até o lixo dentro da lixeira e determina a ocupação percentual da lixeira. Caso haja conexão com a internet, envia os dados de ocupação para o ThingSpeak. Retorna a ocupação formatada como uma string.

---

### `salvar_listTampa_em_txt()`

```
def salvar_listTampa_em_txt():
    with open("logTampa.txt", "a", encoding="utf-8") as file:
        for item in listTampa:
            evento = item['evento']
            data = item['data'].strftime("%Y-%m-%d %H:%M:%S")
            file.write(f"{evento} - {data}\n")
    print("Dados salvos em listTampa.txt")
```

Salva os eventos de abertura e fechamento da tampa da lixeira no arquivo `logTampa.txt`. Cada evento é registrado com a data e hora em que ocorreu.

---

### `index()`

```
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
```

Controla a rota principal do servidor Flask (`"/"`). Renderiza a página principal do sistema com os dados da ocupação da lixeira, status da tampa, status geral da lixeira e o histórico de eventos.

---

### `controleTampaLixeira(action)`

```
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
        salvar_listTampa_em_txt()
    elif action == 'fechar':
        fechandoLixeira = True
        abrindoLixeira = False
        listTampa.append({'evento': 'Tampa Fechada', 'data': datetime.now()})
        salvar_listTampa_em_txt()
        
    return index()
```

Controla a rota `/controle_tampa/<action>`. Permite abrir ou fechar a tampa da lixeira com base no parâmetro `action` (`"abrir"` ou `"fechar"`). Atualiza o status da tampa e a lista de eventos, aciona os LEDs apropriados e salva os eventos no arquivo de log.

---

### `statusLixeira()`

```
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
```

Controla a rota `/status_lixeira`. Determina se a lixeira está "Disponível" ou "Cheia" com base na ocupação calculada pela função `distancia()`. Aciona os LEDs correspondentes e retorna o status atual.

---

### `carregar_listTampa_de_txt()`

```
def carregar_listTampa_de_txt():
    global listTampa
    try:
        with open("logTampa.txt", "r", encoding="utf-8") as file:
            lines = file.readlines()
            for line in lines:
                evento, data = line.strip().split(" - ")
                data = datetime.strptime(data, "%Y-%m-%d %H:%M:%S")
                listTampa.append({'evento': evento, 'data': data})
    except FileNotFoundError:
        listTampa = []
```

Carrega o histórico de eventos de abertura e fechamento da tampa a partir do arquivo `logTampa.txt`, populando a lista `listTampa`. Ignora a operação caso o arquivo não exista.