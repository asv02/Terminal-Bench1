#!/usr/bin/env python3
"""
Data Processing CLI for Clickstream Logs
Processes gzipped JSONL clickstream logs, filters bots, aggregates data, and generates reports.
"""

import argparse
import gzip
import json
import pandas as pd
import re
import sys
from pathlib import Path


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Process clickstream logs and generate analytics')
    parser.add_argument('--input-dir', required=True, help='Directory containing gzipped JSONL files')
    parser.add_argument('--output-json', required=True, help='Output JSON file path')
    parser.add_argument('--output-md', required=True, help='Output Markdown file path')
    return parser.parse_args()


def is_bot_user_agent(user_agent):
    """
    Check if a user agent is from a bot/crawler.
    
    Args:
        user_agent (str): User agent string
        
    Returns:
        bool: True if user agent is a bot, False otherwise
    """
    bot_patterns = [
        r'bot',
        r'crawler',
        r'spider',
        r'slurp',
        r'facebookexternalhit',
        r'twitterbot',
        r'linkedinbot',
        r'slackbot',
        r'discordbot',
        r'whatsapp'
    ]
    
    user_agent_lower = user_agent.lower()
    return any(re.search(pattern, user_agent_lower) for pattern in bot_patterns)


def read_gzipped_jsonl(filepath):
    """
    Read gzipped JSONL file and return list of records.
    
    Args:
        filepath (str): Path to gzipped JSONL file
        
    Returns:
        list: List of dictionaries representing records
    """
    records = []
    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records


def process_logs(input_dir):
    """
    Process all log files in the input directory.
    
    Args:
        input_dir (str): Directory containing log files
        
    Returns:
        pd.DataFrame: Processed data
    """
    # Find the gzipped JSONL file in the input directory
    input_path = Path(input_dir)
    if not input_path.exists():
        print(f"Error: Input directory {input_dir} does not exist", file=sys.stderr)
        sys.exit(1)
    
    # Look for .jsonl.gz files
    gz_files = list(input_path.glob("*.jsonl.gz"))
    if not gz_files:
        print(f"Error: No .jsonl.gz files found in {input_dir}", file=sys.stderr)
        sys.exit(1)
    
    # Process all files found
    all_records = []
    for filepath in gz_files:
        records = read_gzipped_jsonl(filepath)
        all_records.extend(records)
    
    # Convert to DataFrame
    df = pd.DataFrame(all_records)
    
    # Check if required columns exist
    required_columns = ['timestamp', 'user_id', 'event_type', 'user_agent']
    for col in required_columns:
        if col not in df.columns:
            print(f"Error: Missing required column '{col}' in input data", file=sys.stderr)
            sys.exit(1)
    
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Filter out bot traffic
    df['is_bot'] = df['user_agent'].apply(is_bot_user_agent)
    df_filtered = df[~df['is_bot']].copy()
    
    # Extract hour from timestamp
    df_filtered['hour_bucket'] = df_filtered['timestamp'].dt.floor('h')
    
    return df_filtered


def aggregate_data(df):
    """
    Aggregate data by event_type and hour.
    
    Args:
        df (pd.DataFrame): Filtered DataFrame
        
    Returns:
        dict: Aggregated data
    """
    # Group by event_type and hour_bucket
    grouped = df.groupby(['event_type', 'hour_bucket'])
    
    # Calculate hourly counts and unique users
    hourly_stats = grouped.agg({
        'user_id': ['count', 'nunique']
    }).reset_index()
    
    # Flatten column names
    hourly_stats.columns = ['event_type', 'hour_bucket', 'event_count', 'unique_users']
    
    # Sort by event_type and hour_bucket
    hourly_stats = hourly_stats.sort_values(['event_type', 'hour_bucket'])
    
    # Calculate 7-day rolling averages
    result = []
    for event_type in hourly_stats['event_type'].unique():
        event_data = hourly_stats[hourly_stats['event_type'] == event_type].copy()
        
        # Set hour_bucket as index for rolling window calculation
        event_data.set_index('hour_bucket', inplace=True)
        
        # Calculate 7-day rolling averages (168 hours)
        event_data['event_count_7d_avg'] = event_data['event_count'].rolling('7D').mean()
        event_data['unique_users_7d_avg'] = event_data['unique_users'].rolling('7D').mean()
        
        # Reset index
        event_data.reset_index(inplace=True)
        
        result.append(event_data)
    
    # Combine all event types
    final_df = pd.concat(result, ignore_index=True)
    
    # Convert to dictionary for JSON serialization
    return final_df.to_dict('records')


def generate_sparkline(values):
    """
    Generate a simple ASCII sparkline from a list of values.
    
    Args:
        values (list): List of numerical values
        
    Returns:
        str: ASCII sparkline representation
    """
    if not values:
        return ""
    
    # Normalize values to 0-7 for sparkline characters
    min_val = min(values)
    max_val = max(values)
    
    if max_val == min_val:
        # All values are the same
        return "█" * len(values)
    
    # Map values to sparkline characters
    spark_chars = "▁▂▃▄▅▆▇█"
    normalized = [(v - min_val) / (max_val - min_val) * 7 for v in values]
    indices = [int(round(n)) for n in normalized]
    
    return "".join(spark_chars[i] for i in indices)


def generate_json_output(aggregated_data, output_path):
    """
    Generate JSON output file.
    
    Args:
        aggregated_data (list): Aggregated data
        output_path (str): Output file path
    """
    with open(output_path, 'w') as f:
        json.dump(aggregated_data, f, indent=2, default=str)


def generate_markdown_report(aggregated_data, output_path):
    """
    Generate Markdown report with sparklines.
    
    Args:
        aggregated_data (list): Aggregated data
        output_path (str): Output file path
    """
    # Convert to DataFrame for easier manipulation
    df = pd.DataFrame(aggregated_data)
    
    # Group by event_type
    report_lines = [
        "# Clickstream Analytics Report",
        "",
        "## Summary",
        "",
        "This report analyzes clickstream data and provides metrics grouped by event type.",
        f"Data processed: {len(df)} hourly aggregations",
        "",
        "## Metrics by Event Type",
        ""
    ]
    
    for event_type in df['event_type'].unique():
        event_data = df[df['event_type'] == event_type].sort_values('hour_bucket')
        
        # Extract values for sparklines
        event_counts = event_data['event_count'].tolist()
        unique_users = event_data['unique_users'].tolist()
        event_count_7d_avg = event_data['event_count_7d_avg'].tolist()
        unique_users_7d_avg = event_data['unique_users_7d_avg'].tolist()
        
        # Remove NaN values for sparklines
        event_count_7d_avg_clean = [x for x in event_count_7d_avg if not pd.isna(x)]
        unique_users_7d_avg_clean = [x for x in unique_users_7d_avg if not pd.isna(x)]
        
        report_lines.extend([
            f"### {event_type}",
            "",
            f"- Total Events: {event_data['event_count'].sum()}",
            f"- Unique Users: {event_data['unique_users'].sum()}",
            f"- Hourly Event Count: {generate_sparkline(event_counts)}",
            f"- Hourly Unique Users: {generate_sparkline(unique_users)}",
            f"- 7-Day Rolling Avg (Events): {generate_sparkline(event_count_7d_avg_clean)}",
            f"- 7-Day Rolling Avg (Users): {generate_sparkline(unique_users_7d_avg_clean)}",
            ""
        ])
    
    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))


def main():
    """Main function."""
    try:
        args = parse_args()
        
        # Process logs
        print("Processing logs...")
        df_filtered = process_logs(args.input_dir)
        print(f"Processed {len(df_filtered)} human-generated events")
        
        # Aggregate data
        print("Aggregating data...")
        aggregated_data = aggregate_data(df_filtered)
        print(f"Aggregated into {len(aggregated_data)} hourly records")
        
        # Create output directories if they don't exist
        json_output_path = Path(args.output_json)
        md_output_path = Path(args.output_md)
        json_output_path.parent.mkdir(parents=True, exist_ok=True)
        md_output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate outputs
        print("Generating JSON output...")
        generate_json_output(aggregated_data, args.output_json)
        
        print("Generating Markdown report...")
        generate_markdown_report(aggregated_data, args.output_md)
        
        print("Processing complete!")
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()