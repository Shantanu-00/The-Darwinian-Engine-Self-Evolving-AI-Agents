import streamlit as st

st.set_page_config(
    page_title="Darwinian Engine - Admin",
    page_icon="🧬",
    layout="wide"
)

st.title("🧬 Darwinian Engine — Admin Console")

st.markdown("""
## Create → Evolve → Govern AI Agents

Welcome to the Darwinian Engine administrative console. This platform enables you to:

- **Create** new agent lineages with custom genomes
- **Evolve** existing agents through mutation and feedback
- **Govern** agent behavior through version control and rollback

### Navigation

Use the sidebar to access:

- **The Lab** - Create new agent lineages and write genomes from scratch
- **Genome Editor** - Mutate existing agents and manage feedback tickets
- **Lineage** - Visualize evolution history and rollback versions
""")

st.divider()

st.info("Select a page from the sidebar to begin.")