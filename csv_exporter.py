import pandas as pd
import os
import logging
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

class CSVExporter:
    def __init__(self, output_file: str):
        self.output_file = output_file
        self.ensure_output_directory()
    
    def ensure_output_directory(self):
        """Create output directory if it doesn't exist"""
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
    
    def export_invoices(self, invoice_data: List[Dict]) -> bool:
        """Export invoice data to CSV"""
        if not invoice_data:
            logger.warning("No invoice data to export")
            return False
        
        try:
            # Create DataFrame with specific column order
            columns = [
                'email_subject',
                'vendor', 
                'invoice_number',
                'amount',
                'currency',
                'due_date',
                'invoice_date',
                'ocr',
                'description',
                'email_sender',
                'email_date',
                'confidence',
                'processed_date',
                'email_id'
            ]
            
            df = pd.DataFrame(invoice_data)
            
            # Ensure all columns exist
            for col in columns:
                if col not in df.columns:
                    df[col] = ''
            
            # Reorder columns
            df = df[columns]
            
            # Sort by email date (newest first)
            df['email_date'] = pd.to_datetime(df['email_date'], errors='coerce')
            df = df.sort_values('email_date', ascending=False)
            
            # Export to CSV with proper encoding for Swedish characters
            df.to_csv(self.output_file, index=False, encoding='utf-8-sig')
            
            logger.info(f"✓ Exported {len(invoice_data)} invoices to {self.output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            return False
    
    def load_existing_invoices(self) -> List[str]:
        """Load existing invoice IDs to avoid duplicates"""
        if not os.path.exists(self.output_file):
            return []
        
        try:
            df = pd.read_csv(self.output_file, encoding='utf-8-sig')
            return df['email_id'].tolist()
        except Exception as e:
            logger.warning(f"Could not load existing invoices: {e}")
            return []
    
    def append_invoices(self, new_invoice_data: List[Dict]) -> bool:
        """Append new invoices to existing CSV, avoiding duplicates"""
        if not new_invoice_data:
            return False
        
        try:
            existing_ids = self.load_existing_invoices()
            
            # Filter out duplicates
            filtered_data = [
                invoice for invoice in new_invoice_data 
                if invoice['email_id'] not in existing_ids
            ]
            
            if not filtered_data:
                logger.info("No new invoices to add (all were duplicates)")
                return True
            
            if os.path.exists(self.output_file):
                # Load existing data and append
                existing_df = pd.read_csv(self.output_file, encoding='utf-8-sig')
                new_df = pd.DataFrame(filtered_data)
                
                # Ensure same columns
                for col in existing_df.columns:
                    if col not in new_df.columns:
                        new_df[col] = ''
                
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                
                # Sort by email date
                combined_df['email_date'] = pd.to_datetime(combined_df['email_date'], errors='coerce')
                combined_df = combined_df.sort_values('email_date', ascending=False)
                
                combined_df.to_csv(self.output_file, index=False, encoding='utf-8-sig')
                logger.info(f"✓ Appended {len(filtered_data)} new invoices to {self.output_file}")
            else:
                # Create new file
                self.export_invoices(filtered_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Error appending to CSV: {e}")
            return False
    
    def get_summary_stats(self) -> Dict:
        """Get summary statistics of exported invoices"""
        if not os.path.exists(self.output_file):
            return {}
        
        try:
            df = pd.read_csv(self.output_file, encoding='utf-8-sig')
            
            # Convert amount to numeric, handling errors
            df['amount_numeric'] = pd.to_numeric(df['amount'], errors='coerce')
            
            # Basic stats
            stats = {
                'total_invoices': len(df),
                'total_amount': df['amount_numeric'].sum(),
                'avg_amount': df['amount_numeric'].mean(),
                'currency_breakdown': df['currency'].value_counts().to_dict(),
                'top_vendors': df['vendor'].value_counts().head(5).to_dict(),
                'date_range': {
                    'earliest': df['email_date'].min(),
                    'latest': df['email_date'].max()
                }
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error generating summary stats: {e}")
            return {}