import json
import logging
import re
from typing import List, Dict, Any, Optional, Union, Tuple
from openai import OpenAI
from .models import SummaryReport, Cell, Block, DailyReport, WeeklyReport, MonthlyReport

logger = logging.getLogger(__name__)


class Reporter:
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key) if api_key else None
        self.model = model

        # Batch processing attributes
        # Queue to accumulate batch-able requests (currently weekly & monthly reports)
        self._batch_queue: List[Dict[str, Any]] = []  # each item is the preformatted jsonl dict
        # Default flush size – can be tuned; kept small to avoid large files during dev/testing
        self._batch_flush_size: int = 10

        # Track submitted batches awaiting completion. Maps batch_id -> metadata dict
        self._pending_batches: Dict[str, Dict[str, Any]] = {}

    # ------------------------- Batch Helpers -------------------------

    def _enqueue_for_batch(self, report: Union[WeeklyReport, MonthlyReport]) -> None:
        """Add a report prompt to the internal batch queue and submit if threshold reached."""
        if not self.client:
            logger.warning("OpenAI client not configured, skipping batch enqueue")
            return

        prompt: str = report.to_prompt()

        request_line: Dict[str, Any] = {
            "custom_id": report.report_id,
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a security analyst specializing in Linux system activity. Analyze command execution patterns to identify potential security concerns. Format your response with a summary, severity score (1-5), and key findings.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 1024,
            },
        }

        self._batch_queue.append(request_line)

        logger.debug(
            f"Queued {type(report).__name__} {report.report_id} for batch processing (queue size={len(self._batch_queue)})"
        )

        self._flush_batch_queue()

    def _flush_batch_queue(self) -> None:
        """Submit the accumulated batch queue to OpenAI Batch API and clear the queue."""
        if not self._batch_queue:
            return

        if not self.client:
            logger.warning("OpenAI client not configured, skipping batch flush")
            return

        import tempfile, os, json

        try:
            # Write queue to temporary jsonl file
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".jsonl") as tmp_file:
                for line in self._batch_queue:
                    tmp_file.write(json.dumps(line) + "\n")
                tmp_file_path = tmp_file.name

            # Upload file for batch purpose
            file_resp = self.client.files.create(file=open(tmp_file_path, "rb"), purpose="batch")
            logger.debug(f"Uploaded batch input file {file_resp.id} with {len(self._batch_queue)} requests")

            # Create the batch job
            batch_resp = self.client.batches.create(
                input_file_id=file_resp.id,
                endpoint="/v1/chat/completions",
                completion_window="24h",
                metadata={"source": "linux-edr-weekly-monthly"},
            )

            logger.info(
                f"Created batch {batch_resp.id} with {len(self._batch_queue)} requests (status={batch_resp.status})"
            )

            # Record batch for later retrieval
            self._pending_batches[batch_resp.id] = {
                "created_at": batch_resp.created_at,
                "request_count": len(self._batch_queue),
                "output_file_id": None,
            }

        except Exception as e:
            logger.error(f"Failed to submit batch: {e}")
        finally:
            # Clean up local temp file
            try:
                os.remove(tmp_file_path)  # type: ignore[UnboundLocalVariable]
            except Exception:
                pass

            # Clear queue regardless of success; unsent items can accumulate in future enqueue operations if desired
            self._batch_queue.clear()

    def send_llm(
        self, report: Union[SummaryReport, Cell, Block, DailyReport, WeeklyReport, MonthlyReport]
    ) -> Tuple[Optional[str], Optional[int]]:
        """
        Send report to LLM for analysis.

        Args:
            report: Report to analyze

        Returns:
            Tuple of (analysis text, severity score) or (None, None) if error
        """
        if not self.client:
            logger.warning("OpenAI client not configured, skipping LLM analysis")
            return None, None

        prompt = report.to_prompt()
        try:
            logger.debug(f"Sending prompt to {self.model}")
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a security analyst specializing in Linux system activity. Analyze command execution patterns to identify potential security concerns. Format your response with a summary, severity score (1-5), and key findings.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1024,
            )
            analysis = resp.choices[0].message.content
            severity = self.extract_severity(analysis)

            logger.info(f"LLM analysis complete (severity: {severity if severity else 'unknown'})")

            return analysis, severity

        except Exception as e:
            logger.error(f"LLM error: {e}")
            return None, None

    def extract_severity(self, analysis: str) -> Optional[int]:
        """
        Extract severity score from analysis text.

        Args:
            analysis: The analysis text from LLM

        Returns:
            Severity score (1-5) or None if not found
        """
        # Look for patterns like "Security Score: 3" or "Severity: 4/5" or "severity level: 2"
        patterns = [
            r"Security Score:\s*(\d+)",
            r"Severity:?\s*(\d+)(?:/5)?",
            r"severity level:?\s*(\d+)",
            r"severity rating(?:\s+is)?:?\s*(\d+)",  # Modified to better match "severity rating is X"
            r"severity score:?\s*(\d+)",
            r"security score is\s*(\d+)",
            r"rate the severity as\s*(\d+)",
        ]

        for pattern in patterns:
            if match := re.search(pattern, analysis, re.IGNORECASE):
                try:
                    score = int(match.group(1))
                    if 1 <= score <= 5:
                        return score
                except ValueError:
                    continue

        return None

    def analyze_report(
        self, report: Union[SummaryReport, Cell, Block, DailyReport, WeeklyReport, MonthlyReport]
    ) -> None:
        """
        Send a report to LLM for analysis and update it with the results.

        Args:
            report: The report to analyze
        """
        # WeeklyReport & MonthlyReport use Batch API (async) for cost-efficient processing.
        if isinstance(report, (WeeklyReport, MonthlyReport)):
            self._enqueue_for_batch(report)
            # Analysis will be populated later when batch results are retrieved.
            return

        # All other report types are processed synchronously.
        analysis, severity = self.send_llm(report)
        if analysis:
            # Update the report with the analysis and severity
            report.analysis = analysis
            if severity:
                report.severity = severity
            logger.debug(
                f"Updated {type(report).__name__} {report.report_id} with analysis (severity: {severity if severity else 'unknown'})"
            )

    # ------------------------- Batch Result Processing -------------------------

    def process_completed_batches(
        self,
        weekly_repo: "ReportRepository[WeeklyReport]",  # type: ignore
        monthly_repo: "ReportRepository[MonthlyReport]",  # type: ignore
    ) -> None:
        """Check the status of any pending batches, download results for completed ones, and
        update the corresponding Weekly/Monthly reports via the provided repositories.

        Args:
            weekly_repo: Repository instance capable of load/save operations for WeeklyReport.
            monthly_repo: Repository instance capable of load/save operations for MonthlyReport.
        """

        if not self.client or not self._pending_batches:
            return

        completed_batches: List[str] = []

        for batch_id, meta in list(self._pending_batches.items()):
            try:
                batch_obj = self.client.batches.retrieve(batch_id)
            except Exception as e:
                logger.error(f"Failed to retrieve batch {batch_id}: {e}")
                continue

            status: str = getattr(batch_obj, "status", "unknown")

            if status == "completed":
                output_file_id = getattr(batch_obj, "output_file_id", None)
                if not output_file_id:
                    logger.warning(f"Batch {batch_id} completed but no output_file_id found")
                    completed_batches.append(batch_id)
                    continue

                logger.info(f"Batch {batch_id} completed. Downloading results...")

                try:
                    file_resp = self.client.files.content(output_file_id)
                    file_text = file_resp.text  # type: ignore[attr-defined]
                except Exception as e:
                    logger.error(f"Failed to download batch results for {batch_id}: {e}")
                    continue

                processed = 0
                for line in file_text.splitlines():
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        logger.warning(f"Skipping malformed JSONL line in batch {batch_id}")
                        continue

                    if record.get("error") is not None:
                        logger.warning(f"Request {record.get('custom_id')} in batch {batch_id} errored: {record['error']}")
                        continue

                    custom_id = record.get("custom_id")
                    resp_body = record.get("response", {}).get("body", {})
                    analysis = None
                    severity = None
                    try:
                        analysis = resp_body["choices"][0]["message"]["content"]
                        severity = self.extract_severity(analysis)
                    except Exception:
                        logger.warning(f"Unable to extract analysis for {custom_id} from batch {batch_id}")

                    if analysis:
                        # Determine report type by prefix
                        if custom_id.startswith("weekly_"):
                            data = weekly_repo.load(custom_id)
                            if data:
                                report_obj = WeeklyReport(**data)
                                report_obj.analysis = analysis
                                if severity:
                                    report_obj.severity = severity
                                weekly_repo.save(report_obj)
                                processed += 1
                        elif custom_id.startswith("monthly_"):
                            data = monthly_repo.load(custom_id)
                            if data:
                                report_obj = MonthlyReport(**data)
                                report_obj.analysis = analysis
                                if severity:
                                    report_obj.severity = severity
                                monthly_repo.save(report_obj)
                                processed += 1

                logger.info(f"Processed {processed} reports from batch {batch_id}")
                completed_batches.append(batch_id)

            elif status in {"expired", "cancelled", "failed"}:
                logger.warning(f"Batch {batch_id} ended with status '{status}'. Removing from tracking.")
                completed_batches.append(batch_id)

            else:
                # still in progress or validating
                logger.debug(f"Batch {batch_id} status={status}. Not ready yet.")

        # Remove fully handled batches from tracking
        for bid in completed_batches:
            self._pending_batches.pop(bid, None)
