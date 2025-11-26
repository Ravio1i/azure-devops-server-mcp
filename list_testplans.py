"""
List all test plans for a specific Azure DevOps Server team project using REST API and environment variable for token.
Author: Josef Moser (based on GetTestPoints.ps1)
"""
import os
import requests
import argparse


def get_test_plans(planet, collection, project, pat):
    base_url = f"https://{planet}/tfs/{collection}/{project}/_apis/test/plans?includePlanDetails=true&api-version=4.0"
    headers = {
        "Authorization": f"Basic {':'+pat}".encode("ascii").decode("ascii")
    }
    # Use requests with basic auth
    response = requests.get(base_url, headers={
        "Authorization": f"Basic {requests.auth._basic_auth_str('', pat).split(' ')[1]}"
    })
    response.raise_for_status()
    plans = response.json().get('value', [])
    return plans


def main():
    parser = argparse.ArgumentParser(description="List all test plans for a specific Azure DevOps Server team project.")
    parser.add_argument('--planet', type=str, default=os.environ.get('AZURE_DEVOPS_SERVER_URL', 'jupiter.tfs.siemens.net').replace('https://','').replace('/tfs',''), help='Azure DevOps Server hostname')
    parser.add_argument('--collection', type=str, default=os.environ.get('AZURE_DEVOPS_SERVER_COLLECTION', 'IPS'), help='Collection name')
    parser.add_argument('--project', type=str, required=True, help='Team project name')
    parser.add_argument('--pat', type=str, default=os.environ.get('AZURE_DEVOPS_SERVER_TOKEN'), help='Personal Access Token')
    args = parser.parse_args()

    if not args.pat:
        print("Error: Personal Access Token (PAT) is required. Set AZURE_DEVOPS_SERVER_TOKEN or use --pat.")
        exit(1)

    plans = get_test_plans(args.planet, args.collection, args.project, args.pat)
    print(f"Test plans for project '{args.project}':")
    for plan in plans:
        print(f"- {plan.get('name')} (ID: {plan.get('id')}, Last Updated: {plan.get('updatedDate')})")

if __name__ == "__main__":
    main()
