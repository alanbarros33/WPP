import streamlit as st
import pandas as pd
import re
import plotly.express as px
from collections import Counter
from wordcloud import WordCloud
from datetime import datetime
import matplotlib.pyplot as plt
import io


# Configuração do layout wide
st.set_page_config(layout="wide")

# Sidebar com logo e texto explicativo
with st.sidebar:
    st.image("logo.png", width=200)  # Atualizar com o caminho correto da logo
    st.markdown("""
    <div style="text-align: center;">
        <h2 style="color:#4B8BBE;">Análise de Conversas 📊</h2>
        <p>Esta aplicação permite analisar conversas do WhatsApp para identificar sentimentos, 
        padrões de interação e tópicos mais discutidos.</p>
    </div>
    
    <hr style="border:1px solid #4B8BBE;">
    
    <h3 style="color:#4B8BBE;">Como Usar:</h3>
    <ol>
        <li><span style="color:#4CAF50;">📁</span> <strong>Exporte</strong> o histórico de conversa do WhatsApp como um arquivo de texto (.txt).</li>
        <li><span style="color:#4CAF50;">⬆️</span> <strong>Faça o upload</strong> do arquivo na aplicação.</li>
        <li><span style="color:#4CAF50;">🔍</span> O sistema irá processar e exibir insights como a distribuição de sentimentos, quem fala mais e outros padrões interessantes.</li>
    </ol>
    
    <hr style="border:1px solid #4B8BBE;">
    
    <div style="text-align: center;">
        <p style="font-size: 12px; color: gray;">© 2024 Análise de Conversas</p>
    </div>
    """, unsafe_allow_html=True)

# Dicionário de palavras para categorizar sentimentos
word_sentiment = {
    "feliz": ["amor", "gostoso", "bom", "ótimo", "perfeito", "❤️", "💕", "😂"],
    "raiva": ["droga", "raiva", "irritado", "mal", "merda", "💩", "🤬"],
    "triste": ["triste", "desculpa", "saudade", "🥺"],
}

# Função para categorizar mensagens
def categorize_message(message):
    for sentimento, palavras in word_sentiment.items():
        for palavra in palavras:
            if re.search(rf'\b{palavra}\b', message, re.IGNORECASE):
                return sentimento
    return "neutro"

# Função para analisar o chat
def analyze_chat(file):
    lines = file.split("\n")
    data = {"Data": [], "Participante": [], "Mensagem": [], "Sentimento": []}
    
    for line in lines:
        if re.match(r'\[\d{2}/\d{2}/\d{4}, \d{2}:\d{2}:\d{2}\]', line):
            data_match = re.match(r'\[(.*?)\] (.*?): (.*)', line)
            if data_match:
                data["Data"].append(data_match.group(1))
                data["Participante"].append(data_match.group(2))
                mensagem = data_match.group(3)
                sentimento = categorize_message(mensagem)
                data["Mensagem"].append(mensagem)
                data["Sentimento"].append(sentimento)
    
    df = pd.DataFrame(data)
    df["Data"] = pd.to_datetime(df["Data"], format='%d/%m/%Y, %H:%M:%S')
    return df

# Função para identificar quem inicia mais conversas
def quem_inicia_conversa(df):
    df_sorted = df.sort_values(by='Data')
    intervalos = df_sorted['Data'].diff().dt.total_seconds() > 600  # Intervalo de mais de 10 minutos
    iniciadores = df_sorted.loc[intervalos, 'Participante'].value_counts()
    return iniciadores.idxmax() if not iniciadores.empty else "N/A"

# Função para identificar quem mais demora para responder
def quem_demora_para_responder(df):
    df_sorted = df.sort_values(by='Data')
    df_sorted['tempo_resposta'] = df_sorted['Data'].diff().dt.total_seconds()
    media_resposta = df_sorted.groupby('Participante')['tempo_resposta'].mean()
    return media_resposta.idxmax() if not media_resposta.empty else "N/A"

# Função para identificar quem mais demonstra um determinado sentimento
def quem_demonstra_sentimento(df, sentimento):
    sent_counts = df[df['Sentimento'] == sentimento]['Participante'].value_counts()
    return sent_counts.idxmax() if not sent_counts.empty else "N/A"

# Função para identificar picos de sentimentos
def identificar_picos_sentimentos(df):
    # Contagem de sentimentos por dia, excluindo 'neutro'
    sentiment_daily = df[df['Sentimento'] != 'neutro'].groupby([df['Data'].dt.date, 'Sentimento']).size().reset_index(name='Contagem')
    
    # Selecionar dias com pico para cada sentimento
    picos = {}
    for sentimento in ['feliz', 'raiva', 'triste']:
        sentimento_dia = sentiment_daily[sentiment_daily['Sentimento'] == sentimento].sort_values(by='Contagem', ascending=False).head(1)
        if not sentimento_dia.empty:
            picos[sentimento] = sentimento_dia.iloc[0]
    
    return picos


# Função para gerar relatório em texto
def gerar_relatorio_txt(metrics_text, peaks_text):
    output = io.StringIO()

    output.write("Relatório de Conversas\n\n")
    output.write(f"Data da análise: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
    output.write("Métricas da Conversa:\n")
    output.write(metrics_text)
    output.write("\n\nPicos de Sentimentos:\n")
    output.write(peaks_text)
    output.write("\n\n")
    
    return output.getvalue()

# Funções de visualização
def plot_sentiment_over_time(df):
    daily_sentiment = df.groupby([df['Data'].dt.date, "Sentimento"]).size().reset_index(name='Contagem')
    daily_total = daily_sentiment.groupby('Data')['Contagem'].sum().reset_index(name='Total')
    daily_sentiment = daily_sentiment.merge(daily_total, on='Data')
    daily_sentiment['Proporcao'] = daily_sentiment['Contagem'] / daily_sentiment['Total']
    
    fig = px.line(
        daily_sentiment, 
        x='Data', 
        y='Proporcao', 
        color='Sentimento',
        title="Evolução dos Sentimentos ao Longo do Tempo",
        labels={'Proporcao': 'Proporção', 'Data': 'Data'},
        color_discrete_map={
            'feliz': 'blue', 
            'raiva': 'red', 
            'triste': 'purple', 
            'neutro': 'orange'
        }
    )
    fig.update_traces(mode='lines+markers', marker=dict(size=6))
    fig.update_layout(hovermode='x unified')
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("📈 **Análise**: Este gráfico mostra a variação de sentimentos ao longo do tempo. Cada cor representa um sentimento específico.")

def plot_sentiment_distribution(df):
    """Gráfico de barras mostrando a proporção de sentimentos"""
    sentiment_counts = df["Sentimento"].value_counts().reset_index()
    sentiment_counts.columns = ['Sentimento', 'Quantidade']
    
    fig = px.bar(
        sentiment_counts, 
        x='Sentimento', 
        y='Quantidade', 
        text='Quantidade',
        title="Distribuição dos Sentimentos",
        labels={'Quantidade': 'Quantidade de Mensagens', 'Sentimento': 'Sentimento'},
        color='Sentimento',
        color_discrete_map={
            'feliz': 'blue', 
            'raiva': 'red', 
            'triste': 'purple', 
            'neutro': 'orange'
        }
    )
    fig.update_traces(texttemplate='%{text}', textposition='outside')
    fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("📊 **Análise**: Este gráfico mostra a distribuição dos diferentes sentimentos encontrados nas mensagens.")

def plot_participant_stats(df):
    """Gráfico de barras comparando a quantidade de mensagens por participante"""
    participant_counts = df["Participante"].value_counts().reset_index()
    participant_counts.columns = ['Participante', 'Quantidade']
    
    fig = px.bar(
        participant_counts, 
        x='Participante', 
        y='Quantidade', 
        text='Quantidade',
        title="Mensagens por Participante",
        labels={'Quantidade': 'Quantidade de Mensagens', 'Participante': 'Participante'},
        color='Participante',
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig.update_traces(texttemplate='%{text}', textposition='outside')
    fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("👥 **Análise**: Este gráfico compara a quantidade de mensagens enviadas por cada participante, mostrando quem foi o mais ativo.")

def plot_wordcloud(df):
    """Nuvem de palavras das mensagens mais comuns"""
    all_text = ' '.join(df['Mensagem'])
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(all_text)
    
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis("off")
    st.pyplot(plt)
    st.markdown("🌈 **Análise**: Esta nuvem de palavras mostra as palavras mais frequentes nas mensagens, revelando os principais temas e emoções.")

# Streamlit app
def main():
    st.markdown("""
    <div style="text-align: center;">
        <h1>Bem-vindo à Ferramenta de Análise de Conversas do WhatsApp!</h1>
        <h2>Carregue seu arquivo de chat para começar a explorar insights sobre suas conversas.</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Upload do arquivo
    uploaded_file = st.file_uploader("📂 Carregar arquivo de chat", type=["txt"])
    if uploaded_file is not None:
        file_content = uploaded_file.read().decode('utf-8')
        df = analyze_chat(file_content)

        # Filtros na parte superior
        col1, col2 = st.columns(2)
        with col1:
            participante_filter = st.selectbox("👤 Selecionar Participante", options=["Todos"] + list(set(df["Participante"])))
        #with col2:
           #date_filter = st.date_input("Selecionar data", [])

        # Aplicar filtros
        if participante_filter != "Todos":
            df = df[df['Participante'] == participante_filter]
        #if date_filter:
            #df = df[df['Data'].dt.date == date_filter]

        # Gráficos
        st.header("📈 Análises")
        
        col1, col2 = st.columns(2)
        
        with col1:
            plot_sentiment_over_time(df)
        with col2:
            plot_sentiment_distribution(df)

        st.header("👥 Estatísticas dos Participantes")
        plot_participant_stats(df)

        st.header("🌟 Nuvem de Palavras")
        plot_wordcloud(df)

        st.header("🔍 Métricas e Picos de Sentimentos")

        # Texto dinâmico de métricas
        metrics_text = f"🔍 **{quem_inicia_conversa(df)}** é a pessoa que mais inicia conversas.\n"
        metrics_text += f"⏳ **{quem_demora_para_responder(df)}** é a pessoa que mais demora para responder.\n"
        metrics_text += f"😊 **{quem_demonstra_sentimento(df, 'feliz')}** é a pessoa que demonstra mais felicidade.\n"
        
        # Texto dinâmico para picos de sentimentos
        peaks = identificar_picos_sentimentos(df)
        peaks_text = ""
        if 'feliz' in peaks:
            peaks_text += f"🎉 No dia **{peaks['feliz']['Data']}** houve um pico de felicidade.\n"
        if 'raiva' in peaks:
            peaks_text += f"😠 No dia **{peaks['raiva']['Data']}** houve um pico de raiva.\n"
        if 'triste' in peaks:
            peaks_text += f"😢 No dia **{peaks['triste']['Data']}** houve um pico de tristeza.\n"

        # Exibindo métricas e picos juntos
        combined_text = metrics_text + "\n" + peaks_text
        st.text_area("📄 Resumo da Análise", combined_text, height=200)

        # Botão de exportação
        col1, col2 = st.columns(2)
        #with col1:
            #if st.button("Exportar Relatório em PDF"):
                #pdf = generate_pdf_report(df)
                #buffer = io.BytesIO()
                #pdf.output(buffer, 'F')  # 'F' para salvar no buffer
                #buffer.seek(0)
                #st.download_button("Baixar Relatório PDF", data=buffer, file_name="relatorio_sentimentos.pdf", mime="application/pdf")
        with col2:
            if st.button("📄 Exportar Relatório em TXT"):
                report = gerar_relatorio_txt(metrics_text, peaks_text)
                st.download_button("⬇️ Baixar Relatório TXT", report, "relatorio.txt")

    else:
        st.markdown("""
        <div style="text-align: center; margin-top: 50px;">
            <p>☝️ Utilize o botão acima para fazer o upload do seu histórico de conversas do WhatsApp.</p>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
