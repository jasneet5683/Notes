from config import Config
import pandas as pd


#----- Generate Chart
def generate_chart_base64():
    """
    Generates a chart based on current Google Sheet data.
    No arguments required - fetches data internally.
    """
    try:
        # 1. Fetch fresh data directly
        sheet = Config.get_google_sheet()
        if not sheet:
            print("❌ Chart Error: Could not connect to sheet.")
            return None

        data = sheet.get_all_records()
        if not data:
            print("⚠️ Chart Error: No data in sheet.")
            return None

        # 2. Prepare DataFrame
        df = pd.DataFrame(data)
        
        # Ensure 'Status' column exists (flexible check)
        # If your column is named differently (e.g., 'Project Status'), update it here.
        if 'status' not in df.columns:
            print("⚠️ Chart Error: 'Status' column not found.")
            return None

        # 3. Create the plot
        plt.clf() # Clear previous figures
        plt.figure(figsize=(8, 5))
        
        counts = df['status'].value_counts()
        
        # Plot with some nice colors
        counts.plot(kind='bar', color=['#667eea', '#764ba2', '#28a745'])
        plt.title('Project Status Overview')
        plt.xlabel('Status')
        plt.ylabel('Count')
        plt.xticks(rotation=45) # Rotate labels if they are long
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
