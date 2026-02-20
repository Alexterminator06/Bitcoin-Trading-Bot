import streamlit as st
import yfinance as yf
import pandas as pd
from engine import TradingEngine
import os
import sys
import subprocess
import time
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi

# --- CONFIGURATION INITIALE ---
st.set_page_config(page_title="Crypto Bot Dashboard", layout="wide")
load_dotenv()

st.title("🤖 Bitcoin Trading Bot - Centre de Contrôle")

# --- GESTION DE L'ÉTAT DU BOT (MÉMOIRE) ---
if 'bot_process' not in st.session_state:
    st.session_state.bot_process = None
if 'active_bot_type' not in st.session_state:
    st.session_state.active_bot_type = None # 'alpaca' ou 'binance'

# Fonction pour vérifier si le processus est toujours vivant
def is_bot_running():
    if st.session_state.bot_process is None:
        return False
    if st.session_state.bot_process.poll() is not None:
        # Le processus s'est terminé tout seul (erreur ou fin)
        st.session_state.bot_process = None
        st.session_state.active_bot_type = None
        return False
    return True

# Fonction pour arrêter proprement n'importe quel bot
def stop_bot():
    if st.session_state.bot_process:
        st.session_state.bot_process.terminate()
        st.session_state.bot_process = None
        st.session_state.active_bot_type = None

# --- CONNEXION ALPACA (Pour l'affichage onglet 1) ---
api_key = os.getenv("ALPACA_API_KEY")
secret_key = os.getenv("ALPACA_SECRET_KEY")
base_url = os.getenv("ALPACA_BASE_URL")

connected = False
account = None
try:
    if api_key:
        api = tradeapi.REST(api_key, secret_key, base_url, api_version='v2')
        account = api.get_account()
        connected = True
except:
    pass

# --- TABS (NAVIGATION) ---
# On a maintenant 3 onglets distincts
tab_alpaca, tab_binance, tab_simu = st.tabs(["🇺🇸 ALPACA (Signaux)", "🔶 BINANCE (Auto)", "⚡ SIMULATION"])

# ==========================================
# ONGLET 1 : ALPACA / SIGNAL BOT
# ==========================================
with tab_alpaca:
    st.header("📡 Bot de Signaux (Alpaca Data + Telegram)")
    st.caption("Ce bot surveille le marché et vous envoie des notifications Telegram.")
    
    col_config, col_status = st.columns([1, 2])
    
    with col_config:
        choix_symbol = st.selectbox(
            "Actif à surveiller",
            ["BTC/USD", "ETH/USD", "NVDA", "TSLA", "AAPL"],
            index=0,
            disabled=is_bot_running()
        )
        
        st.divider()
        
        # BOUTON START ALPACA
        if st.button("▶️ DÉMARRER SIGNAUX", disabled=is_bot_running(), key="start_alpaca", use_container_width=True):
            try:
                cmd = [sys.executable, "signal_bot.py", "--symbol", choix_symbol]
                st.session_state.bot_process = subprocess.Popen(cmd)
                st.session_state.active_bot_type = 'alpaca'
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {e}")

        # BOUTON STOP
        if st.button("⏹️ ARRÊTER", disabled=not is_bot_running(), key="stop_alpaca", use_container_width=True):
            stop_bot()
            st.rerun()

    with col_status:
        # Affichage conditionnel du statut
        if is_bot_running() and st.session_state.active_bot_type == 'alpaca':
            st.success(f"✅ BOT SIGNAL EN LIGNE sur {choix_symbol}")
            st.markdown("Le bot scanne le marché... Vérifiez votre Telegram.")
        elif is_bot_running() and st.session_state.active_bot_type == 'binance':
            st.warning("⚠️ Le Bot Binance tourne actuellement. Arrêtez-le avant de lancer celui-ci.")
        else:
            st.info("Le bot est à l'arrêt.")

        # Affichage Compte Alpaca
        st.divider()
        st.subheader("Portefeuille Alpaca (Paper)")
        if connected:
            c1, c2 = st.columns(2)
            c1.metric("Equity", f"{float(account.equity)} $")
            c2.metric("Buying Power", f"{float(account.buying_power)} $")
        else:
            st.warning("Alpaca non connecté.")

# ==========================================
# ONGLET 2 : SIMULATION LOCALE (ZERO API KEY)
# ==========================================
with tab_binance: # On garde le nom de variable tab_binance pour pas casser le code
    st.header("🎮 Simulation Locale (Sans Risque)")
    st.caption("Ce bot utilise les données RÉELLES de Binance mais un portefeuille VIRTUEL sur votre PC.")
    st.success("✅ Aucune clé API nécessaire. Fonctionne immédiatement.")

    col_sim_conf, col_sim_stat = st.columns([1, 2])
    
    with col_sim_conf:
        # Configuration
        local_symbol = st.text_input("Paire (ex: BTC/USDT)", value="BTC/USDT", disabled=is_bot_running())
        local_amount = st.number_input("Quantité à Trader", value=0.001, format="%.4f", step=0.0001, disabled=is_bot_running())
        
        st.divider()
        
        # BOUTON START
        if st.button("🚀 LANCER LA SIMULATION", disabled=is_bot_running(), key="start_local", use_container_width=True):
            try:
                # On lance local_bot.py
                cmd = [sys.executable, "local_bot.py", "--symbol", local_symbol, "--amount", str(local_amount)]
                st.session_state.bot_process = subprocess.Popen(cmd)
                st.session_state.active_bot_type = 'local' # Nouveau type
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {e}")

        # BOUTON STOP
        if st.button("💀 STOPPER", disabled=not is_bot_running(), key="stop_local", use_container_width=True):
            stop_bot()
            st.rerun()
            
    with col_sim_stat:
        if is_bot_running() and st.session_state.active_bot_type == 'local':
            st.success(f"✅ SIMULATION EN COURS sur {local_symbol}")
            st.markdown(f"**Capital de départ :** 1000 USDT (Fictif)")
            st.markdown(f"**Mise par trade :** {local_amount} {local_symbol.split('/')[0]}")
            
            st.info("👇 Regardez le terminal VS Code ci-dessous pour voir le journal des transactions en direct.")
            
        elif is_bot_running():
            st.warning("⚠️ Un autre bot tourne déjà.")
        else:
            st.info("Le bot est à l'arrêt.")

# ==========================================
# ONGLET 3 : SIMULATION (Ton ancien code)
# ==========================================
with tab_simu:
    st.header("Simulation Réelle (Objectif 5 Jours / 1H)")
    st.warning("⚠️ Mode Sniper : Analyse sur 120 bougies horaires.")
    
    symbol = st.selectbox("Actif", ["BTC-USD", "ETH-USD", "NVDA", "AAPL"], index=0, key="sim_select")
    days = 5  
    timeframe = "1h" 
    
    if st.button("Lancer la Simulation", key="sim_btn"):
        try:
            with st.spinner("Analyse en cours..."):
                lookback = days + 10 
                hist = yf.download(symbol, period=f"{lookback}d", interval=timeframe)
                
                if not hist.empty:
                    if isinstance(hist.columns, pd.MultiIndex):
                        hist.columns = hist.columns.get_level_values(0)
                    
                    hist = hist[['Open', 'High', 'Low', 'Close', 'Volume']]
                    hist = hist.dropna()

                    eng = TradingEngine(symbol)
                    stats, bt = eng.run_backtest(hist)
                    
                    if stats['# Trades'] == 0:
                        st.warning("⚠️ Aucun trade détecté.")
                    
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Net Return", f"{stats['Return [%]']:.2f}%")
                    c2.metric("Win Rate", f"{stats['Win Rate [%]']:.1f}%")
                    c3.metric("Profit Factor", f"{stats['Profit Factor']:.2f}")
                    c4.metric("Number of Trades", int(stats['# Trades']))

                    st.subheader("Capital Evolution")
                    st.line_chart(stats['_equity_curve']['Equity'])

                    st.subheader("Transaction Report")
                    trades = stats['_trades']

                    if not trades.empty:
                        df_trades = trades.copy()
                        df_trades['PnL ($)'] = df_trades['PnL'].round(2)
                        df_trades['Return (%)'] = (df_trades['ReturnPct'] * 100).round(2)
                        df_trades['Type'] = df_trades['Size'].apply(lambda x: "🟢 LONG" if x > 0 else "🔴 SHORT")

                        cols = ['Type', 'EntryPrice', 'ExitPrice', 'PnL ($)', 'Return (%)']
                        df_trades = df_trades[cols]

                        def highlight_pnl(val):
                            try:
                                num = float(val)
                                color = 'green' if num > 0 else 'red'
                                return f'color: {color}'
                            except:
                                return None

                        st.dataframe(
                            df_trades.style.map(highlight_pnl, subset=['PnL($)', 'Return (%)']),
                            use_container_width=True
                        )
                    else:
                        st.info("Aucun trade n'a été ouvert sur cette période.")

        except Exception as e:
            st.error(f"Erreur d'affichage : {e}")