#!/usr/bin/env python3

from turtle import title
import mariadb
from datetime import datetime
import os
from dotenv import load_dotenv
from rich import print
from rich.console import Console
from rich.style import Style
from rich.columns import Columns
from rich.table import Table
from rich.padding import Padding
from rich import box
from rich import terminal_theme

#####################################
# mariadb-analyzer
# Version: 0.3.1
# Author: Peter Pakula
# Date: 2026-05-03
#####################################

analyzer_style_white = Style()
analyzer_style_yellow = Style(color="yellow")
analyzer_style_border_style = Style(color="cyan")
analyzer_style_console = Style()

def connect_database(database_host, database_port, database_user, database_pass, database_dbname):
    """Connect to MariaDB Server"""
    try:
        return mariadb.connect(
            host=database_host,
            port=database_port,
            database=database_dbname,
            user=database_user,
            password=database_pass
        )
    except mariadb.Error as e:
        raise RuntimeError(f"MariaDB connection failed: {e}") from e

def get_variables(cursor):
    cursor.execute("SHOW VARIABLES")
    return dict(cursor.fetchall())

def get_status(cursor):
    cursor.execute("SHOW GLOBAL STATUS")
    return dict(cursor.fetchall())

def get_processlist(cursor):
    cursor.execute("SHOW PROCESSLIST")
    return cursor.fetchall()

def get_diff_variables(cursor):
    cursor.execute("""SELECT information_schema.system_variables.variable_name,
        information_schema.system_variables.default_value,
        information_schema.global_variables.variable_value
        FROM information_schema.system_variables
        JOIN information_schema.global_variables
        ON information_schema.system_variables.variable_name = information_schema.global_variables.variable_name
        WHERE information_schema.system_variables.default_value <> information_schema.global_variables.variable_value
        AND information_schema.system_variables.default_value <> 0
        ORDER BY information_schema.system_variables.variable_name ASC""")
    return cursor.fetchall()

def get_index_and_data_length_per_tablename(cursor):
    cursor.execute("""SELECT table_schema, table_name, engine, table_collation, index_length, data_length
        FROM information_schema.tables
        WHERE information_schema.tables.table_type = 'BASE TABLE'
        AND information_schema.tables.table_schema NOT IN ('information_schema', 'sys', 'performance_schema', 'mysql')
        ORDER BY information_schema.tables.table_schema, information_schema.tables.table_name ASC""")
    return cursor.fetchall()

def get_grants(cursor):
    cursor.execute("SHOW GRANTS")
    return cursor.fetchall()

def query_cache_read_hit_rate(status):
    """Qcache_hits / Qcache_inserts"""
    qcache_hits = int(status.get("Qcache_hits", 0))
    qcache_inserts = int(status.get("Qcache_inserts", 0))
    read_hit_rate = 0
    if qcache_inserts > 0:
        read_hit_rate = qcache_hits / qcache_inserts
    return round(read_hit_rate, 2)

def innodb_buffer_pool_hit_ratio(status, variables):
    """The InnoDB Buffer Pool hit ratio is a indicator how often your pages are retrieved from memory instead of disk:"""
    """Innodb_buffer_pool_read_requests / (Innodb_buffer_pool_read_requests + Innodb_buffer_pool_reads) * 100 = InnoDB Buffer Pool hit ratio"""
    key_reads = int(status.get("Innodb_buffer_pool_reads", 0))
    key_read_requests = int(status.get("Innodb_buffer_pool_read_requests", 0))
    hit_ratio = 0
    if key_read_requests > 0:
        hit_ratio = key_read_requests / (key_read_requests + key_reads) * 100
    return round(hit_ratio, 2)

def calculate_per_connection_total(status, variables):
    sort_buffer_size = int(variables.get('sort_buffer_size', 0))
    read_buffer_size = int(variables.get('read_buffer_size', 0))
    read_rnd_buffer_size = int(variables.get('read_rnd_buffer_size', 0))
    join_buffer_size = int(variables.get('join_buffer_size', 0))
    thread_stack = int(variables.get('thread_stack', 0))
    tmp_table_size = int(variables.get('tmp_table_size', 0))
    total = sort_buffer_size + read_buffer_size + read_rnd_buffer_size + join_buffer_size + thread_stack + tmp_table_size
    return round(total, 2)

def format_bytes(size):
    # 2**10 = 1024
    power = 2**10
    n = 0
    power_labels = {0 : 'Bytes', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while size > power and n < len(power_labels) - 1:
        size /= power
        n += 1
    return f"{round(size, 2)} {power_labels[n]}"

def format_uptime(total_seconds):
    years, remainder = divmod(total_seconds, 365 * 24 * 60 * 60)
    days, remainder = divmod(remainder, 24 * 60 * 60)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if years:
        parts.append(f"{years} year{'s' if years != 1 else ''}")
    if days:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds or not parts:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")

    return ", ".join(parts)

def generate_table_general(mariadb_variables, mariadb_status) -> Table:
    """Uptime, Memory"""
    table_general = Table(title="General", box=box.ROUNDED, show_header=False, width=55, border_style=analyzer_style_border_style, title_justify="left")
    table_general.add_column("Variable name", style=analyzer_style_yellow)
    table_general.add_column("Value", style=analyzer_style_white)
    table_general.add_row("hostname", f"{mariadb_variables.get('hostname', 'unknown')}")
    table_general.add_row("version", f"{mariadb_variables.get('version', 'unknown')}")
    table_general.add_row("uptime", f"{ format_uptime(int(mariadb_status.get('Uptime', 0))) }")
    table_general.add_row("Memory_used", f"{ format_bytes(int(mariadb_status.get('Memory_used', 0))) }")
    table_general.add_row("table_definition_cache", f"{ mariadb_variables.get('table_definition_cache') }")
    table_general.add_row("table_open_cache", f"{ mariadb_variables.get('table_open_cache') }")
    return table_general

def generate_table_connections(mariadb_variables, mariadb_status) -> Table:
    """Connections and Buffer per Connection"""
    table_connections = Table(title="Connections", box=box.ROUNDED, show_header=False, width=55, border_style=analyzer_style_border_style, title_justify="left")
    table_connections.add_column("Variable name", style=analyzer_style_yellow)
    table_connections.add_column("Value", style=analyzer_style_white)
    table_connections.add_row("max_connections", f"{ mariadb_variables.get('max_connections') }")
    table_connections.add_row("Max_used_connections", f"{ mariadb_status.get('Max_used_connections', 0) }")
    table_connections.add_row("Max_used_connections_time", f"{ mariadb_status.get('Max_used_connections_time') }", end_section=True)
    table_connections.add_row("sort_buffer_size", f"{ format_bytes(int(mariadb_variables.get('sort_buffer_size', 0))) }")
    table_connections.add_row("read_buffer_size", f"{ format_bytes(int(mariadb_variables.get('read_buffer_size', 0))) }")
    table_connections.add_row("read_rnd_buffer_size", f"{ format_bytes(int(mariadb_variables.get('read_rnd_buffer_size', 0))) }")
    table_connections.add_row("join_buffer_size", f"{ format_bytes(int(mariadb_variables.get('join_buffer_size', 0))) }")
    table_connections.add_row("thread_stack", f"{ format_bytes(int(mariadb_variables.get('thread_stack', 0))) }")
    table_connections.add_row("tmp_table_size", f"{ format_bytes(int(mariadb_variables.get('tmp_table_size', 0))) }", end_section=True)
    table_connections.add_row("Per-Connection Total", f"{ format_bytes(calculate_per_connection_total(status=mariadb_status, variables=mariadb_variables)) }")
    return table_connections

def generate_table_innodb(mariadb_variables, mariadb_status) -> Table:
    """InnoDB Storage Engine"""
    table_innodb = Table(title="InnoDB", box=box.ROUNDED, show_header=False, border_style=analyzer_style_border_style, title_justify="left")
    table_innodb.add_column("Variable name", style=analyzer_style_yellow)
    table_innodb.add_column("Value", style=analyzer_style_white)
    table_innodb.add_row("innodb_buffer_pool_size", f"{ format_bytes(int(mariadb_variables.get('innodb_buffer_pool_size', 0))) }")
    table_innodb.add_row("innodb_flush_method", f"{ mariadb_variables.get('innodb_flush_method') }")
    table_innodb.add_row("innodb_log_file_size", f"{ format_bytes(int(mariadb_variables.get('innodb_log_file_size', 0))) }")
    table_innodb.add_row("innodb_log_buffer_size", f"{ format_bytes(int(mariadb_variables.get('innodb_log_buffer_size', 0))) }")
    table_innodb.add_row("Innodb_buffer_pool_read_requests", f"{ mariadb_status.get('Innodb_buffer_pool_read_requests') }")
    table_innodb.add_row("Innodb_buffer_pool_reads", f"{ mariadb_status.get('Innodb_buffer_pool_reads') }")
    table_innodb.add_row("Innodb_buffer_pool_pages_data", f"{ mariadb_status.get('Innodb_buffer_pool_pages_data') }")
    table_innodb.add_row("Innodb_buffer_pool_pages_misc", f"{ mariadb_status.get('Innodb_buffer_pool_pages_misc') }")
    table_innodb.add_row("Innodb_buffer_pool_pages_free", f"{ mariadb_status.get('Innodb_buffer_pool_pages_free') }")
    table_innodb.add_row("Innodb_buffer_pool_pages_total", f"{ mariadb_status.get('Innodb_buffer_pool_pages_total') }")
    table_innodb.add_row("Innodb_page_size", f"{ format_bytes(int(mariadb_status.get('Innodb_page_size',0 ))) }", end_section=True)
    table_innodb.add_row("pool_hit_ratio", f"{ innodb_buffer_pool_hit_ratio(status=mariadb_status, variables=mariadb_variables) } %")
    return table_innodb

def generate_table_myisam(mariadb_variables, mariadb_status) -> Table:
    """MyISAM Storage Engine"""
    table_myisam = Table(title="MyISAM", box=box.ROUNDED, show_header=False, border_style=analyzer_style_border_style, title_justify="left")
    table_myisam.add_column("Variable name", style=analyzer_style_yellow)
    table_myisam.add_column("Value", style=analyzer_style_white)
    table_myisam.add_row("key_buffer_size", f"{ format_bytes(int(mariadb_variables.get('key_buffer_size', 0))) }")
    table_myisam.add_row("Key_read_requests", f"{ int(mariadb_status.get('Key_read_requests', 0)) }")
    table_myisam.add_row("Key_reads", f"{ int(mariadb_status.get('Key_reads', 0)) }")
    table_myisam.add_row("Key_write_requests", f"{ int(mariadb_status.get('Key_write_requests', 0)) }")
    table_myisam.add_row("Key_writes", f"{ int(mariadb_status.get('Key_writes', 0)) }")
    table_myisam.add_row("Key_blocks_not_flushed", f"{ int(mariadb_status.get('Key_blocks_not_flushed', 0)) }")
    table_myisam.add_row("Key_blocks_used", f"{ int(mariadb_status.get('Key_blocks_used', 0)) }")
    table_myisam.add_row("Key_blocks_unused", f"{ int(mariadb_status.get('Key_blocks_unused', 0)) }")
    table_myisam.add_row("Key_blocks_warm", f"{ int(mariadb_status.get('Key_blocks_warm', 0)) }")
    return table_myisam

def generate_table_aria(mariadb_variables, mariadb_status) -> Table:
    """Aria Storage Engine"""
    table_aria = Table(title="Aria", box=box.ROUNDED, show_header=False, border_style=analyzer_style_border_style, title_justify="left")
    table_aria.add_column("Variable name", style=analyzer_style_yellow)
    table_aria.add_column("Value", style=analyzer_style_white)
    table_aria.add_row("aria_pagecache_buffer_size", f"{ format_bytes(int(mariadb_variables.get('aria_pagecache_buffer_size', 0))) }")
    table_aria.add_row("Aria_pagecache_read_requests", f"{ int(mariadb_status.get('Aria_pagecache_read_requests', 0)) }")
    table_aria.add_row("Aria_pagecache_reads", f"{ int(mariadb_status.get('Aria_pagecache_reads', 0)) }")
    table_aria.add_row("Aria_pagecache_write_requests", f"{ int(mariadb_status.get('Aria_pagecache_write_requests', 0)) }")
    table_aria.add_row("Aria_pagecache_writes", f"{ int(mariadb_status.get('Aria_pagecache_writes', 0)) }")
    table_aria.add_row("Aria_pagecache_blocks_not_flushed", f"{ int(mariadb_status.get('Aria_pagecache_blocks_not_flushed', 0)) }")
    table_aria.add_row("Aria_pagecache_blocks_used", f"{ int(mariadb_status.get('Aria_pagecache_blocks_used', 0)) }")
    table_aria.add_row("Aria_pagecache_blocks_unused", f"{ int(mariadb_status.get('Aria_pagecache_blocks_unused', 0)) }")
    table_aria.add_row("Aria_transaction_log_syncs", f"{ int(mariadb_status.get('Aria_transaction_log_syncs', 0)) }")
    return table_aria

def generate_table_query_cache(mariadb_variables, mariadb_status) -> Table:
    """Query Cache"""
    table_query_cache = Table(title="Query Cache", box=box.ROUNDED, show_header=False, border_style=analyzer_style_border_style, title_justify="left")
    table_query_cache.add_column("Variable name", style=analyzer_style_yellow)
    table_query_cache.add_column("Value", style=analyzer_style_white)
    table_query_cache.add_row("query_cache_size", f"{ format_bytes(int(mariadb_variables.get('query_cache_size', 0))) }")
    table_query_cache.add_row("query_cache_type", f"{ mariadb_variables.get('query_cache_type') }")
    table_query_cache.add_row("Qcache_free_blocks", f"{ int(mariadb_status.get('Qcache_free_blocks', 0)) }")
    table_query_cache.add_row("Qcache_free_memory", f"{ format_bytes(int(mariadb_status.get('Qcache_free_memory', 0))) }")
    table_query_cache.add_row("Qcache_hits", f"{ int(mariadb_status.get('Qcache_hits', 0)) }")
    table_query_cache.add_row("Qcache_inserts", f"{ int(mariadb_status.get('Qcache_inserts', 0)) }")
    table_query_cache.add_row("Qcache_lowmem_prunes", f"{ int(mariadb_status.get('Qcache_lowmem_prunes', 0)) }")
    table_query_cache.add_row("Qcache_not_cached", f"{ int(mariadb_status.get('Qcache_not_cached', 0)) }")
    table_query_cache.add_row("Qcache_queries_in_cache", f"{ int(mariadb_status.get('Qcache_queries_in_cache', 0)) }")
    table_query_cache.add_row("Qcache_total_blocks", f"{ int(mariadb_status.get('Qcache_total_blocks', 0)) }", end_section=True)
    table_query_cache.add_row("read_hit_rate", f"{ query_cache_read_hit_rate(mariadb_status) }")
    return table_query_cache

def generate_table_processlist(mariadb_processlist) -> Table:
    """Processlist"""
    table_processlist = Table(title="Processlist", box=box.ROUNDED, show_header=False, border_style=analyzer_style_border_style, title_justify="left")
    table_processlist.add_column("Id", style=analyzer_style_yellow)
    table_processlist.add_column("User", style=analyzer_style_white)
    table_processlist.add_column("Host", style=analyzer_style_white)
    table_processlist.add_column("db", style=analyzer_style_white)
    table_processlist.add_column("Command", style=analyzer_style_white)
    table_processlist.add_column("Time", style=analyzer_style_white)
    table_processlist.add_column("State", style=analyzer_style_white)
    table_processlist.add_column("Info", style=analyzer_style_white)
    table_processlist.add_column("Progress", style=analyzer_style_white)

    for plist_row in mariadb_processlist:
        table_processlist.add_row(
            str(plist_row[0]),
            str(plist_row[1]),
            str(plist_row[2]),
            str(plist_row[3]),
            str(plist_row[4]),
            str(plist_row[5]),
            str(plist_row[6]),
            str(plist_row[7]),
            str(plist_row[8]),
        )

    return table_processlist

def generate_table_index_and_data_length(mariadb_index_and_data_length) -> Table:
    """Index and Data length per Tablename and Schema"""
    table_index_and_data_length = Table(title="Index and Data length", box=box.ROUNDED, border_style=analyzer_style_border_style, title_justify="left")
    table_index_and_data_length.add_column("Schema", style=analyzer_style_yellow)
    table_index_and_data_length.add_column("Table name", style=analyzer_style_yellow)
    table_index_and_data_length.add_column("Engine", style=analyzer_style_yellow)
    table_index_and_data_length.add_column("Table collation", style=analyzer_style_yellow)
    table_index_and_data_length.add_column("Index size", style=analyzer_style_white)
    table_index_and_data_length.add_column("Data size", style=analyzer_style_white)

    for index_and_data_length in mariadb_index_and_data_length:
        table_index_and_data_length.add_row(
            str(index_and_data_length[0]),
            str(index_and_data_length[1]),
            str(index_and_data_length[2]),
            str(index_and_data_length[3]),
            format_bytes(int(index_and_data_length[4])),
            format_bytes(int(index_and_data_length[5]))
        )

    return table_index_and_data_length

def generate_table_diff_variables(mariadb_diff_variables) -> Table:
    """Diff default vs custom variables"""
    table_diff_variables = Table(title="Diff Variables", box=box.ROUNDED, border_style=analyzer_style_border_style, title_justify="left")
    table_diff_variables.add_column("Variable name", style=analyzer_style_yellow)
    table_diff_variables.add_column("Default", style=analyzer_style_white)
    table_diff_variables.add_column("Value", style=analyzer_style_white)

    for diff_variable in mariadb_diff_variables:
        table_diff_variables.add_row(str(diff_variable[0]), str(diff_variable[1]), str(diff_variable[2]))

    return table_diff_variables

def generate_table_grants(mariadb_grants) -> Table:
    """Grants"""
    table_grants = Table(title="Grants", box=box.ROUNDED, show_header=False, border_style=analyzer_style_border_style, title_justify="left")
    table_grants.add_column("Grants for user", style=analyzer_style_white)

    for mariadb_grant in mariadb_grants:
        table_grants.add_row(str(mariadb_grant[0]))

    return table_grants

def generate_report():
    load_dotenv()

    report_datetime = datetime.now()

    database_user = os.getenv("MARIADB_ANALYZER_USERNAME", "root")
    database_pass = os.getenv("MARIADB_ANALYZER_PASSWORD")
    database_host = os.getenv("MARIADB_ANALYZER_HOST", "localhost")
    database_port = int(os.getenv("MARIADB_ANALYZER_PORT", 3306))
    database_dbname = os.getenv("MARIADB_ANALYZER_DATABASE_NAME", "information_schema")
    create_html_report = int(os.getenv("MARIADB_ANALYZER_CREATE_HTML_REPORT", 1))
    view_processlist = int(os.getenv("MARIADB_ANALYZER_VIEW_PROCESSLIST", 1))
    view_diff_variables = int(os.getenv("MARIADB_ANALYZER_VIEW_DIFF_VARIABLES", 1))
    view_index_and_data_length = int(os.getenv("MARIADB_ANALYZER_VIEW_INDEX_DATA_LENGTH", 1))
    view_grants = int(os.getenv("MARIADB_ANALYZER_VIEW_GRANTS", 1))

    with connect_database(database_host, database_port, database_user, database_pass, database_dbname) as conn:
        with conn.cursor() as cursor:
            mariadb_variables = get_variables(cursor)
            mariadb_status = get_status(cursor)
            mariadb_processlist = get_processlist(cursor)
            mariadb_diff_variables = get_diff_variables(cursor)
            mariadb_index_and_data_length = get_index_and_data_length_per_tablename(cursor)
            mariadb_grants = get_grants(cursor)

    console = Console(record=True, style=analyzer_style_console)

    analyzer_columns = Columns(
        [
            generate_table_general(mariadb_status=mariadb_status, mariadb_variables=mariadb_variables),
            generate_table_connections(mariadb_status=mariadb_status, mariadb_variables=mariadb_variables),
            generate_table_query_cache(mariadb_status=mariadb_status, mariadb_variables=mariadb_variables),
            generate_table_innodb(mariadb_status=mariadb_status, mariadb_variables=mariadb_variables),
            generate_table_myisam(mariadb_status=mariadb_status, mariadb_variables=mariadb_variables),
            generate_table_aria(mariadb_status=mariadb_status, mariadb_variables=mariadb_variables),
        ]
    )

    console.print("[bold cyan]MariaDB Analyzer Report[/bold cyan]", justify="center")
    console.print(f"Generated: {report_datetime.strftime('%Y-%m-%d %H:%M:%S')}", justify="center")
    console.print(f"Host: {mariadb_variables.get('hostname', 'unknown')}", justify="center")
    console.print()

    console.print(Padding(analyzer_columns, 1))
    if view_processlist:
        console.print(Padding(generate_table_processlist(mariadb_processlist=mariadb_processlist),1))
    if view_diff_variables:
        console.print(Padding(generate_table_diff_variables(mariadb_diff_variables),1))
    if view_index_and_data_length:
        console.print(Padding(generate_table_index_and_data_length(mariadb_index_and_data_length),1))
    if view_grants:
        console.print(Padding(generate_table_grants(mariadb_grants),1))
    if create_html_report:
        report_filename = f"{report_datetime.strftime('%Y%m%d%H%M%S')}_report.html"
        console.save_html(report_filename, theme=terminal_theme.SVG_EXPORT_THEME)

if __name__ == "__main__":
    generate_report()
