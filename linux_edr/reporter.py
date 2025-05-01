import json
import logging
from typing import List, Dict, Any, Optional, Union
from openai import OpenAI
from .models import SummaryReport, Cell, Block, DailyReport, WeeklyReport, MonthlyReport

logger = logging.getLogger(__name__)

class Reporter:
    def __init__(self, api_key: str = None, output_file: str = None, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key) if api_key else None
        self.output_file = output_file
        self.model = model

    def save_json(self, summary: Union[SummaryReport, Cell, Block, DailyReport, WeeklyReport, MonthlyReport], 
                 include_raw_events: bool = False, 
                 raw_events: Optional[List[Dict[str, Any]]] = None) -> None:
        """Save summary report to a JSON file."""
        if not self.output_file:
            return
            
        try:
            # Convert to dict for serialization
            data = summary.model_dump()
            
            # Add raw events if requested and not already in summary
            if include_raw_events and raw_events and not data.get("raw_events"):
                data["raw_events"] = raw_events
                
            # Make sure process_events is included
            if not data.get("process_events") and hasattr(summary, "process_events") and summary.process_events:
                data["process_events"] = summary.process_events
                
            with open(self.output_file, "a") as f:
                f.write(json.dumps(data) + "\n")
                
            logger.debug(f"Saved report to {self.output_file}")
        except Exception as e:
            logger.error(f"Failed writing report: {e}")

    def send_llm(self, report: Union[SummaryReport, Cell, Block, DailyReport, WeeklyReport, MonthlyReport]) -> Optional[str]:
        """Send report to LLM for analysis."""
        if not self.client:
            logger.warning("OpenAI client not configured, skipping LLM analysis")
            return None
            
        prompt = report.to_prompt()
        try:
            logger.debug(f"Sending prompt to {self.model}")
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role":"system","content":"You are a security analyst specializing in Linux system activity. Analyze command execution patterns to identify potential security concerns."},
                    {"role":"user","content":prompt}
                ],
                temperature=0.3,
                max_tokens=500,
            )
            analysis = resp.choices[0].message.content
            logger.info("LLM analysis: " + analysis)
            
            # Save the analysis to the report file if available
            if self.output_file:
                try:
                    with open(self.output_file + ".analysis", "a") as f:
                        f.write(f"--- Analysis for report {report.report_id} ---\n")
                        f.write(analysis)
                        f.write("\n\n")
                except Exception as e:
                    logger.error(f"Failed to save analysis: {e}")
            
            return analysis
                    
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return None
    
    def analyze_report(self, report: Union[Block, DailyReport, WeeklyReport, MonthlyReport]) -> None:
        """
        Send a higher-level report to LLM for analysis and update it with the results.
        
        Args:
            report: The higher-level report to analyze
        """
        analysis = self.send_llm(report)
        if analysis:
            # Update the report with the analysis
            report.analysis = analysis
            logger.debug(f"Updated {type(report).__name__} {report.report_id} with analysis") 