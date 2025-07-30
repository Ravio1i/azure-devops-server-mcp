#!/usr/bin/env python3
"""
Simple test script for Azure DevOps Server MCP
"""
import os
import asyncio
from mcp.server import AzureDevOpsServerMCP

async def test_connection():
    """Test basic connection to Azure DevOps Server"""
    try:
        # Make sure environment variables are set
        server_url = os.getenv("AZURE_DEVOPS_SERVER_URL")
        token = os.getenv("AZURE_DEVOPS_SERVER_TOKEN")
        
        if not server_url or not token:
            print("❌ Please set AZURE_DEVOPS_SERVER_URL and AZURE_DEVOPS_SERVER_TOKEN environment variables")
            return
        
        print(f"🔗 Connecting to: {server_url}")
        
        client = AzureDevOpsServerMCP()
        print("✅ Connection initialized successfully")
        
        # Test with a sample project (replace with your actual project name)
        project_name = input("Enter project name to test: ").strip()
        if project_name:
            print(f"📋 Testing work item listing for project: {project_name}")
            work_items = await client.list_work_items(project_name)
            print(f"✅ Found {len(work_items)} work items")
            
            if work_items:
                first_item = work_items[0]
                print(f"📝 First work item: ID {first_item['id']} - {first_item['fields'].get('System.Title', 'No title')}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())