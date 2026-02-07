from config import Config
import pandas as pd
import matplotlib
# Set backend to 'Agg' immediately to prevent GUI errors on servers (Railway/Linux)
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import io
import base64


#----- Generate Chart
def generate_chart_base64():
    """
    Generates a chart based on current Google Sheet data.
    """
    try:
        # 1. Fetch fresh data
        sheet = Config.get_google_sheet()
        if not sheet:
            print("❌ Chart Error: Could not connect to sheet.")
            return None
        # Fetch all records
        data = sheet.get_all_records()
        
        # DEBUG: Print the first record to ensure data is fresh/not cached
        # print("DEBUG - Fresh Data Sample:", data[:1]) 
        if not data:
            print("⚠️ Chart Error: No data returned from sheet.")
            return None
        # 2. Prepare DataFrame & Normalize Columns
        df = pd.DataFrame(data)
        
        # Convert all column names to lowercase to make the check case-insensitive
        # This handles 'Status', 'status', or 'STATUS' automatically.
        df.columns = df.columns.str.strip().str.lower()
        
        target_col = 'status'
        
        if target_col not in df.columns:
            print(f"⚠️ Chart Error: Column '{target_col}' not found. Available columns: {list(df.columns)}")
            return None
        # 3. Create the plot
        plt.clf() # Clear previous figures to prevent overlapping
        plt.figure(figsize=(8, 5))
        
        # Get value counts
        counts = df[target_col].value_counts()
        
        if counts.empty:
            print("⚠️ Chart Error: Column exists but has no data to plot.")
            return None
        
        # Plot with custom colors
        counts.plot(kind='bar', color=['#667eea', '#764ba2', '#28a745'])
        
        plt.title('Project Status Overview')
        plt.xlabel('Status')
        plt.ylabel('Count')
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # 4. Save to memory buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        
        # 5. Convert to Base64 String
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        
        # 6. Cleanup
        plt.close()
        
        return img_str
    except Exception as e:
        print(f"❌ Chart generation failed: {e}")
        return None
        
#---- Create Table
def generate_table_base64():
    """
    Generates a table image (PNG) based on current Google Sheet data.
    """
    try:
        sheet = Config.get_google_sheet()
        if not sheet:
            return None

        data = sheet.get_all_records()
        if not data:
            return None

        df = pd.DataFrame(data)
        
        # Create figure for the table
        plt.clf()
        fig, ax = plt.subplots(figsize=(10, 6)) # Adjust size as needed
        ax.axis('tight')
        ax.axis('off')
        
        # Create the table
        table = ax.table(
            cellText=df.values,
            colLabels=df.columns,
            cellLoc='center',
            loc='center',
            colWidths=[0.15] * len(df.columns)
        )
        
        # Style the table
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 1.5)
        
        # Add a nice header color
        for (i, j), cell in table.get_celld().items():
            if i == 0:
                cell.set_facecolor('#667eea')
                cell.set_text_props(weight='bold', color='white')

        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
        buf.seek(0)
        
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        plt.close()
        
        return img_str

    except Exception as e:
        print(f"❌ Table generation failed: {e}")
        return None
