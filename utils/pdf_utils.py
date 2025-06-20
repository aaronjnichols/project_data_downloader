"""
PDF generation utilities for NOAA Atlas 14 precipitation frequency reports.
Creates professional PDFs with data tables and DDF/IDF curves.
"""
import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class NOAAPrecipitationReport:
    """Generate PDF reports for NOAA Atlas 14 precipitation frequency data"""
    
    def __init__(self):
        self.page_width = 8.5  # inches
        self.page_height = 11.0  # inches
        self.dpi = 300
        
        # Color scheme for different return periods (matching NOAA style)
        self.return_period_colors = {
            1: '#1f77b4',      # blue
            2: '#ff7f0e',      # orange  
            5: '#2ca02c',      # green
            10: '#d62728',     # red
            25: '#9467bd',     # purple
            50: '#8c564b',     # brown
            100: '#e377c2',    # pink
            200: '#7f7f7f',    # gray
            500: '#bcbd22',    # olive
            1000: '#17becf'    # cyan
        }
        
        # Duration colors for the second plot
        self.duration_colors = plt.cm.tab20(np.linspace(0, 1, 20))
    
    def generate_precipitation_report(self, processed_csv_path: str, metadata_path: str, 
                                    output_pdf_path: str) -> bool:
        """
        Generate a complete precipitation frequency report PDF
        
        Args:
            processed_csv_path: Path to processed precipitation frequency CSV
            metadata_path: Path to metadata JSON file
            output_pdf_path: Path for output PDF file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load data
            df = pd.read_csv(processed_csv_path)
            
            import json
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Create PDF
            with PdfPages(output_pdf_path) as pdf:
                # Page 1: Data table and metadata
                self._create_data_table_page(pdf, df, metadata)
                
                # Page 2: DDF curves
                self._create_ddf_curves_page(pdf, df, metadata)
            
            logger.info(f"Successfully generated precipitation frequency report: {output_pdf_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating precipitation frequency report: {e}")
            return False
    
    def _create_data_table_page(self, pdf: PdfPages, df: pd.DataFrame, metadata: Dict):
        """Create the first page with data table and metadata"""
        fig, ax = plt.subplots(figsize=(self.page_width, self.page_height))
        ax.axis('off')
        
        # Title
        title = "NOAA Atlas 14 Precipitation Frequency Estimates"
        fig.suptitle(title, fontsize=16, fontweight='bold', y=0.96)
        
        # Metadata section - positioned higher and made more compact
        meta_text = self._format_metadata_text(metadata)
        ax.text(0.05, 0.92, meta_text, transform=ax.transAxes, fontsize=9,
                verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle="round,pad=0.4", facecolor="lightgray", alpha=0.3))
        
        # Prepare table data
        table_data = self._prepare_table_data(df)
        
        # Create table - positioned lower to avoid overlap
        table = ax.table(cellText=table_data['data'],
                        colLabels=table_data['headers'],
                        cellLoc='center',
                        loc='center',
                        bbox=[0.05, 0.08, 0.9, 0.55])
        
        # Style the table
        table.auto_set_font_size(False)
        table.set_fontsize(7)
        table.scale(1, 1.2)
        
        # Header styling
        for i in range(len(table_data['headers'])):
            table[(0, i)].set_facecolor('#4472C4')
            table[(0, i)].set_text_props(weight='bold', color='white')
        
        # Alternate row colors
        for i in range(1, len(table_data['data']) + 1):
            if i % 2 == 0:
                for j in range(len(table_data['headers'])):
                    table[(i, j)].set_facecolor('#F2F2F2')
        
        # Footer note - positioned at the bottom
        footer_text = ("Notes: Precipitation frequency estimates are based on NOAA Atlas 14. PDS = Partial Duration Series. Values are in inches.\n"
                      "These estimates represent statistical averages and should be used with appropriate engineering judgment.")
        ax.text(0.05, 0.02, footer_text, transform=ax.transAxes, fontsize=7,
                verticalalignment='bottom', style='italic', wrap=True)
        
        pdf.savefig(fig, dpi=self.dpi, bbox_inches='tight')
        plt.close(fig)
    
    def _create_ddf_curves_page(self, pdf: PdfPages, df: pd.DataFrame, metadata: Dict):
        """Create the second page with DDF curves"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(self.page_width, self.page_height), 
                                       gridspec_kw={'height_ratios': [1, 1], 'hspace': 0.3})
        
        # Get return periods and durations
        return_periods = [col.replace('_year', '') for col in df.columns if '_year' in col]
        return_periods = [int(rp) for rp in return_periods]
        durations = df['Duration'].tolist()
        
        # Convert durations to numeric values for plotting (in hours)
        duration_hours = self._convert_durations_to_hours(durations)
        
        # Plot 1: Precipitation depth vs Duration for different return periods
        ax1.set_title('PDS-based depth-duration-frequency (DDF) curves\n' + 
                     f"Latitude: {metadata['centroid_coordinates']['latitude']:.4f}°, " +
                     f"Longitude: {metadata['centroid_coordinates']['longitude']:.4f}°", 
                     fontsize=12, pad=20)
        
        for rp in return_periods:
            col_name = f"{rp}_year"
            if col_name in df.columns:
                values = df[col_name].values
                color = self.return_period_colors.get(rp, '#333333')
                ax1.plot(duration_hours, values, 'o-', color=color, linewidth=2, 
                        markersize=4, label=f'{rp}')
        
        ax1.set_xlabel('Duration', fontsize=10)
        ax1.set_ylabel('Precipitation depth (in)', fontsize=10)
        ax1.set_xscale('log')
        ax1.grid(True, alpha=0.3)
        ax1.legend(title='Average recurrence\ninterval\n(years)', bbox_to_anchor=(1.05, 1), 
                  loc='upper left', fontsize=8)
        
        # Set x-axis labels
        ax1.set_xticks(duration_hours)
        ax1.set_xticklabels(durations, rotation=45, ha='right', fontsize=8)
        
        # Plot 2: Precipitation depth vs Return period for different durations
        ax2.set_title('Precipitation depth vs Average recurrence interval', fontsize=12, pad=20)
        
        for i, duration in enumerate(durations):
            values = []
            for rp in return_periods:
                col_name = f"{rp}_year"
                if col_name in df.columns:
                    values.append(df.loc[df['Duration'] == duration, col_name].iloc[0])
            
            if values:
                color = self.duration_colors[i % len(self.duration_colors)]
                ax2.plot(return_periods, values, 'o-', color=color, linewidth=1.5, 
                        markersize=3, label=duration)
        
        ax2.set_xlabel('Average recurrence interval (years)', fontsize=10)
        ax2.set_ylabel('Precipitation depth (in)', fontsize=10)
        ax2.set_xscale('log')
        ax2.grid(True, alpha=0.3)
        ax2.legend(title='Durations', bbox_to_anchor=(1.05, 1), loc='upper left', 
                  fontsize=7, ncol=2)
        
        # Footer with generation info
        footer_text = f"NOAA Atlas 14, Volume 1 - Version 5        Created (GMT): {datetime.now().strftime('%a %b %d %H:%M:%S %Y')}"
        fig.text(0.05, 0.02, footer_text, fontsize=8, style='italic')
        fig.text(0.95, 0.02, "Maps & aerials", fontsize=8, style='italic', ha='right')
        fig.text(0.5, 0.02, "Small scale terrain", fontsize=8, style='italic', ha='center')
        
        pdf.savefig(fig, dpi=self.dpi, bbox_inches='tight')
        plt.close(fig)
    
    def _format_metadata_text(self, metadata: Dict) -> str:
        """Format metadata information for display"""
        coords = metadata.get('centroid_coordinates', {})
        noaa_meta = metadata.get('noaa_metadata', {})
        data_summary = metadata.get('data_summary', {})
        
        lat = coords.get('latitude', 'Unknown')
        lon = coords.get('longitude', 'Unknown')
        download_date = metadata.get('download_timestamp', 'Unknown')
        
        # Format download date
        try:
            if download_date != 'Unknown':
                dt = datetime.strptime(download_date, '%Y%m%d_%H%M%S')
                download_date = dt.strftime('%Y-%m-%d %H:%M UTC')
        except:
            pass
        
        text = f"""Location: {lat}°, {lon}° | Project Area: {noaa_meta.get('project_area', 'Southwest')}
Data Type: {data_summary.get('data_type', 'Precipitation depth')} | Units: {data_summary.get('units', 'inches')}
Time Series: {noaa_meta.get('time_series_type', 'Partial duration')} | Durations: {data_summary.get('durations', 19)} | Return Periods: {data_summary.get('return_periods', 10)}
Downloaded: {download_date} | Source: NOAA Atlas 14 PFDS Volume 1 Version 5"""
        
        return text
    
    def _prepare_table_data(self, df: pd.DataFrame) -> Dict:
        """Prepare data for the precipitation frequency table"""
        # Headers
        headers = ['Duration'] + [col.replace('_year', '-yr') for col in df.columns if '_year' in col]
        
        # Data rows
        data = []
        for _, row in df.iterrows():
            row_data = [row['Duration']]
            for col in df.columns:
                if '_year' in col:
                    value = row[col]
                    if pd.notna(value):
                        row_data.append(f"{value:.3f}")
                    else:
                        row_data.append("N/A")
            data.append(row_data)
        
        return {'headers': headers, 'data': data}
    
    def _convert_durations_to_hours(self, durations: List[str]) -> List[float]:
        """Convert duration strings to hours for plotting"""
        hours = []
        for duration in durations:
            duration = duration.lower()
            if 'min' in duration:
                mins = float(duration.replace('-min', '').replace('min', ''))
                hours.append(mins / 60.0)
            elif 'hr' in duration:
                hrs = float(duration.replace('-hr', '').replace('hr', ''))
                hours.append(hrs)
            elif 'day' in duration:
                days = float(duration.replace('-day', '').replace('day', ''))
                hours.append(days * 24.0)
            else:
                hours.append(1.0)  # Default
        return hours


def generate_precipitation_pdf(processed_csv_path: str, metadata_path: str, 
                             output_pdf_path: str) -> bool:
    """
    Convenience function to generate a precipitation frequency PDF report
    
    Args:
        processed_csv_path: Path to processed precipitation frequency CSV
        metadata_path: Path to metadata JSON file  
        output_pdf_path: Path for output PDF file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        report_generator = NOAAPrecipitationReport()
        return report_generator.generate_precipitation_report(
            processed_csv_path, metadata_path, output_pdf_path
        )
    except Exception as e:
        logger.error(f"Error generating precipitation PDF: {e}")
        return False 