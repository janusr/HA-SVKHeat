#!/usr/bin/env python3
"""Test script to debug SVK heat pump device response format."""

import asyncio
import logging
import sys
from urllib.parse import urljoin

import aiohttp
from yarl import URL

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
_LOGGER = logging.getLogger(__name__)

async def test_device_response(host, username="", password=""):
    """Test the device response format."""
    
    base_url = URL.build(scheme="http", host=host)
    timeout = aiohttp.ClientTimeout(total=10)
    
    # Test a few different endpoints to understand the API
    test_endpoints = [
        "/cgi-bin/json_values.cgi",
        "/json_values.cgi",
        "/api/values",
        "/api/json",
        "/"
    ]
    
    # Test with a few sample IDs
    test_ids = [297, 253, 254, 255, 256]
    
    headers = {
        "User-Agent": "SVKHeatpump/0.1 (HomeAssistant)",
        "Accept": "application/json",
        "Accept-Language": "en",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "close",
    }
    
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        # Test each endpoint
        for endpoint in test_endpoints:
            url = base_url.with_path(endpoint)
            _LOGGER.info("Testing endpoint: %s", url)
            
            try:
                # Test with GET request and query parameters
                query_params = f"ids={','.join(map(str, test_ids))}"
                get_url = url.with_query(query_params)
                
                async with session.get(get_url) as resp:
                    _LOGGER.info("GET %s - Status: %d", get_url, resp.status)
                    _LOGGER.info("Response headers: %s", dict(resp.headers))
                    
                    if resp.status == 200:
                        content_type = resp.headers.get('Content-Type', '')
                        _LOGGER.info("Content-Type: %s", content_type)
                        
                        if 'application/json' in content_type:
                            try:
                                data = await resp.json()
                                _LOGGER.info("JSON response type: %s", type(data))
                                _LOGGER.info("JSON response: %s", data)
                            except Exception as e:
                                text = await resp.text()
                                _LOGGER.error("Failed to parse JSON: %s", e)
                                _LOGGER.error("Response text: %s", text[:500])
                        else:
                            text = await resp.text()
                            _LOGGER.info("Non-JSON response (first 500 chars): %s", text[:500])
                    else:
                        text = await resp.text()
                        _LOGGER.error("Error response (first 500 chars): %s", text[:500])
                        
            except Exception as e:
                _LOGGER.error("Error testing %s: %s", get_url, e)
            
            print("\n" + "="*80 + "\n")
        
        # Test with POST request
        if username and password:
            auth = aiohttp.BasicAuth(username, password)
            headers["Authorization"] = auth.encode()
        
        post_url = base_url.with_path("/cgi-bin/json_values.cgi")
        payload = {"ids": test_ids}
        
        _LOGGER.info("Testing POST request to: %s", post_url)
        _LOGGER.info("POST payload: %s", payload)
        
        try:
            async with session.post(post_url, json=payload) as resp:
                _LOGGER.info("POST %s - Status: %d", post_url, resp.status)
                _LOGGER.info("Response headers: %s", dict(resp.headers))
                
                if resp.status == 200:
                    content_type = resp.headers.get('Content-Type', '')
                    _LOGGER.info("Content-Type: %s", content_type)
                    
                    if 'application/json' in content_type:
                        try:
                            data = await resp.json()
                            _LOGGER.info("JSON response type: %s", type(data))
                            _LOGGER.info("JSON response: %s", data)
                        except Exception as e:
                            text = await resp.text()
                            _LOGGER.error("Failed to parse JSON: %s", e)
                            _LOGGER.error("Response text: %s", text[:500])
                    else:
                        text = await resp.text()
                        _LOGGER.info("Non-JSON response (first 500 chars): %s", text[:500])
                else:
                    text = await resp.text()
                    _LOGGER.error("Error response (first 500 chars): %s", text[:500])
                    
        except Exception as e:
            _LOGGER.error("Error testing POST %s: %s", post_url, e)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_device_response.py <host> [username] [password]")
        sys.exit(1)
    
    host = sys.argv[1]
    username = sys.argv[2] if len(sys.argv) > 2 else ""
    password = sys.argv[3] if len(sys.argv) > 3 else ""
    
    asyncio.run(test_device_response(host, username, password))