#!/usr/bin/env python3
"""
Quick test to verify Claude API is working
Run: python quick_test_claude.py
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_claude_api():
    api_key = os.getenv('ANTHROPIC_API_KEY')
    
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not found in .env file")
        return False
    
    print(f"🔑 API Key found: {api_key[:20]}...")
    
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    
    # Simple test
    data = {
        "model": "claude-3-sonnet-20240229",
        "max_tokens": 100,
        "messages": [
            {
                "role": "user",
                "content": "Hello! Can you help me analyze contracts? Just respond with 'Yes, I can analyze contracts.'"
            }
        ]
    }
    
    try:
        print("🚀 Testing Claude API connection...")
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            claude_response = result["content"][0]["text"]
            print(f"✅ Claude API Working!")
            print(f"📝 Response: {claude_response}")
            return True
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def test_contract_analysis():
    """Test with a sample contract snippet"""
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    
    # Sample contract text (from your database)
    sample_contract = """
    BLAST ALL Inc.
    Subcontract Agreement
    THIS AGREEMENT made this 19th day of September 2023 by and between Tri-State Painting, LLC 612 W Main St,
    Unit 2, Tilton NH 03276 hereinafter called the "Subcontractor", and Blast All, Inc., 148 Mill Rock Road, Old
    Saybrook, CT 06475, hereinafter called the "Contractor".
    
    The Subcontractor agrees to furnish all materials and perform all work as described in Section 1 and
    Section 2 hereof for the Project: CTDOT # 172-517, Metallizing of 19 Bridges Along I-395 Corridor
    
    This subcontract agreement between Blast All Inc. and Tri-State Painting, LLC is valued and
    agreed by all parties in the amount of One Million, Five Hundred Eighty-Two Thousand, Three Hundred
    and Eighty-Nine Dollars.
    """
    
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    
    # Test contract value extraction
    prompt = f"""
    Extract the contract value from this text. Return only the dollar amount.
    
    CONTRACT TEXT:
    {sample_contract}
    """
    
    data = {
        "model": "claude-3-sonnet-20240229",
        "max_tokens": 150,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
    
    try:
        print("\n🔍 Testing contract value extraction...")
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            claude_response = result["content"][0]["text"]
            print(f"✅ Contract Value Found: {claude_response}")
            
            # Test project number extraction
            prompt2 = f"""
            Extract the project number or contract identifier from this text. Return only the identifier.
            
            CONTRACT TEXT:
            {sample_contract}
            """
            
            data2 = {
                "model": "claude-3-sonnet-20240229",
                "max_tokens": 100,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt2
                    }
                ]
            }
            
            print("\n🔍 Testing contract number extraction...")
            response2 = requests.post(url, headers=headers, json=data2, timeout=30)
            
            if response2.status_code == 200:
                result2 = response2.json()
                claude_response2 = result2["content"][0]["text"]
                print(f"✅ Contract Number Found: {claude_response2}")
                return True
            else:
                print(f"❌ Second test failed: {response2.status_code}")
                return False
        else:
            print(f"❌ Contract analysis failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Contract analysis error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 CLAUDE API QUICK TEST")
    print("=" * 40)
    
    # Test 1: Basic API connectivity
    if test_claude_api():
        print("\n" + "=" * 40)
        
        # Test 2: Contract analysis capabilities
        if test_contract_analysis():
            print("\n✅ ALL TESTS PASSED!")
            print("🎯 Claude is ready for contract analysis!")
        else:
            print("\n❌ Contract analysis tests failed")
    else:
        print("\n❌ Basic API test failed")
        print("🔧 Check your ANTHROPIC_API_KEY in .env file")
