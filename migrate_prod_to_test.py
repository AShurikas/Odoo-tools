#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import subprocess
import sys
import logging
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_command(command):
    """Execute shell command and return output"""
    logger.info(f"Executing: {command}")
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        logger.error(f"Command failed with code {process.returncode}")
        logger.error(f"Error: {stderr.decode('utf-8')}")
        sys.exit(1)
    return stdout.decode('utf-8')


def restore_database(db_name, backup_path):
    """Restore database from backup"""
    logger.info(f"Restoring database {db_name} from {backup_path}")
    cmd = f"odood db restore --recreate --stun {db_name} {backup_path}"
    return run_command(cmd)


def get_websites(db_name):
    """Get all websites from database with their id, name and domain"""
    logger.info(f"Getting websites from {db_name}")
    cmd = f"odoo-helper psql -d {db_name} -c \"SELECT id, name, domain FROM website;\""
    result = run_command(cmd)
    
    # Parse the output to extract website information
    websites = []
    for line in result.strip().split('\n')[2:-1]:  # Skip header and footer lines
        if '|' in line:
            parts = line.split('|')
            if len(parts) >= 3:
                website_id = parts[0].strip()
                website_name = parts[1].strip()
                domain = parts[2].strip()
                if domain == 'NULL' or not domain:
                    domain = None
                websites.append((website_id, website_name, domain))
    
    return websites


def get_domain_from_url(url):
    """Extract domain from URL"""
    match = re.search(r'https?://([^/]+)', url)
    if match:
        return match.group(1)
    return None


def update_database_settings(db_name, base_url, disable_website_domains=False, website_domain=None):
    """Update database settings using odoo-helper psql"""
    logger.info(f"Updating database settings for {db_name}")
    
    # Prepare the SQL script with base settings
    sql_script = f"""
    -- Update base URL
    UPDATE ir_config_parameter SET value = '{base_url}' WHERE key = 'web.base.url';
    
    -- Update base URL freeze if exists
    UPDATE ir_config_parameter SET value = '{base_url}' WHERE key = 'web.base.url.freeze';
    
    -- Set autoredirect to false in auth_saml_provider table
    UPDATE auth_saml_provider SET autoredirect = false;
    """
    
    # Get websites
    websites = get_websites(db_name)
    
    # Handle website domains
    if websites:
        logger.info(f"Found {len(websites)} websites:")
        for site_id, site_name, site_domain in websites:
            domain_info = site_domain if site_domain else "(not set)"
            logger.info(f"  ID: {site_id}, Name: {site_name}, Domain: {domain_info}")
        
        if disable_website_domains:
            # If --disable-website-domains is specified, set all domains to NULL
            logger.info(f"Will disable domains for all {len(websites)} websites")
            sql_script += f"""
    -- Disable all website domains
    UPDATE website SET domain = NULL WHERE id IS NOT NULL;
    """
        elif len(websites) == 1 and (website_domain is not None or base_url):
            # If there's only one website and --website-domain is provided or we can use base_url
            site_id, site_name, _ = websites[0]
            
            # Determine what domain to use
            domain_to_set = website_domain if website_domain else get_domain_from_url(base_url)
            
            if domain_to_set:
                logger.info(f"Will set domain '{domain_to_set}' for website ID {site_id} ({site_name})")
                sql_script += f"""
    -- Set domain for the only website
    UPDATE website SET domain = '{domain_to_set}' WHERE id = {site_id};
    """
            else:
                logger.warning("Could not determine domain from base_url and no website_domain provided")
    else:
        logger.info("No websites found in the database.")
    
    # Create a temporary SQL file
    temp_sql_file = '/tmp/update_settings.sql'
    with open(temp_sql_file, 'w') as f:
        f.write(sql_script)
    
    try:
        # Execute SQL script using odoo-helper psql
        logger.info("Executing SQL script to update database settings")
        cmd = f"odoo-helper psql -d {db_name} -f {temp_sql_file}"
        run_command(cmd)
        logger.info("Database settings updated successfully")
    except Exception as e:
        logger.error(f"Error updating database settings: {e}")
        sys.exit(1)
    finally:
        # Clean up temporary file
        if os.path.exists(temp_sql_file):
            os.remove(temp_sql_file)


def print_migration_summary(db_name, base_url, disable_website_domains, website_domain=None):
    """Print summary of migration results"""
    logger.info("\n====================== MIGRATION SUMMARY ======================")
    logger.info(f"Database name: {db_name}")
    logger.info(f"Base URL: {base_url}")
    
    # Check base URL
    cmd = f"odoo-helper psql -d {db_name} -c \"SELECT value FROM ir_config_parameter WHERE key = 'web.base.url'\""
    result = run_command(cmd).strip().split('\n')[2:-1]
    if result and base_url in result[0]:
        logger.info("✅ Base URL successfully updated")
    else:
        logger.info("❌ Base URL update failed")
    
    # Check SAML providers
    cmd = f"odoo-helper psql -d {db_name} -c \"SELECT COUNT(*) FROM auth_saml_provider WHERE autoredirect = true\""
    result = run_command(cmd).strip().split('\n')[2:-1]
    if result and result[0].strip() == '0':
        logger.info("✅ SAML autoredirect successfully disabled for all providers")
    else:
        logger.info(f"❌ SAML autoredirect not disabled for all providers ({result[0].strip()} providers still have autoredirect enabled)")
    
    # Check mail servers
    cmd = f"odoo-helper psql -d {db_name} -c \"SELECT COUNT(*) FROM ir_mail_server WHERE active = true\""
    result = run_command(cmd).strip().split('\n')[2:-1]
    if result and result[0].strip() == '0':
        logger.info("✅ All outgoing mail servers successfully disabled")
    else:
        logger.info(f"❌ Not all outgoing mail servers disabled ({result[0].strip()} servers still active)")
    
    # Check fetchmail servers
    cmd = f"odoo-helper psql -d {db_name} -c \"SELECT COUNT(*) FROM fetchmail_server WHERE active = true\""
    result = run_command(cmd).strip().split('\n')[2:-1]
    if result and result[0].strip() == '0':
        logger.info("✅ All incoming mail servers successfully disabled")
    else:
        logger.info(f"❌ Not all incoming mail servers disabled ({result[0].strip()} servers still active)")
    
    # Check cron jobs (scheduled tasks)
    cmd = f"odoo-helper psql -d {db_name} -c \"SELECT COUNT(*) FROM ir_cron WHERE active = true\""
    result = run_command(cmd).strip().split('\n')[2:-1]
    if result and result[0].strip() == '0':
        logger.info("✅ All cron jobs successfully disabled")
    else:
        logger.info(f"❌ Not all cron jobs disabled ({result[0].strip()} cron jobs still active)")
    
    # Check website domains based on parameters
    if disable_website_domains:
        # If --disable-website-domains was specified, all domains should be NULL
        cmd = f"odoo-helper psql -d {db_name} -c \"SELECT COUNT(*) FROM website WHERE domain IS NOT NULL\""
        result = run_command(cmd).strip().split('\n')[2:-1]
        if result and result[0].strip() == '0':
            logger.info("✅ All website domains successfully disabled")
        else:
            logger.info(f"❌ Not all website domains disabled ({result[0].strip()} websites still have domains)")
    else:
        # Check if domains were set correctly when there's only one website
        cmd = f"odoo-helper psql -d {db_name} -c \"SELECT COUNT(*) FROM website\""
        result = run_command(cmd).strip().split('\n')[2:-1]
        
        if result and result[0].strip() == '1':
            expected_domain = website_domain if website_domain else get_domain_from_url(base_url)
            if expected_domain:
                cmd = f"odoo-helper psql -d {db_name} -c \"SELECT domain FROM website LIMIT 1\""
                domain_result = run_command(cmd).strip().split('\n')[2:-1]
                
                if domain_result and expected_domain in domain_result[0]:
                    logger.info(f"✅ Website domain successfully set to '{expected_domain}'")
                else:
                    logger.info(f"❌ Website domain not set correctly (expected: '{expected_domain}')")
    
    logger.info("==============================================================\n")


def main():
    parser = argparse.ArgumentParser(
        description='''
        Tool for migrating Odoo production database backup to a test server.
        
        The script performs the following actions:
        1. Restores the database backup with --stun option (deactivates mail servers and cron jobs)
        2. Changes the base URL to the specified one
        3. Sets autoredirect=false for all SAML providers
        4. Processes website domains according to the specified options
        5. Outputs a summary report of the changes made
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--db-name', required=True, 
                        help='Target database name for restoration')
    parser.add_argument('--backup-path', required=True, 
                        help='Path to the backup file')
    parser.add_argument('--base-url', required=True, 
                        help='New base URL for the test server (e.g., https://test.example.com)')
    parser.add_argument('--disable-website-domains', action='store_true',
                        help='Disable all website domains (set to NULL) for all websites. If specified, overrides --website-domain')
    parser.add_argument('--website-domain', 
                        help='''Domain to set for website if there is only one website in the database. 
                        If not provided and not --disable-website-domains, domain from base-url will be used. 
                        Note: This option has no effect if there are multiple websites in the database.''')
    
    # Add epilogue with usage examples
    parser.epilog = '''
Usage examples:

1. Restore a backup with disabled website domains:
   ./tools/migrate_prod_to_test.py --db-name test_db --backup-path /path/to/backup.dump --base-url https://test-odoo.example.com --disable-website-domains

2. Restore a backup with a custom domain for the website:
   ./tools/migrate_prod_to_test.py --db-name test_db --backup-path /path/to/backup.dump --base-url https://test-odoo.example.com --website-domain custom-domain.example.com

3. Restore a backup using the domain from base-url for the website:
   ./tools/migrate_prod_to_test.py --db-name test_db --backup-path /path/to/backup.dump --base-url https://test-odoo.example.com

Website Domain Behavior:
- If --disable-website-domains is specified: Domains for ALL websites will be set to NULL
- If only one website exists in the database: Domain will be set to --website-domain or domain from base-url
- If multiple websites exist: Domains will remain unchanged unless --disable-website-domains is used
'''
    
    args = parser.parse_args()
    
    # Validate backup file exists
    if not os.path.isfile(args.backup_path):
        logger.error(f"Backup file not found: {args.backup_path}")
        sys.exit(1)
    
    # Restore database
    restore_database(args.db_name, args.backup_path)
    
    # Update database settings
    update_database_settings(
        args.db_name,
        args.base_url,
        args.disable_website_domains,
        args.website_domain
    )
    
    # Print migration summary
    print_migration_summary(
        args.db_name,
        args.base_url,
        args.disable_website_domains,
        args.website_domain
    )
    
    logger.info("Migration completed successfully!")


if __name__ == "__main__":
    main()
