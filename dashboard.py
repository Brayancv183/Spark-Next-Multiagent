import json
import os
import streamlit as st
import pandas as pd
import plotly.express as px

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
HISTORIAL_PATH = os.path.join(DATA_DIR, "historial_clientes.json")

st.set_page_config(page_title="Dashboard - Centro de Contacto", layout="wide")
st.title("Dashboard del Centro de Contacto")
st.caption("Datos extraidos del historial de conversaciones del bot multiagente")

def cargar_datos():
    if not os.path.exists(HISTORIAL_PATH):
        return pd.DataFrame()
    with open(HISTORIAL_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    rows = []
    for cedula, info in data.items():
        for inc in info["incidencias"]:
            rows.append({
                "cliente": info["nombre"],
                "cedula": cedula,
                "tipo": inc["tipo"],
                "descripcion": inc["descripcion"],
                "fecha": inc["fecha"],
                "mensaje_cliente": inc["mensaje_cliente"],
            })
    return pd.DataFrame(rows)

df = cargar_datos()
refresh = st.button("Actualizar datos")

if df.empty:
    st.info("No hay datos aun. Usa el bot de Telegram para registrar conversaciones.")
    st.stop()

total_clientes = df["cedula"].nunique()
total_incidencias = len(df)
top_tipo = df["tipo"].mode().iloc[0] if not df.empty else "-"
ultima_fecha = df["fecha"].max()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Clientes con incidencias", total_clientes)
col2.metric("Total incidencias", total_incidencias)
col3.metric("Problema mas frecuente", top_tipo)
col4.metric("Ultima incidencia", ultima_fecha[:10])

st.subheader("Incidencias por tipo")
tipo_counts = df["tipo"].value_counts().reset_index()
tipo_counts.columns = ["tipo", "cantidad"]
fig1 = px.bar(tipo_counts, x="tipo", y="cantidad", color="tipo",
              title="Distribucion de problemas reportados")
st.plotly_chart(fig1, use_container_width=True)

st.subheader("Incidencias por cliente")
cliente_counts = df["cliente"].value_counts().reset_index()
cliente_counts.columns = ["cliente", "cantidad"]
fig2 = px.bar(cliente_counts, x="cliente", y="cantidad", color="cliente",
              title="Clientes con mas incidencias")
st.plotly_chart(fig2, use_container_width=True)

st.subheader("Evolucion temporal")
df["fecha_dt"] = pd.to_datetime(df["fecha"])
df["fecha_dia"] = df["fecha_dt"].dt.date
temporal = df.groupby("fecha_dia").size().reset_index(name="cantidad")
fig3 = px.line(temporal, x="fecha_dia", y="cantidad",
               title="Incidencias por dia", markers=True)
st.plotly_chart(fig3, use_container_width=True)

st.subheader("Detalle de incidencias")
st.dataframe(
    df[["fecha", "cliente", "tipo", "mensaje_cliente"]].sort_values("fecha", ascending=False),
    use_container_width=True,
    hide_index=True,
)
