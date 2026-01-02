"""
Get all test suites of a specific test plan in a team project, and get all test points from every test suite using Azure DevOps REST API.
Author: Josef Moser
"""

import os
import argparse
import logging
try:
    from azure.devops.connection import Connection
    from msrest.authentication import BasicAuthentication
except ImportError:
    Connection = None
    BasicAuthentication = None
    logging.warning("Azure DevOps SDK not installed. Falling back to REST API.")
import requests


def get_test_plans(planet, collection, project, pat):
    url = f"https://{planet}/tfs/{collection}/{project}/_apis/test/plans?includePlanDetails=true&api-version=4.0"
    auth = requests.auth.HTTPBasicAuth('', pat)
    response = requests.get(url, auth=auth)
    response.raise_for_status()
    return response.json().get('value', [])

def get_test_suites(planet, collection, project, plan_id, pat):
    url = f"https://{planet}/tfs/{collection}/{project}/_apis/test/plans/{plan_id}/suites?api-version=4.0"
    auth = requests.auth.HTTPBasicAuth('', pat)
    response = requests.get(url, auth=auth)
    response.raise_for_status()
    return response.json().get('value', [])


def get_test_points(planet, collection, project, plan_id, suite_id, pat):
    url = f"https://{planet}/tfs/{collection}/{project}/_apis/test/plans/{plan_id}/suites/{suite_id}/points?api-version=4.0"
    auth = requests.auth.HTTPBasicAuth('', pat)
    response = requests.get(url, auth=auth)
    response.raise_for_status()
    return response.json().get('value', [])



def main():
    parser = argparse.ArgumentParser(description="Get all test suites and test points for a test plan in a team project.")
    parser.add_argument('--planet', type=str, default=os.environ.get('AZURE_DEVOPS_SERVER_URL', 'jupiter.tfs.siemens.net').replace('https://','').replace('/tfs',''), help='Azure DevOps Server hostname')
    parser.add_argument('--collection', type=str, default=os.environ.get('AZURE_DEVOPS_SERVER_COLLECTION', 'IPS'), help='Collection name')
    parser.add_argument('--project', type=str, required=True, help='Team project name')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--planid', type=str, help='Test plan ID')
    group.add_argument('--planname', type=str, help='Test plan name')
    parser.add_argument('--pat', type=str, default=os.environ.get('AZURE_DEVOPS_SERVER_TOKEN'), help='Personal Access Token')
    parser.add_argument('--outcome', type=str, choices=['Failed', 'Passed', 'Unspecified'], help='Filter testpoints by outcome (e.g., Failed)')
    args = parser.parse_args()

    if not args.pat:
        print("Error: Personal Access Token (PAT) is required. Set AZURE_DEVOPS_SERVER_TOKEN or use --pat.")
        exit(1)

    # If planname is given, look up its ID
    plan_id = args.planid
    if args.planname:
        plans = get_test_plans(args.planet, args.collection, args.project, args.pat)
        match = [p for p in plans if p.get('name', '').lower() == args.planname.lower()]
        if not match:
            print(f"Test plan with name '{args.planname}' not found in project '{args.project}'.")
            exit(1)
        plan_id = match[0].get('id')
        print(f"Found test plan '{args.planname}' with ID: {plan_id}")

    print(f"Getting test suites for plan {plan_id} in project '{args.project}'...")
    suites = get_test_suites(args.planet, args.collection, args.project, plan_id, args.pat)
    allowed_outcomes = {"Failed", "Passed", "Unspecified"}
    filter_outcome = args.outcome
    found_suite = False
    for suite in suites:
        suite_id = suite.get('id')
        suite_name = suite.get('name')
        points = get_test_points(args.planet, args.collection, args.project, plan_id, suite_id, args.pat)
        # Filter points by outcome
        if filter_outcome:
            filtered_points = [point for point in points if point.get('outcome', 'Unknown') == filter_outcome]
        else:
            filtered_points = [point for point in points if point.get('outcome', 'Unknown') in allowed_outcomes]
        if filtered_points:
            found_suite = True
            print(f"Suite: {suite_name} (ID: {suite_id})")
            for point in filtered_points:
                outcome = point.get('outcome', 'Unknown')
                test_case = point.get('testCase', {})
                print(f"  TestPoint: {test_case.get('name', 'Unknown')} (Outcome: {outcome})")
    if not found_suite:
        print("There are not any testsuites that fulfill the outcome condition.")

if __name__ == "__main__":
    main()
