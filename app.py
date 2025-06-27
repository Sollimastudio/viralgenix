import streamlit as st
import sqlite3
import bcrypt
import os
from datetime import datetime
import pandas as pd
import google.generativeai as genai

# --- CONFIGURAÇÃO INICIAL E LEITURA SEGURA DA CHAVE DE API ---
st.set_page_config(
    page_title="ViralGenix",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

try:
    # Esta linha lê a chave de API que vamos configurar na nuvem do Streamlit
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)
except FileNotFoundError:
    # Este erro acontece quando rodamos localmente sem um arquivo de segredos.
    # Podemos adicionar uma mensagem mais amigável ou usar uma chave local para testes.
    st.warning("Arquivo de segredos não encontrado. A IA não funcionará no ambiente local sem um arquivo secrets.toml.")
    st.stop()
except KeyError:
    # Este erro acontece na nuvem se a chave não for configurada.
    st.error("ERRO CRÍTICO: A chave de API do Gemini não foi encontrada nos 'Segredos' do Streamlit. Por favor, configure-a no painel de deploy.")
    st.stop()
except Exception as e:
    st.error(f"Erro na configuração da API Key do Gemini: {e}")
    st.stop()

# --- CLASSE DE IA E FUNÇÕES DE BANCO DE DADOS ---
class ViralContentGenerator:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-1.5-flash-latest')

    def generate_content(self, prompt):
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            st.error(f"Erro ao contatar a IA: {e}")
            return f"Erro ao gerar conteúdo. Verifique suas permissões de API e o faturamento no Google Cloud."

def init_database():
    conn = sqlite3.connect('viralgenix.db')
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contents (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            tema TEXT,
            artigo TEXT,
            roteiro TEXT,
            legendas TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS insights (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            text TEXT,
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()

# --- LÓGICA DE AUTENTICAÇÃO ---
def login_page():
    st.title("🚀 Bem-vindo ao ViralGenix")
    st.subheader("Faça login para começar a criar")
    if "logged_in" not in st.session_state: st.session_state.logged_in = False
    if st.session_state.logged_in: return True
    
    choice = st.selectbox("Escolha uma opção:", ["Login", "Registrar"])
    if choice == "Login":
        with st.form("login_form"):
            username = st.text_input("Nome de Usuário")
            password = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Entrar")
            if submitted:
                conn = sqlite3.connect('viralgenix.db')
                cursor = conn.cursor()
                cursor.execute("SELECT id, password FROM users WHERE username=?", (username,))
                user_data = cursor.fetchone()
                conn.close()
                if user_data and bcrypt.checkpw(password.encode('utf-8'), user_data[1]):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.user_id = user_data[0]
                    st.rerun()
                else: st.error("Usuário ou senha inválidos.")
    elif choice == "Registrar":
        with st.form("register_form"):
            new_username = st.text_input("Escolha um Nome de Usuário")
            new_password = st.text_input("Crie uma Senha", type="password")
            submitted = st.form_submit_button("Registrar")
            if submitted:
                if new_username and new_password:
                    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
                    conn = sqlite3.connect('viralgenix.db')
                    cursor = conn.cursor()
                    try:
                        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (new_username, hashed_password))
                        conn.commit()
                        st.success("Usuário registrado! Agora você pode fazer login.")
                    except sqlite3.IntegrityError: st.error("Esse nome de usuário já existe.")
                    conn.close()
                else: st.warning("Por favor, preencha todos os campos.")
    return st.session_state.logged_in

# --- FUNÇÃO PRINCIPAL DO APLICATIVO ---
def main():
    init_database()
    if not login_page(): return

    st.markdown('<h1 style="text-align: center;">🚀 ViralGenix</h1>', unsafe_allow_html=True)
    ai_generator = ViralContentGenerator()

    with st.sidebar:
        st.header("⚙️ Configurações Gerais")
        st.write(f"Olá, **{st.session_state.username}**!")
        amostra_texto = st.text_area("Seu Estilo de Escrita (Tom de Voz):", height=150, placeholder="Cole textos seus aqui...")
        publico = st.selectbox("Público-alvo:", ["Empreendedores", "Estudantes", "Criadores de Conteúdo", "Geral"])
        tendencia = st.text_input("Tendência para Conectar:")
        if st.button("Sair"):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    st.header("💡 Criação de Conteúdo")
    tema = st.text_input("🎯 Qual é o tema principal?", placeholder="Ex: Dicas de produtividade")

    if st.button("🚀 Gerar Conteúdo (Artigo e Roteiro)", type="primary"):
        if tema:
            with st.spinner("🤖 Contratando a IA... Gerando artigo e roteiro... Por favor, aguarde."):
                prompt_artigo = f"Escreva um artigo de blog otimizado para SEO sobre '{tema}' para um público de '{publico}', conectando com a tendência '{tendencia}' e com o tom de '{amostra_texto}'."
                artigo_gerado = ai_generator.generate_content(prompt_artigo)
                
                if "ERRO_IA:" not in artigo_gerado:
                    prompt_roteiro = f"Baseado no seguinte artigo, crie um roteiro de vídeo para o YouTube de 10 minutos, com marcações para cortes virais. Artigo: {artigo_gerado}"
                    roteiro_gerado = ai_generator.generate_content(prompt_roteiro)
                else:
                    roteiro_gerado = "Não foi possível gerar o roteiro pois a geração do artigo falhou."
                
                conn = sqlite3.connect('viralgenix.db')
                cursor = conn.cursor()
                cursor.execute("INSERT INTO contents (user_id, tema, artigo, roteiro, legendas) VALUES (?, ?, ?, ?, ?)", (st.session_state.user_id, tema, artigo_gerado, roteiro_gerado, ""))
                conn.commit()
                conn.close()
                st.session_state.last_generated = {"artigo": artigo_gerado, "roteiro": roteiro_gerado}
                st.rerun()
        else:
            st.warning("Por favor, insira um tema.")

    if "last_generated" in st.session_state:
        st.header("📊 Resultados Gerados")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📝 Artigo de Blog")
            st.text_area("Artigo", value=st.session_state.last_generated["artigo"], height=400, key="artigo_res")
        with col2:
            st.subheader("🎬 Roteiro de Vídeo")
            st.text_area("Roteiro", value=st.session_state.last_generated["roteiro"], height=400, key="roteiro_res")

    with st.expander("📚 Histórico de Criações"):
        conn = sqlite3.connect('viralgenix.db')
        try:
            if 'user_id' in st.session_state:
                history_df = pd.read_sql_query(f"SELECT tema, created_at FROM contents WHERE user_id = {st.session_state.user_id} ORDER BY created_at DESC", conn)
                st.dataframe(history_df)
        except Exception:
            st.write("Histórico vazio ou erro ao carregar.")
        finally:
            conn.close()

if __name__ == "__main__":
    main()
