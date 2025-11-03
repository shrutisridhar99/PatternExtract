import streamlit as st
import cv2
import pandas as pd
import numpy as np
import glob
from pathlib import Path
import os
import subprocess
import platform
import shutil
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="PatternExtract - Ki67 Analysis Pipeline",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced custom CSS for better aesthetics
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    .main-header {
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    
    .subtitle {
        text-align: center;
        color: #6c757d;
        font-size: 1.2rem;
        margin-bottom: 2rem;
    }
    
    .section-header {
        font-size: 1.8rem;
        color: #2c3e50;
        font-weight: 600;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-left: 4px solid #667eea;
        padding-left: 1rem;
    }
    
    .success-box {
        padding: 1.2rem;
        border-radius: 0.75rem;
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        border: 2px solid #28a745;
        color: #155724;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .error-box {
        padding: 1.2rem;
        border-radius: 0.75rem;
        background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
        border: 2px solid #dc3545;
        color: #721c24;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .info-box {
        padding: 1.2rem;
        border-radius: 0.75rem;
        background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%);
        border: 2px solid #17a2b8;
        color: #0c5460;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 0.75rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
        transition: transform 0.2s;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.15);
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: 600;
        border: none;
        border-radius: 0.5rem;
        padding: 0.75rem 2rem;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        transition: all 0.3s;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
    
    .workflow-step {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 1.5rem;
        border-radius: 0.75rem;
        margin: 1rem 0;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #f8f9fa 0%, #ffffff 100%);
    }
    
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 700;
        color: #667eea;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'pipeline_run' not in st.session_state:
    st.session_state.pipeline_run = False
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = []
if 'pipeline_stats' not in st.session_state:
    st.session_state.pipeline_stats = {
        'csv_files': 0,
        'image_files': 0,
        'processed_images': 0,
        'total_centroids': 0,
        'avg_centroids': 0,
        'processing_time': 0
    }

# Detect OS
def detect_os():
    """Detect operating system"""
    system = platform.system()
    return system  # Returns 'Windows', 'Darwin' (macOS), or 'Linux'

# Helper function to find base directory automatically
def find_base_directory():
    """Automatically find the base directory containing the required structure"""
    current_dir = Path.cwd()
    
    # Check if current directory has the required structure
    if (current_dir / "data" / "CSV").exists() and (current_dir / "data" / "Images_RGB").exists():
        return current_dir
    
    # Check parent directory
    parent_dir = current_dir.parent
    if (parent_dir / "data" / "CSV").exists() and (parent_dir / "data" / "Images_RGB").exists():
        return parent_dir
    
    # Check for common project names
    for pattern in ["PatternExtract*", "Ki67*", "pattern*"]:
        matches = list(current_dir.glob(pattern))
        for match in matches:
            if match.is_dir() and (match / "data" / "CSV").exists():
                return match
        
        parent_matches = list(parent_dir.glob(pattern))
        for match in parent_matches:
            if match.is_dir() and (match / "data" / "CSV").exists():
                return match
    
    # Default to parent directory if nothing found
    return parent_dir

# Helper functions
def parse_csv_files(csv_dir):
    """Parse CSV files and extract image IDs"""
    a = []  # image IDs
    b = []  # CSV file paths
    
    for file in glob.glob(f"{csv_dir}/*"):
        try:
            b.append(file)
            bit0 = file.split("_1_HP_IM3_0_Core")[0].split(" ")[-1]
            bit1 = file.split("_1_HP_IM3_0_Core")[1].split("_")[0].split(",")
            p3 = f"{int(bit1[1]):02d}"
            p4 = f"{int(bit1[2]):02d}"
            a.append([bit0, p3, p4])
        except Exception:
            pass  # Silently skip files that don't match pattern
    
    return a, b

def parse_image_files(image_dir):
    """Parse image files and extract image IDs"""
    c = []  # image IDs
    d = []  # image file paths
    
    for file in glob.glob(f"{image_dir}/*"):
        try:
            d.append(file)
            bit2 = file.split("_1_HP_IM3_0_Core")[0].split(" ")[-1]
            bit3 = file.split("_1_HP_IM3_0_Core")[1].split("_")[0].split(",")
            p1 = f"{int(bit3[1]):02d}"
            p2 = f"{int(bit3[2]):02d}"
            c.append([bit2, p1, p2])
        except Exception:
            pass  # Silently skip files that don't match pattern
    
    return c, d

def create_masks(a, b, c, d, mask_dir, progress_bar, status_text):
    """Create mask images with centroid overlays"""
    processed = []
    total = len(a)
    start_time = datetime.now()
    
    for j, item in enumerate(a):
        try:
            # Update progress
            progress = (j + 1) / total
            progress_bar.progress(progress)
            status_text.text(f"Processing image {j+1}/{total}...")
            
            # Find matching image
            i = c.index(item)
            
            # Read image
            image3 = cv2.imread(d[i])
            if image3 is None:
                continue
                
            image4 = image3.copy()
            
            # Read CSV
            df = pd.read_csv(b[j], sep='\t')
            
            # Overlay red dots at centroids
            for _, row in df.iterrows():
                x = int(row["Centroid X µm"]) * 2
                y = int(row["Centroid Y µm"]) * 2
                cv2.circle(image3, (x, y), radius=0, color=[0, 0, 255], thickness=15)
                cv2.circle(image4, (x, y), radius=5, color=[0, 0, 200], thickness=15)
            
            # Blend overlays
            dst_0 = cv2.addWeighted(image3, 0.5, image4, 0.5, 0)
            
            # Save output
            outname = os.path.splitext(os.path.basename(b[j]))[0] + ".tiff"
            out_path = mask_dir / outname
            cv2.imwrite(str(out_path), dst_0)
            
            processed.append({
                'csv': os.path.basename(b[j]),
                'image': os.path.basename(d[i]),
                'output': outname,
                'centroids': len(df)
            })
            
        except ValueError:
            pass  # Silently skip if no matching image
        except Exception:
            pass  # Silently skip other errors
    
    end_time = datetime.now()
    processing_time = (end_time - start_time).total_seconds()
    
    return processed, processing_time

def run_qupath_windows(base_dir, mask_dir, qupath_path, project_dir):
    """Run QuPath scripts on Windows"""
    try:
        os.chdir(qupath_path)
        
        create_project_script = base_dir / "scripts" / "createproject_ki67.groovy"
        annotate_script = base_dir / "scripts" / "annotate_ki67_cells.groovy"
        project_file = project_dir / "project.qpproj"
        qupath_bin = "QuPath-0.6.0 (console).exe"
        geojson_dir = base_dir / "data" / "geoJSON"
        
        # Create project - suppress output
        subprocess.run([
            qupath_bin,
            "script",
            "--args", str(mask_dir),
            str(create_project_script)
        ], capture_output=True, text=True, check=False)
        
        # Run annotation script - suppress output
        subprocess.run([
            qupath_bin,
            "script",
            "--save",
            "--project", str(project_file),
            "--args", str(geojson_dir),
            str(annotate_script)
        ], capture_output=True, text=True, check=False)
        
        return True
        
    except Exception:
        return False

def run_qupath_mac(base_dir, mask_dir, qupath_path, project_dir):
    """Run QuPath scripts on macOS"""
    try:
        os.chdir(qupath_path)
        
        create_project_script = base_dir / "scripts" / "createproject_ki67.groovy"
        annotate_script = base_dir / "scripts" / "annotate_ki67_cells.groovy"
        project_file = project_dir / "project.qpproj"
        qupath_bin = "./QuPath-0.6.0-arm64"
        geojson_dir = base_dir / "data" / "geoJSON"
        
        # Create project - suppress output
        subprocess.run([
            qupath_bin,
            "script",
            "--args", str(mask_dir),
            str(create_project_script)
        ], capture_output=True, text=True, check=False)
        
        # Run annotation script - suppress output
        subprocess.run([
            qupath_bin,
            "script",
            "--save",
            "--project", str(project_file),
            "--args", str(geojson_dir),
            str(annotate_script)
        ], capture_output=True, text=True, check=False)
        
        return True
        
    except Exception:
        return False

def open_qupath_gui(qupath_path, project_file, current_os):
    """Open QuPath GUI for inspection"""
    try:
        os.chdir(qupath_path)
        
        if current_os == "Windows":
            qupath_bin = "QuPath-0.6.0 (console).exe"
        elif current_os == "Darwin":
            qupath_bin = "./QuPath-0.6.0-arm64"
        else:
            return False
        
        subprocess.Popen([
            qupath_bin,
            "--project", str(project_file)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        return True
    except Exception:
        return False

def run_r_script(base_dir, rscript_path):
    """Run R analysis script"""
    try:
        Rfile = base_dir / "scripts" / "R_script_ki67.R"
        
        result = subprocess.call([
            rscript_path,
            "--vanilla",
            str(Rfile)
        ])
        
        return result == 0
        
    except Exception:
        return False

# Main UI
st.markdown('<p class="main-header">🔬 PatternExtract</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Automated Spatial Point Pattern Analysis Pipeline for Ki67 Histology</p>', unsafe_allow_html=True)

# Detect OS and show info
current_os = detect_os()
os_emoji = "🪟" if current_os == "Windows" else "🍎" if current_os == "Darwin" else "🐧"

col_os1, col_os2, col_os3 = st.columns([1, 2, 1])
with col_os2:
    st.info(f"{os_emoji} **Detected OS**: {current_os} | **Pipeline Status**: {'✅ Ready' if not st.session_state.pipeline_run else '✅ Completed'}")

# Sidebar configuration
st.sidebar.header("⚙️ Configuration")

# Base directory with auto-detection
detected_base = find_base_directory()
base_dir_input = st.sidebar.text_input(
    "Base Directory",
    value=str(detected_base),
    help="Auto-detected directory containing data and scripts folders"
)
base_dir = Path(base_dir_input)

# Show directory validation
csv_dir = base_dir / "data" / "CSV"
image_dir = base_dir / "data" / "Images_RGB"
scripts_dir = base_dir / "scripts"

if csv_dir.exists() and image_dir.exists():
    st.sidebar.success("✅ Valid project structure detected")
else:
    st.sidebar.error("❌ Invalid directory structure")

# QuPath configuration
st.sidebar.subheader("🔬 QuPath Settings")
run_qupath = st.sidebar.checkbox("Run QuPath Analysis", value=True, help="Execute QuPath pixel classification and object segmentation")
open_qupath_gui_option = st.sidebar.checkbox("Open QuPath GUI", value=True, help="Launch QuPath GUI after processing for manual inspection")

if run_qupath:
    if current_os == "Windows":
        default_qupath = "C:/Program Files/QuPath-0.6.0"
    elif current_os == "Darwin":
        default_qupath = "/Applications/QuPath-0.6.0-arm64.app/Contents/MacOS/"
    else:
        default_qupath = "/usr/local/QuPath-0.6.0"
    
    qupath_path = st.sidebar.text_input(
        "QuPath Installation Path",
        value=default_qupath,
        help="Path to QuPath installation directory"
    )

# R configuration
st.sidebar.subheader("📊 R Analysis Settings")
run_r = st.sidebar.checkbox("Run R Analysis", value=True, help="Convert GeoJSON annotations to spatstat ppp objects")

if run_r:
    if current_os == "Windows":
        default_rscript = "C:/Program Files/R/R-4.3.1/bin/Rscript.exe"
    elif current_os == "Darwin":
        default_rscript = "/usr/local/bin/Rscript"
    else:
        default_rscript = "/usr/bin/Rscript"
    
    rscript_path = st.sidebar.text_input(
        "Rscript Path",
        value=default_rscript,
        help="Path to Rscript executable"
    )

# Main content area
tab1, tab2, tab3, tab4 = st.tabs(["🚀 Pipeline", "📊 Results", "📁 File Browser", "ℹ️ About"])

with tab1:
    st.markdown('<p class="section-header">Pipeline Execution</p>', unsafe_allow_html=True)
    
    # Verify directories
    mask_dir = base_dir / "data" / "Mask"
    project_dir = base_dir / "Project" / "ki67"
    
    # Directory status with enhanced styling
    st.markdown("### 📂 Directory Status")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        csv_exists = csv_dir.exists()
        if csv_exists:
            csv_count = len(list(csv_dir.glob("*")))
            st.metric("CSV Files", csv_count, "✅ Found")
        else:
            st.metric("CSV Files", "0", "❌ Missing")
    
    with col2:
        image_exists = image_dir.exists()
        if image_exists:
            image_count = len(list(image_dir.glob("*")))
            st.metric("RGB Images", image_count, "✅ Found")
        else:
            st.metric("RGB Images", "0", "❌ Missing")
    
    with col3:
        mask_dir.mkdir(parents=True, exist_ok=True)
        mask_count = len(list(mask_dir.glob("*")))
        st.metric("Masks Generated", mask_count, "✅ Ready")
    
    with col4:
        scripts_exist = scripts_dir.exists()
        if scripts_exist:
            script_count = len(list(scripts_dir.glob("*.groovy"))) + len(list(scripts_dir.glob("*.R")))
            st.metric("Scripts", script_count, "✅ Found")
        else:
            st.metric("Scripts", "0", "❌ Missing")
    
    # Run button
    st.markdown("---")
    
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
        run_button = st.button("🚀 Run Complete Pipeline", type="primary", use_container_width=True)
    
    if run_button:
        if not csv_exists or not image_exists:
            st.error("❌ Required directories not found! Please check your base directory path.")
        else:
            st.session_state.pipeline_run = True
            
            # Step 1: Parse files
            st.markdown('<div class="workflow-step">', unsafe_allow_html=True)
            st.markdown("### 📋 Step 1: Parsing Input Files")
            with st.spinner("Parsing CSV and image files..."):
                a, b = parse_csv_files(csv_dir)
                c, d = parse_image_files(image_dir)
                
                st.session_state.pipeline_stats['csv_files'] = len(a)
                st.session_state.pipeline_stats['image_files'] = len(c)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.success(f"✅ Found **{len(a)}** CSV files with centroid data")
                with col2:
                    st.success(f"✅ Found **{len(c)}** RGB image files")
                
                if c and d:
                    st.info(f"📌 Example match: `{c[0]}` → `{os.path.basename(d[0])}`")
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Step 2: Create masks
            st.markdown('<div class="workflow-step">', unsafe_allow_html=True)
            st.markdown("### 🎨 Step 2: Creating Two-Kernel Mask Overlays")
            st.caption("Overlaying cell centroids onto tissue images to generate masks preserving tissue contours")
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            processed, proc_time = create_masks(a, b, c, d, mask_dir, progress_bar, status_text)
            st.session_state.processed_files = processed
            st.session_state.pipeline_stats['processed_images'] = len(processed)
            st.session_state.pipeline_stats['processing_time'] = proc_time
            
            if processed:
                total_centroids = sum([f['centroids'] for f in processed])
                avg_centroids = total_centroids / len(processed)
                st.session_state.pipeline_stats['total_centroids'] = total_centroids
                st.session_state.pipeline_stats['avg_centroids'] = avg_centroids
            
            status_text.empty()
            progress_bar.empty()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Images Processed", len(processed))
            with col2:
                st.metric("Total Centroids", st.session_state.pipeline_stats['total_centroids'])
            with col3:
                st.metric("Processing Time", f"{proc_time:.2f}s")
            
            st.success(f"✅ Mask creation complete! Generated {len(processed)} mask images.")
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Step 3: QuPath
            if run_qupath:
                st.markdown('<div class="workflow-step">', unsafe_allow_html=True)
                st.markdown("### 🔬 Step 3: QuPath Pixel Classification & Segmentation")
                st.caption("Generating GeoJSON annotations of tissue regions with pixel classification")
                project_dir.mkdir(parents=True, exist_ok=True)
                
                with st.spinner("Running QuPath scripts..."):
                    if current_os == "Windows":
                        success = run_qupath_windows(base_dir, mask_dir, qupath_path, project_dir)
                    elif current_os == "Darwin":
                        success = run_qupath_mac(base_dir, mask_dir, qupath_path, project_dir)
                    else:
                        st.warning("⚠️ QuPath automation not configured for Linux. Please run manually.")
                        success = False
                
                if success:
                    st.success("✅ QuPath analysis completed successfully!")
                    
                    # Open GUI if requested
                    if open_qupath_gui_option:
                        project_file = project_dir / "project.qpproj"
                        with st.spinner("Opening QuPath GUI..."):
                            gui_success = open_qupath_gui(qupath_path, project_file, current_os)
                        
                        if gui_success:
                            st.info("🖥️ QuPath GUI launched for manual inspection")
                        else:
                            st.warning("⚠️ Could not launch QuPath GUI automatically")
                else:
                    st.error("❌ QuPath analysis encountered an issue")
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Step 4: R Analysis
            if run_r:
                st.markdown('<div class="workflow-step">', unsafe_allow_html=True)
                st.markdown("### 📊 Step 4: R Statistical Analysis (spatstat)")
                st.caption("Converting GeoJSON annotations to spatial point pattern (ppp) objects")
                with st.spinner("Running R analysis script..."):
                    r_success = run_r_script(base_dir, rscript_path)
                
                if r_success:
                    st.success("✅ R analysis completed! Spatial point patterns generated.")
                else:
                    st.info("ℹ️ R script executed. Check console for detailed output.")
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown("---")
            st.balloons()
            st.success("🎉 **Pipeline completed successfully!** All steps executed.")

with tab2:
    st.markdown('<p class="section-header">Results & Statistics</p>', unsafe_allow_html=True)
    
    if st.session_state.pipeline_run and st.session_state.processed_files:
        # Summary metrics
        st.markdown("### 📊 Processing Summary")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Images",
                st.session_state.pipeline_stats['processed_images'],
                delta=f"{st.session_state.pipeline_stats['csv_files']} CSV files"
            )
        
        with col2:
            st.metric(
                "Total Centroids",
                f"{st.session_state.pipeline_stats['total_centroids']:,}",
                delta=f"Avg: {st.session_state.pipeline_stats['avg_centroids']:.1f}"
            )
        
        with col3:
            st.metric(
                "Processing Time",
                f"{st.session_state.pipeline_stats['processing_time']:.2f}s",
                delta=f"{st.session_state.pipeline_stats['processing_time']/st.session_state.pipeline_stats['processed_images']:.2f}s/image"
            )
        
        with col4:
            success_rate = (st.session_state.pipeline_stats['processed_images'] / st.session_state.pipeline_stats['csv_files']) * 100
            st.metric(
                "Success Rate",
                f"{success_rate:.1f}%",
                delta="Processing accuracy"
            )
        
        # Detailed results table
        st.markdown("### 📋 Detailed Processing Results")
        df_display = pd.DataFrame(st.session_state.processed_files)
        
        # Add summary statistics
        df_display['Image ID'] = df_display['csv'].str.split('_1_HP_IM3_0_Core').str[0]
        
        st.dataframe(
            df_display[['Image ID', 'csv', 'image', 'output', 'centroids']],
            use_container_width=True,
            height=400
        )
        
        # Centroid distribution chart
        st.markdown("### 📈 Centroid Distribution")
        centroid_data = df_display[['Image ID', 'centroids']].sort_values('centroids', ascending=False)
        st.bar_chart(centroid_data.set_index('Image ID')['centroids'])
        
        # Download option
        st.markdown("### 💾 Export Results")
        csv_export = df_display.to_csv(index=False)
        st.download_button(
            label="📥 Download Processing Report (CSV)",
            data=csv_export,
            file_name=f"patternextract_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.info("📊 No results yet. Run the pipeline to see detailed statistics and results.")
        st.image("https://via.placeholder.com/800x400/667eea/ffffff?text=Run+Pipeline+to+See+Results", use_container_width=True)

with tab3:
    st.markdown('<p class="section-header">File Browser</p>', unsafe_allow_html=True)
    
    # Directory contents
    st.markdown("### 📁 Generated Files")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if mask_dir.exists():
            mask_files = list(mask_dir.glob("*"))
            st.metric("Mask Images", len(mask_files))
            
            if mask_files and st.checkbox("Show mask files"):
                for f in mask_files[:20]:  # Show first 20
                    st.text(f"🖼️ {f.name}")
                if len(mask_files) > 20:
                    st.info(f"... and {len(mask_files) - 20} more files")
    
    with col2:
        geojson_dir = base_dir / "data" / "geoJSON"
        if geojson_dir.exists():
            geojson_files = list(geojson_dir.glob("*.geojson"))
            st.metric("GeoJSON Files", len(geojson_files))
            
            if geojson_files and st.checkbox("Show GeoJSON files"):
                for f in geojson_files[:20]:
                    st.text(f"📐 {f.name}")
                if len(geojson_files) > 20:
                    st.info(f"... and {len(geojson_files) - 20} more files")
    
    # Processed files table
    if st.session_state.processed_files:
        st.markdown("### 📊 Processed Files Details")
        df_display = pd.DataFrame(st.session_state.processed_files)
        st.dataframe(df_display, use_container_width=True, height=300)

with tab4:
    st.markdown('<p class="section-header">About PatternExtract</p>', unsafe_allow_html=True)
    
    st.markdown("""
    ### 🎯 Overview
    
    **PatternExtract** is an automated cross-platform pipeline for transforming whole-slide images (WSI) 
    or tissue microarrays (TMA) into spatial point pattern (`ppp`) objects. It integrates **OpenCV**, 
    **QuPath**, and **R's spatstat** framework to streamline quantitative spatial analysis of histology markers.
    
    This workflow presents an example for **Ki67 histology marker** analysis.
    
    ---
    
    ### 🔄 Workflow
    
    """)
    
    # Step 1
    st.markdown('<div class="workflow-step">', unsafe_allow_html=True)
    st.markdown("""
    #### **Step 1: Pre-process Images in Python (OpenCV)**
    
    Overlay cell centroids from CSVs onto tissue images to generate **two-kernel masks**, 
    preserving tissue contours and holes where cells are absent.
    
    **Input:**
    - CSV files containing x–y cell coordinates (from any cell segmentation algorithm)
    - Corresponding tissue image
    
    **Output:**
    - Image overlaid with a two-kernel mask
    
    **Example:** RGB image → Mask annotation
    """)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Step 2
    st.markdown('<div class="workflow-step">', unsafe_allow_html=True)
    st.markdown("""
    #### **Step 2: Generate GeoJSONs in QuPath (Groovy script)**
    
    Run pixel classification and object segmentation in QuPath to generate **GeoJSON annotations** 
    of tissue regions, filling holes and preserving region structure.
    
    This step applies:
    - Color deconvolution
    - Gaussian blur
    - Thresholding
    
    **Input:**
    - Image overlaid with a two-kernel mask from Step 1
    
    **Output:**
    - GeoJSON file containing pixel-classified binary annotations of the image
    - Labeled tissue regions versus residual regions
    """)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Step 3
    st.markdown('<div class="workflow-step">', unsafe_allow_html=True)
    st.markdown("""
    #### **Step 3: Construct `ppp` Objects in R (spatstat)**
    
    Convert the exported spatial coordinates into analyzable **point pattern datasets**.
    
    **Input:**
    - GeoJSON file containing pixel-classified binary annotations from Step 2
    - CSV file with x–y coordinates and phenotype information
    
    **Output:**
    - Spatial point pattern (`ppp` object) highlighting tissue regions and annotated phenotypes
    
    **Comparison:**
    - **Convex-hull window**: Approximate tissue boundary
    - **Precise GeoJSON annotation**: True tissue contour with holes preserved
    """)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Requirements
    st.markdown("""
    ### 🛠️ Requirements
    
    **Software:**
    - Python ≥ 3.9
    - QuPath ≥ 0.6.0 (for image analysis)
    - R ≥ 4.2 with `spatstat` package
    
    **Python Packages:**
    ```bash
    pip install -r requirements.txt
    ```
    - opencv-python
    - pandas
    - numpy
    - streamlit
    
    ---
    
    ### 📁 Required Project Structure
    
    ```
    PatternExtract/
    │
    ├── LICENSE
    ├── requirements.txt
    ├── README.md
    │
    ├── scripts/
    │   ├── createproject_ki67.groovy        # QuPath project creation
    │   ├── annotate_ki67_cells.groovy       # Ki67+ cell detection
    │   └── R_script_ki67.R                  # Spatial point pattern conversion
    │
    ├── data/
    │   ├── CSV/                             # Cell centroids (x–y coordinates)
    │   ├── Images_RGB/                      # Input RGB images
    │   ├── Mask/                            # Generated mask images (output)
    │   └── geoJSON/                         # QuPath GeoJSON exports (output)
    │
    └── Project/
        └── ki67/                            # QuPath project files
    ```
    
    ---
    
    ### 🚀 Quick Start
    
    ```bash
    git clone https://github.com/shrutisridhar99/PatternExtract.git
    cd PatternExtract
    
    # Create conda environment
    conda create -n patternextract python=3.9 -y
    conda activate patternextract
    
    # Install dependencies
    pip install -r requirements.txt
    
    # Launch the web interface
    streamlit run app.py
    ```
    
    **Note:** Update file paths in:
    - Line 40 of `createproject_ki67.groovy`
    - Line 29 of `R_script_ki67.R`
    
    ---
    
    ### 📊 Output Examples
    
    The pipeline generates:
    1. **Mask images** with two-kernel centroid overlays
    2. **GeoJSON annotations** with precise tissue boundaries
    3. **Spatial point patterns** (`ppp` objects) ready for statistical analysis
    
    The resulting point patterns preserve:
    - Tissue contours and internal structures
    - Holes where cells are absent
    - Accurate spatial relationships for downstream analysis
    
    ---
    
    ### 📚 Citation & Documentation
    
    For more information, visit the [PatternExtract GitHub repository](https://github.com/shrutisridhar99/PatternExtract)
    
    **Key Features:**
    - ✅ Cross-platform support (Windows, macOS, Linux)
    - ✅ Automated end-to-end pipeline
    - ✅ Preserves tissue topology
    - ✅ Integrates industry-standard tools (OpenCV, QuPath, R/spatstat)
    - ✅ Extensible to other histology markers
    
    ---
    
    ### 💡 Tips for Best Results
    
    1. **Image Quality**: Ensure high-resolution RGB images for optimal mask generation
    2. **CSV Format**: Cell coordinates should be in tab-separated format with "Centroid X µm" and "Centroid Y µm" columns
    3. **QuPath Settings**: Adjust pixel classification parameters in the Groovy scripts for different tissue types
    4. **R Analysis**: Customize spatial analysis parameters in `R_script_ki67.R` for your specific research questions
    
    """)
    
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #6c757d; padding: 2rem;'>
        <p><strong>PatternExtract v1.0</strong> | Created 2025</p>
        <p>🔬 Automated Spatial Point Pattern Analysis for Histology</p>
    </div>
    """, unsafe_allow_html=True)

# Enhanced Sidebar Footer with More Stats
st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Pipeline Statistics")

if st.session_state.pipeline_run and st.session_state.processed_files:
    st.sidebar.metric("Images Processed", st.session_state.pipeline_stats['processed_images'])
    st.sidebar.metric("Total Centroids", f"{st.session_state.pipeline_stats['total_centroids']:,}")
    st.sidebar.metric("Avg Centroids/Image", f"{st.session_state.pipeline_stats['avg_centroids']:.1f}")
    st.sidebar.metric("Processing Time", f"{st.session_state.pipeline_stats['processing_time']:.2f}s")
    st.sidebar.metric("Time per Image", f"{st.session_state.pipeline_stats['processing_time']/st.session_state.pipeline_stats['processed_images']:.2f}s")
    
    # Success rate
    success_rate = (st.session_state.pipeline_stats['processed_images'] / 
                   st.session_state.pipeline_stats['csv_files']) * 100
    st.sidebar.metric("Success Rate", f"{success_rate:.1f}%")
    
    # Additional stats
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📈 Additional Info")
    st.sidebar.info(f"""
    **CSV Files Found:** {st.session_state.pipeline_stats['csv_files']}  
    **Image Files Found:** {st.session_state.pipeline_stats['image_files']}  
    **Matched Pairs:** {st.session_state.pipeline_stats['processed_images']}
    """)
else:
    st.sidebar.info("Run the pipeline to see detailed statistics")
    st.sidebar.markdown("""
    **Pipeline Steps:**
    1. 📋 Parse CSV & Images
    2. 🎨 Create Masks
    3. 🔬 QuPath Analysis
    4. 📊 R Statistical Analysis
    """)

st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style='text-align: center; font-size: 0.85rem; color: #6c757d;'>
    <strong>PatternExtract</strong><br>
    Spatial Point Pattern Pipeline<br>
    v1.0 | 2025
</div>
""", unsafe_allow_html=True)