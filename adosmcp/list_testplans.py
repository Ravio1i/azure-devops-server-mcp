"""
List all test plans for a specific Azure DevOps Server team project using the Azure DevOps Python SDK (if available).
Author: Josef Moser (improved, uses AzureDevOpsWorkItems.py style)
"""
import os
import argparse
import logging

from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication

import requests


def get_test_plans_sdk(connection, project):
    try:
        test_client = connection.clients.get_test_plan_client()
        plans = test_client.get_test_plans(project)
        return [
            {
                "id": plan.id,
                "name": plan.name,
                "state": plan.state,
                "updatedDate": getattr(plan, 'updated_date', None)
            }
            for plan in plans
        ]
    except Exception as e:
        logging.error(f"SDK error: {e}")
        return None






def main():

    parser = argparse.ArgumentParser(description="List all test plans for a specific Azure DevOps Server team project.")
    parser.add_argument('--planet', type=str, default=os.environ.get('AZURE_DEVOPS_SERVER_URL', 'jupiter.tfs.siemens.net').replace('https://','').replace('/tfs',''), help='Azure DevOps Server hostname')
    parser.add_argument('--collection', type=str, default=os.environ.get('AZURE_DEVOPS_SERVER_COLLECTION', 'IPS'), help='Collection name')
    parser.add_argument('--project', type=str, required=True, help='Team project name')
    parser.add_argument('--pat', type=str, default=os.environ.get('AZURE_DEVOPS_SERVER_TOKEN'), help='Personal Access Token')
    parser.add_argument('--latest', action='store_true', help='Show only the latest test plan')
    parser.add_argument('--lastdays', type=int, default=None, help='Show test plans updated in the last N days (e.g., 14)')
    parser.add_argument('--active', action='store_true', help='Show only active test plans (state=active)')
    args = parser.parse_args()

    if not args.pat:
        print("Error: Personal Access Token (PAT) is required. Set AZURE_DEVOPS_SERVER_TOKEN or use --pat.")
        exit(1)

    plans = None
    if Connection and BasicAuthentication:
        try:
            org_url = f"https://{args.planet}/tfs/{args.collection}"
            credentials = BasicAuthentication('', args.pat)
            connection = Connection(base_url=org_url, creds=credentials)
            plans = get_test_plans_sdk(connection, args.project)
        except Exception as sdk_error:
            logging.warning(f"SDK failed: {sdk_error}. Falling back to REST API.")


    # Filtering
    from datetime import datetime, timedelta
    filtered_plans = plans
    # Convert updatedDate to datetime if present
    for plan in filtered_plans:
        if plan.get('updatedDate'):
            try:
                plan['updatedDate_dt'] = datetime.strptime(plan['updatedDate'][:19], "%Y-%m-%dT%H:%M:%S")
            except Exception:
                plan['updatedDate_dt'] = None
        else:
            plan['updatedDate_dt'] = None

    if args.active:
        filtered_plans = [p for p in filtered_plans if str(p.get('state','')).lower() == 'active']

    if args.lastdays:
        cutoff = datetime.now() - timedelta(days=args.lastdays)
        filtered_plans = [p for p in filtered_plans if p['updatedDate_dt'] and p['updatedDate_dt'] >= cutoff]

    if args.latest and filtered_plans:
        filtered_plans = [max(filtered_plans, key=lambda p: p['updatedDate_dt'] or datetime.min)]

    print(f"Test plans for project '{args.project}':")
    for plan in filtered_plans:
        print(f"- {plan['name']} (ID: {plan['id']}, State: {plan['state']}, Last Updated: {plan['updatedDate']})")

if __name__ == "__main__":
    main()
