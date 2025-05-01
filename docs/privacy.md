# Privacy Policy

This document outlines the privacy considerations for the Linux EDR system.

## Data Collection

Linux EDR collects process execution events from the Linux kernel through the `ftrace` subsystem. This includes:

- Process IDs (PIDs)
- Command names and arguments
- Execution timestamps
- Parent-child process relationships

## Data Storage

All data collected by Linux EDR is stored locally on the system where it is installed. By default, no data is transmitted to external servers.

## AI Analysis

When the AI analysis feature is enabled:

1. Report summaries (not raw event data) may be sent to OpenAI's API for analysis
2. The data sent is limited to aggregated statistics and patterns, not detailed command arguments
3. You can disable this feature in the configuration file

## Data Retention

- Cell reports (5-minute intervals): Retained for 24 hours
- Block reports (hourly): Retained for 7 days  
- Daily reports: Retained for 30 days
- Weekly reports: Retained for 90 days
- Monthly reports: Retained for 365 days

You can modify these retention periods in the configuration file.

## Security Considerations

- All data is stored in the local filesystem
- Access to the reports requires filesystem permissions
- No authentication is built into the tool itself - rely on system-level access controls

## Third-Party Services

The only external service optionally used is the OpenAI API for report analysis. This can be disabled in the configuration.

## Changes to This Policy

This privacy policy may be updated as the tool evolves. Check the repository for the latest version. 