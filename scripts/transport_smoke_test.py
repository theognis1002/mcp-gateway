#!/usr/bin/env python3
"""
MCP Gateway Gateway Transport Smoke Test

Quick and simple smoke test for all MCP Gateway Gateway transport protocols.
This script verifies that all transport endpoints are working correctly.

Usage:
  python3 transport_smoke_test.py
"""

import asyncio

import httpx

# MCP Gateway Configuration
GATEWAY_BASE_URL = "http://localhost:8080"
ADMIN_EMAIL = "admin@admin.com"
ADMIN_PASSWORD = "qwerty123"


async def authenticate(session: httpx.AsyncClient) -> str:
    """Authenticate and get access token"""
    response = await session.post(
        f"{GATEWAY_BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    response.raise_for_status()
    data = response.json()
    return data["data"]["access_token"]


async def test_transport(
    session: httpx.AsyncClient, token: str, transport_name: str, tests: list
) -> dict:
    """Test a specific transport and return results"""
    results = {"name": transport_name, "passed": 0, "failed": 0, "tests": []}

    for test in tests:
        try:
            method = test["method"].upper()
            url = f"{GATEWAY_BASE_URL}{test['endpoint']}"
            headers = {"Authorization": f"Bearer {token}"}

            if method == "GET":
                response = await session.get(url, headers=headers)
            elif method == "POST":
                headers["Content-Type"] = "application/json"
                response = await session.post(
                    url, json=test.get("data", {}), headers=headers
                )

            response.raise_for_status()
            data = response.json()

            results["tests"].append(
                {
                    "name": test["name"],
                    "status": "✅ PASSED",
                    "response_keys": (
                        list(data.keys()) if isinstance(data, dict) else "non-dict"
                    ),
                }
            )
            results["passed"] += 1
            print(f"    ✅ {test['name']}")

        except Exception as e:
            # Get more details about HTTP errors
            error_details = str(e)
            if hasattr(e, "response") and hasattr(e.response, "text"):
                error_details = f"{str(e)} - Response: {e.response.text}"
            elif hasattr(e, "response") and hasattr(e.response, "status_code"):
                error_details = f"{str(e)} - Status: {e.response.status_code}"

            results["tests"].append(
                {
                    "name": test["name"],
                    "status": f"❌ FAILED: {error_details}",
                    "error": error_details,
                }
            )
            results["failed"] += 1
            print(f"    ❌ {test['name']}: {error_details}")

    return results


async def main():
    print("🚀 MCP Gateway Transport Smoke Test")
    print("=" * 50)

    # Test definitions for each transport
    transport_tests = {
        "JSON-RPC": [
            {
                "name": "Single RPC Request",
                "method": "POST",
                "endpoint": "/rpc",
                "data": {"jsonrpc": "2.0", "id": "1", "method": "ping", "params": {}},
            },
            {
                "name": "Batch RPC Request",
                "method": "POST",
                "endpoint": "/rpc/batch",
                "data": [{"jsonrpc": "2.0", "id": "1", "method": "ping", "params": {}}],
            },
            {
                "name": "RPC Introspection",
                "method": "GET",
                "endpoint": "/rpc/introspection",
            },
        ],
        "WebSocket": [
            {"name": "Status Check", "method": "GET", "endpoint": "/ws/status"},
            {"name": "Health Check", "method": "GET", "endpoint": "/ws/health"},
            {"name": "Metrics", "method": "GET", "endpoint": "/ws/metrics"},
        ],
        "SSE": [
            {"name": "Status Check", "method": "GET", "endpoint": "/sse/status"},
            {"name": "Health Check", "method": "GET", "endpoint": "/sse/health"},
        ],
        "MCP (Streamable HTTP)": [
            {"name": "Capabilities", "method": "GET", "endpoint": "/mcp/capabilities"},
            {"name": "Status Check", "method": "GET", "endpoint": "/mcp/status"},
            {"name": "Health Check", "method": "GET", "endpoint": "/mcp/health"},
        ],
        "STDIO": [
            {"name": "Health Check", "method": "GET", "endpoint": "/stdio/health"},
            {
                "name": "Execute Command",
                "method": "POST",
                "endpoint": "/stdio/execute",
                "data": {"command": "echo", "args": ["test"], "timeout": 5000},
            },
        ],
    }

    async with httpx.AsyncClient(timeout=30.0) as session:
        try:
            # Authenticate
            print("🔐 Authenticating...")
            token = await authenticate(session)
            print("✅ Authentication successful")

            # Test each transport
            all_results = []
            total_passed = 0
            total_failed = 0

            for transport_name, tests in transport_tests.items():
                print(f"\n🧪 Testing {transport_name} Transport...")

                result = await test_transport(session, token, transport_name, tests)
                all_results.append(result)
                total_passed += result["passed"]
                total_failed += result["failed"]

            # Print summary
            print(f"\n📊 TRANSPORT TEST SUMMARY")
            print("=" * 50)

            for result in all_results:
                status = (
                    "✅"
                    if result["failed"] == 0
                    else "❌"
                    if result["passed"] == 0
                    else "⚠️"
                )
                print(
                    f"{status} {result['name']}: {result['passed']} passed, {result['failed']} failed"
                )

            success_rate = (
                (total_passed / (total_passed + total_failed) * 100)
                if (total_passed + total_failed) > 0
                else 0
            )
            print(
                f"\n🎯 Overall Success Rate: {success_rate:.1f}% ({total_passed}/{total_passed + total_failed})"
            )

            if total_failed == 0:
                print("🎉 All transport protocols are working perfectly!")
            elif success_rate >= 80:
                print("✅ Most transport protocols are working correctly!")
            else:
                print("⚠️  Multiple transport protocols need attention.")

        except Exception as e:
            print(f"❌ Test failed: {e}")
            return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
