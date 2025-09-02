#!/usr/bin/env python3
"""
Demo script to test the eCommerce Order Processing API
"""

import requests
import json
import time
import uuid

# Configuration - Update these values after deployment
API_BASE_URL = "https://8uq0sm8ip5.execute-api.eu-central-1.amazonaws.com/prod"
API_KEY = "l4Xay4hF1Y1TDKOEnMv5W5YArH7UZJNJ4jGZWwM1"

class OrderAPIDemo:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {
            'Content-Type': 'application/json',
            'X-API-Key': api_key
        }
    
    def create_sample_order(self, customer_id=None):
        """Create a sample order for testing"""
        if not customer_id:
            customer_id = f"customer_{uuid.uuid4().hex[:8]}"
        
        sample_order = {
            "customerId": customer_id,
            "customerEmail": f"{customer_id}@example.com",
            "items": [
                {
                    "productId": "LAPTOP001",
                    "name": "Gaming Laptop",
                    "quantity": 1,
                    "price": 1299.99
                },
                {
                    "productId": "MOUSE001",
                    "name": "Wireless Mouse",
                    "quantity": 1,
                    "price": 49.99
                }
            ],
            "totalAmount": 1349.98,
            "shippingAddress": {
                "street": "123 Main St",
                "city": "Anytown",
                "state": "CA",
                "zipCode": "12345",
                "country": "USA"
            },
            "billingAddress": {
                "street": "123 Main St",
                "city": "Anytown",
                "state": "CA",
                "zipCode": "12345",
                "country": "USA"
            }
        }
        
        print(f"\n🛒 Creating order for customer: {customer_id}")
        print(f"   Items: {len(sample_order['items'])}")
        print(f"   Total: ${sample_order['totalAmount']}")
        
        try:
            response = requests.post(
                f"{self.base_url}/orders",
                headers=self.headers,
                json=sample_order
            )
            
            if response.status_code == 201:
                result = response.json()
                print(f"✅ Order created successfully!")
                print(f"   Order ID: {result['orderId']}")
                print(f"   Status: {result['status']}")
                return result['orderId']
            else:
                print(f"❌ Failed to create order: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error creating order: {str(e)}")
            return None
    
    def get_order_status(self, order_id):
        """Get the current status of an order"""
        print(f"\n📋 Checking status for order: {order_id}")
        
        try:
            response = requests.get(
                f"{self.base_url}/orders/{order_id}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                order = response.json()
                print(f"✅ Order found!")
                print(f"   Status: {order.get('status', 'Unknown')}")
                print(f"   Created: {order.get('createdAt', 'Unknown')}")
                print(f"   Updated: {order.get('updatedAt', 'Unknown')}")
                if 'errorMessage' in order:
                    print(f"   Error: {order['errorMessage']}")
                return order
            else:
                print(f"❌ Failed to get order: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting order: {str(e)}")
            return None
    
    def test_chatbot(self, query, customer_id=None):
        """Test the chatbot functionality"""
        print(f"\n🤖 Testing chatbot with query: '{query}'")
        
        payload = {"query": query}
        if customer_id:
            payload["customerId"] = customer_id
        
        try:
            response = requests.post(
                f"{self.base_url}/chatbot",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Chatbot response:")
                print(f"   {result['response']}")
                return result['response']
            else:
                print(f"❌ Chatbot request failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error testing chatbot: {str(e)}")
            return None
    
    def run_demo(self):
        """Run a complete demo of the system"""
        print("🚀 Starting eCommerce Order Processing API Demo")
        print("=" * 50)
        
        # Step 1: Create a new order
        customer_id = f"demo_customer_{int(time.time())}"
        order_id = self.create_sample_order(customer_id)
        
        if not order_id:
            print("❌ Demo failed - could not create order")
            return
        
        # Step 2: Wait a moment for processing
        print("\n⏳ Waiting for order processing...")
        time.sleep(5)
        
        # Step 3: Check order status
        order = self.get_order_status(order_id)
        
        # Step 4: Test chatbot with order ID
        if order_id:
            self.test_chatbot(f"What's the status of my order {order_id}?")
        
        # Step 5: Test chatbot with customer ID
        self.test_chatbot("What are my recent orders?", customer_id)
        
        # Step 6: Test general chatbot query
        self.test_chatbot("How do I track my order?")
        
        print("\n🎉 Demo completed!")
        print(f"📝 Summary:")
        print(f"   Customer ID: {customer_id}")
        print(f"   Order ID: {order_id}")
        print(f"   Final Status: {order.get('status', 'Unknown') if order else 'Unknown'}")

def main():
    """Main function to run the demo"""
    
    # Check if URL and API key are configured
    if "your-api-gateway-url" in API_BASE_URL or "your-api-key" in API_KEY:
        print("⚠️  Please update the API_BASE_URL and API_KEY variables in this script")
        print("   You can find these values in the CDK output after deployment")
        return
    
    # Initialize the demo
    demo = OrderAPIDemo(API_BASE_URL, API_KEY)
    
    # Run the demo
    demo.run_demo()

if __name__ == "__main__":
    main()