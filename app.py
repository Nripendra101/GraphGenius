import streamlit as st
from neo4j import GraphDatabase
from pyvis.network import Network
import pandas as pd
import streamlit.components.v1 as components
import os
from dotenv import load_dotenv
# === Neo4j Configuration ===
# uri = "bolt://localhost:7687"
# username = "neo4j"
# password = "neo4j@123"  # 👈 Replace with your password
# === Load Environment Variables ===
load_dotenv()

uri = os.getenv("NEO4J_URI")
username = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(uri, auth=(username, password))

driver = GraphDatabase.driver(uri, auth=(username, password))

# === Utility: Convert Neo4j Node/Rel/Complex values into readable strings ===
def safe_string(value):
    if hasattr(value, 'id'):  # Neo4j Node or Relationship
        value_dict = {
            'type': value.__class__.__name__,
            'id': value.id,
            **dict(value.items())
        }
        if value.__class__.__name__ == 'Relationship':
            value_dict['start'] = value.start_node.id
            value_dict['end'] = value.end_node.id
            value_dict['label'] = value.type
        if value.__class__.__name__ == 'Node':
            value_dict['labels'] = list(value.labels)
        return str(value_dict)
    elif isinstance(value, dict):
        return str(value)
    else:
        return str(value)

# === Function: Run Cypher and Build Graph ===
def run_cypher_and_build_graph(query):
    net = Network(height="600px", width="100%", bgcolor="#f5f5f5", font_color="black", directed=True)
    net.force_atlas_2based(gravity=-50)
    nodes_added = set()

    with driver.session() as session:
        result = session.run(query)
        for record in result:
            for value in record.values():
                if value.__class__.__name__ == "Node":
                    node_id = str(value.id)
                    label = list(value.labels)[0] if value.labels else "Node"
                    title = "<br>".join([f"{k}: {v}" for k, v in dict(value.items()).items()])
                    if node_id not in nodes_added:
                        net.add_node(node_id, label=label, title=title)
                        nodes_added.add(node_id)
                elif value.__class__.__name__ == "Relationship":
                    start = str(value.start_node.id)
                    end = str(value.end_node.id)
                    rel_type = value.type
                    net.add_edge(start, end, label=rel_type)

    return net

# === Function: Run Cypher and Return Clean Table ===
def run_cypher_return_table(query):
    with driver.session() as session:
        result = session.run(query)
        cleaned_records = []
        for record in result:
            cleaned_record = {}
            for key, value in record.items():
                cleaned_record[key] = safe_string(value)
            cleaned_records.append(cleaned_record)
        return cleaned_records

# === Streamlit UI ===
st.set_page_config(page_title="Neo4j Visual Explorer", layout="wide")
st.title("🧠 Neo4j Knowledge Graph Explorer")

# Query input
query = st.text_area("📥 Enter your Cypher Query", "MATCH (a)-[r]->(b) RETURN a, r, b LIMIT 50")

col1, col2 = st.columns(2)

with col1:
    if st.button("👁️ Visualize as Graph"):
        try:
            net = run_cypher_and_build_graph(query)
            net.save_graph("graph.html")
            HtmlFile = open("graph.html", "r", encoding="utf-8")
            source_code = HtmlFile.read()
            components.html(source_code, height=600, scrolling=True)
        except Exception as e:
            st.error(f"Graph error: {e}")

with col2:
    if st.button("📊 Show as Table"):
        try:
            data = run_cypher_return_table(query)
            if data:
                df = pd.DataFrame(data)
                st.dataframe(df)
            else:
                st.info("No data found.")
        except Exception as e:
            st.error(f"Cypher error: {e}")
