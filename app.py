import sqlite3
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
import pandas as pd

app = Flask(__name__)

# Configuração do banco de dados
DATABASE = 'sistema_vendas_servicos.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Tabela de clientes
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS clientes (
        id TEXT PRIMARY KEY,
        nome TEXT NOT NULL,
        telefone TEXT,
        email TEXT,
        status TEXT DEFAULT 'ativo'
    )
    ''')
    
    # Tabela de vendas
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS vendas (
        id TEXT PRIMARY KEY,
        id_cliente TEXT,
        produto TEXT NOT NULL,
        valor REAL NOT NULL,
        data_venda DATE,
        responsavel TEXT,
        status TEXT DEFAULT 'pendente',
        FOREIGN KEY (id_cliente) REFERENCES clientes(id)
    )
    ''')
    
    # Tabela de ordens de serviço
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ordens_servico (
        id TEXT PRIMARY KEY,
        id_venda TEXT,
        servico TEXT NOT NULL,
        tecnico_responsavel TEXT,
        prioridade TEXT DEFAULT 'normal',
        status TEXT DEFAULT 'pendente',
        data_criacao DATE,
        data_conclusao DATE,
        observacoes TEXT,
        FOREIGN KEY (id_venda) REFERENCES vendas(id)
    )
    ''')
    
    # Tabela de histórico de status
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS historico_status (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo_entidade TEXT,
        id_entidade TEXT,
        status_anterior TEXT,
        status_novo TEXT,
        responsavel TEXT,
        data_mudanca TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()

# Rotas da aplicação
@app.route('/')
def dashboard():
    conn = sqlite3.connect(DATABASE)
    
    # Converter DataFrames para listas de dicionários
    clientes = pd.read_sql('SELECT * FROM clientes', conn).to_dict('records')
    vendas = pd.read_sql('SELECT * FROM vendas', conn).to_dict('records')
    ordens = pd.read_sql('SELECT * FROM ordens_servico', conn).to_dict('records')
    
    conn.close()
    
    return render_template('dashboard.html', 
                         clientes=clientes, 
                         vendas=vendas, 
                         ordens=ordens)

@app.route('/cliente/novo', methods=['GET', 'POST'])
def novo_cliente():
    if request.method == 'POST':
        id_cliente = request.form['id_cliente']
        nome = request.form['nome']
        telefone = request.form['telefone']
        email = request.form['email']
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            INSERT INTO clientes (id, nome, telefone, email)
            VALUES (?, ?, ?, ?)
            ''', (id_cliente, nome, telefone, email))
            
            conn.commit()
            conn.close()
            return redirect(url_for('dashboard'))
        except sqlite3.IntegrityError:
            conn.close()
            return "Erro: ID do cliente já existe", 400
    
    return render_template('novo_cliente.html')

@app.route('/venda/nova', methods=['GET', 'POST'])
def nova_venda():
    if request.method == 'POST':
        id_venda = f"V-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        id_cliente = request.form['id_cliente']
        produto = request.form['produto']
        valor = float(request.form['valor'])
        responsavel = request.form['responsavel']
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO vendas (id, id_cliente, produto, valor, data_venda, responsavel)
        VALUES (?, ?, ?, ?, DATE('now'), ?)
        ''', (id_venda, id_cliente, produto, valor, responsavel))
        
        # Registrar no histórico
        cursor.execute('''
        INSERT INTO historico_status (tipo_entidade, id_entidade, status_anterior, status_novo, responsavel, data_mudanca)
        VALUES ('venda', ?, '', 'pendente', ?, CURRENT_TIMESTAMP)
        ''', (id_venda, responsavel))
        
        conn.commit()
        conn.close()
        
        return redirect(url_for('dashboard'))
    
    conn = sqlite3.connect(DATABASE)
    clientes = pd.read_sql('SELECT id, nome FROM clientes WHERE status = "ativo"', conn).to_dict('records')
    conn.close()
    
    return render_template('nova_venda.html', clientes=clientes)

@app.route('/ordem/nova/<id_venda>', methods=['GET', 'POST'])
def nova_ordem_servico(id_venda):
    if request.method == 'POST':
        id_ordem = f"OS-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        servico = request.form['servico']
        tecnico = request.form['tecnico']
        prioridade = request.form['prioridade']
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO ordens_servico (id, id_venda, servico, tecnico_responsavel, prioridade, data_criacao)
        VALUES (?, ?, ?, ?, ?, DATE('now'))
        ''', (id_ordem, id_venda, servico, tecnico, prioridade))
        
        # Registrar no histórico
        cursor.execute('''
        INSERT INTO historico_status (tipo_entidade, id_entidade, status_anterior, status_novo, responsavel, data_mudanca)
        VALUES ('ordem_servico', ?, '', 'pendente', ?, CURRENT_TIMESTAMP)
        ''', (id_ordem, tecnico))
        
        conn.commit()
        conn.close()
        
        return redirect(url_for('dashboard'))
    
    return render_template('nova_ordem.html', id_venda=id_venda)

@app.route('/relatorios')
def relatorios():
    conn = sqlite3.connect(DATABASE)
    
    # Converter resultados para formatos amigáveis ao template
    vendas_cliente = pd.read_sql('''
    SELECT c.nome AS cliente, COUNT(v.id) AS total_vendas, SUM(v.valor) AS valor_total
    FROM clientes c
    LEFT JOIN vendas v ON c.id = v.id_cliente
    GROUP BY c.id
    ''', conn).to_dict('records')
    
    ordens_status = pd.read_sql('''
    SELECT status, COUNT(id) AS quantidade
    FROM ordens_servico
    GROUP BY status
    ''', conn).to_dict('records')
    
    historico = pd.read_sql('''
    SELECT * FROM historico_status
    ORDER BY data_mudanca DESC
    LIMIT 20
    ''', conn).to_dict('records')
    
    conn.close()
    
    return render_template('relatorios.html',
                         vendas_cliente=vendas_cliente,
                         ordens_status=ordens_status,
                         historico=historico)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)