import streamlit as st
from pathlib import Path
import base64
from deadlock_sim import avash      #name of function that runs the whole deadlock simulation
from cpu_scheduler import din       #name of function that runs the whole cpu scheduling simulation
from Virtual_memory import anurodh
from Paging_module import aseem

st.set_page_config(
    page_title="OS Simulator",
    page_icon="Ω",
    layout="wide",
    initial_sidebar_state="expanded"
)

if "active_module" not in st.session_state:
    st.session_state.active_module = "Hub"

# Helper function to switch modules programmatically
def navigate_to(module_name):
    st.session_state.active_module = module_name

def png_as_data_uri(image_path):
    image_bytes = image_path.read_bytes()
    encoded_image = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    return (
        "data:image/png;base64,"
        + encoded_image
    )

with st.sidebar:

    logo_path = Path(__file__).parent/ "logoSidebar.png"
    if logo_path.exists():
        logo_uri = png_as_data_uri(logo_path)

    st.markdown(
    f"""
    <div style="background-color:#4F3E6D; padding:15px; border-radius:10px; text-align:center; margin-bottom:20px;">
        <img src="{logo_uri}" style="width:150px; height:auto; display:block; margin:0 auto 0px auto;">
        <h1 style="color:#FDC215; margin:0; font-family:sans-serif; font-size:24px; letter-spacing:1px;">
                SIMULATOR
        </h1>
    </div>
    """, 
        unsafe_allow_html=True
    )
    st.write("### Quick Access Links")
    if st.button("Main Dashboard Menu", use_container_width=True):
        navigate_to("Hub")
        
    st.divider()
    st.caption("Simulation Modules:")
    if st.button("CPU Scheduler", use_container_width=True):
        navigate_to("cpu")
    if st.button("Virtual Memory", use_container_width=True):
        navigate_to("disk")
    if st.button("Deadlock Engine", use_container_width=True):
        navigate_to("deadlock_sim.py")
    if st.button("VFS & Disk Manager", use_container_width=True):
        st.write("to be implemented")
    
if st.session_state.active_module == "Hub":
    st.title("OS Simulation Menu")
    st.markdown("Pick one of the following topics to simulate")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("### CPU Scheduling")
        st.write("Simulating task scheduling in a CPU to investigate efficiency of FCFS, SJF, and Round Robin scheduling algorithms with and without preemption.")
        if st.button("Launch CPU Module", key="btn_cpu", use_container_width=True):
            navigate_to("cpu")
            st.rerun()

        st.warning("### Deadlock Avoidance")
        st.write("Banker's Algorithm simulation for illustrating proper resource allocation and deadlock prevention")
        if st.button("Launch Deadlock Module", key="btn_deadlock", use_container_width=True):
            navigate_to("deadlock_sim.py")
            st.rerun()
    with col2:
        st.success("### Paging")
        st.write("FIFO vs. LRU page replacement performance comparision along with other related variable comparisions")
        if st.button("Launch Paging Module", key="btn_mem", use_container_width=True):
            navigate_to("memory")
            st.rerun()

        st.error("### VFS & Disk Scheduling")
        st.write("Interact with a customized mock terminal tree alongside real-time mechanical SCAN and SSTF visualizers.")
        if st.button("Launch VFS & Disk Module", key="btn_disk", use_container_width=True):
            navigate_to("disk")
            st.rerun()

elif st.session_state.active_module == "cpu":
    st.title("CPU Scheduling Simulation Workspace")
    if st.button("Return to Main Menu"): navigate_to("Hub"); st.rerun()
    st.divider()
    din()

elif st.session_state.active_module == "memory":
    st.title("Virtual Memory & Demand Paging Workspace")
    if st.button("Return to Main Menu"): navigate_to("Hub"); st.rerun()
    st.divider()
    aseem()


# ROUTE: DEADLOCK ENGINE WORKSPACE
elif st.session_state.active_module == "deadlock_sim.py":
    st.title("Concurrency & Deadlock Avoidance Workspace")
    if st.button("Return to Main Menu"): navigate_to("Hub"); st.rerun()
    st.divider()
    avash()
    # a previous functional version was being used but is no longer used because of graphics mismatch (the graph was not implemented)

elif st.session_state.active_module == "disk":
    st.title("VFS & Disk Scheduling Workspace")
    if st.button("Return to Main Menu"): navigate_to("Hub"); st.rerun()
    st.divider()
    anurodh()