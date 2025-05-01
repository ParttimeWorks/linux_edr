# Privacy Policy for Linux EDR

## Our Privacy Commitment

Linux EDR is committed to respecting user privacy and system integrity. Our tool is designed to monitor system activity via the kernel's trace_pipe without modifying system behavior or exfiltrating data without explicit permission.

## Data Collection

### What We Collect

Linux EDR collects:
- Command execution events from the kernel trace subsystem
- Process names and command line arguments
- Process IDs and timestamps

### What We DO NOT Collect

Linux EDR does **not**:
- Access file contents
- Monitor network traffic content
- Capture user keystrokes
- Access sensitive system files
- Store persistent user identifiers
- Modify system behavior or files

## Data Storage

All data collected by Linux EDR is:
- Stored locally on your system only
- Never transmitted externally without explicit configuration
- Automatically rotated to prevent excessive disk usage
- Retained only as long as configured in your settings

## OpenAI Integration (Optional)

If you enable and configure the OpenAI integration:
- Command execution data is sent to OpenAI for security analysis
- Only command names, arguments, and timestamps are transmitted
- No personal user data or system identifiers are included
- Data transmission only occurs with your explicit API key configuration

## Minimizing System Impact

Linux EDR is designed to:
- Use minimal system resources
- Run with the lowest necessary privileges
- Not interfere with normal system operation
- Support graceful degradation if resource constraints are encountered

## Configuration Control

You maintain complete control through:
- Explicit configuration options for all functionality
- The ability to specify what data is collected and processed
- Options to limit the size and scope of data retention
- Full control over external API integrations

## Transparency

Linux EDR is fully open source, allowing you to:
- Inspect all code to verify privacy claims
- Modify the tool to meet your specific requirements
- Verify that data handling matches documented behavior

## Changes to This Policy

Any changes to this privacy policy will be documented in release notes and this document will be updated accordingly.

## Contact

If you have any questions about this privacy policy or Linux EDR's handling of data, please raise an issue on our GitHub repository. 