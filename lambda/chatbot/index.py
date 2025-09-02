import json
import boto3
import os
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
bedrock = boto3.client('bedrock-runtime')

# Environment variables
ORDERS_TABLE_NAME = os.environ['ORDERS_TABLE_NAME']
BEDROCK_MODEL_ID = os.environ['BEDROCK_MODEL_ID']

def handler(event, context):
    """
    Lambda function to handle chatbot queries for order status
    """
    try:
        # Parse request body
        body = json.loads(event['body'])
        
        # Validate required fields
        if 'query' not in body:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Query field is required'}),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            }
        
        user_query = body['query']
        customer_id = body.get('customerId')  # Optional for privacy
        
        logger.info(f"Processing chatbot query: {user_query[:100]}...")
        
        # Extract order ID or customer ID from query
        order_info = extract_order_info(user_query, customer_id)
        
        # Get order data if relevant identifiers found
        order_data = None
        if order_info:
            order_data = get_order_data(order_info)
        
        # Generate response using Bedrock
        response_text = generate_ai_response(user_query, order_data)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'response': response_text,
                'timestamp': datetime.utcnow().isoformat()
            }),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
        
    except Exception as e:
        logger.error(f"Error processing chatbot query: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Sorry, I encountered an error processing your request. Please try again later.'}),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }

def extract_order_info(query, customer_id=None):
    """
    Extract order ID or customer ID from user query
    """
    import re
    
    order_info = {}
    
    # Look for order ID patterns (UUID format)
    order_id_pattern = r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})'
    order_id_match = re.search(order_id_pattern, query.lower())
    
    if order_id_match:
        order_info['orderId'] = order_id_match.group(1)
    
    # Use provided customer ID if available
    if customer_id:
        order_info['customerId'] = customer_id
    
    # Look for customer ID patterns in query
    customer_id_pattern = r'customer\s*(?:id|number)?\s*:?\s*([a-zA-Z0-9]+)'
    customer_id_match = re.search(customer_id_pattern, query.lower())
    
    if customer_id_match and not customer_id:
        order_info['customerId'] = customer_id_match.group(1)
    
    return order_info if order_info else None

def get_order_data(order_info):
    """
    Retrieve order data from DynamoDB
    """
    try:
        table = dynamodb.Table(ORDERS_TABLE_NAME)
        orders = []
        
        if 'orderId' in order_info:
            # Query by order ID
            response = table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('orderId').eq(order_info['orderId'])
            )
            orders = response['Items']
            
        elif 'customerId' in order_info:
            # Query by customer ID using GSI
            response = table.query(
                IndexName='CustomerIdIndex',
                KeyConditionExpression=boto3.dynamodb.conditions.Key('customerId').eq(order_info['customerId']),
                ScanIndexForward=False,  # Get most recent orders first
                Limit=5  # Limit to 5 most recent orders
            )
            orders = response['Items']
        
        logger.info(f"Retrieved {len(orders)} orders from database")
        return orders
        
    except Exception as e:
        logger.error(f"Error retrieving order data: {str(e)}")
        return []

def generate_ai_response(user_query, order_data):
    """
    Generate AI response using Amazon Bedrock
    """
    try:
        # Prepare context for the AI model
        context = "You are a helpful customer service chatbot for an eCommerce company. "
        context += "Answer customer questions about their orders in a friendly and helpful manner. "
        context += "If you don't have specific order information, provide general guidance about order tracking and customer service.\n\n"
        
        if order_data:
            context += "Here is the relevant order information:\n"
            for i, order in enumerate(order_data[:3]):  # Limit to 3 orders for context
                context += f"Order {i+1}:\n"
                context += f"- Order ID: {order['orderId']}\n"
                context += f"- Status: {order.get('status', 'Unknown')}\n"
                context += f"- Created: {order.get('createdAt', 'Unknown')}\n"
                context += f"- Total: ${order.get('totalAmount', 'Unknown')}\n"
                context += f"- Items: {len(order.get('items', []))} items\n\n"
        else:
            context += "No specific order information was found for this query.\n\n"
        
        # Prepare the prompt
        prompt = f"{context}Customer Question: {user_query}\n\nResponse:"
        
        # Call Bedrock API
        model_input = {
            "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
            "max_tokens_to_sample": 300,
            "temperature": 0.7,
            "top_p": 0.9
        }
        
        response = bedrock.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps(model_input),
            contentType='application/json'
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        ai_response = response_body.get('completion', '').strip()
        
        # Fallback response if AI doesn't provide a good answer
        if not ai_response or len(ai_response) < 10:
            ai_response = generate_fallback_response(user_query, order_data)
        
        logger.info("AI response generated successfully")
        return ai_response
        
    except Exception as e:
        logger.error(f"Error generating AI response: {str(e)}")
        return generate_fallback_response(user_query, order_data)

def generate_fallback_response(user_query, order_data):
    """
    Generate a fallback response when AI is not available
    """
    if order_data:
        if len(order_data) == 1:
            order = order_data[0]
            status = order.get('status', 'Unknown')
            order_id = order.get('orderId', 'Unknown')
            
            status_messages = {
                'PENDING': 'Your order is currently being processed. We\'ll update you once it moves to the next stage.',
                'VALIDATING': 'We\'re currently validating your order details.',
                'INVENTORY_CHECK': 'We\'re checking inventory availability for your items.',
                'PAYMENT_PROCESSING': 'Your payment is being processed.',
                'FULFILLMENT': 'Your order is being prepared for shipping.',
                'COMPLETED': 'Great news! Your order has been completed and should be on its way to you.',
                'FAILED': 'There was an issue with your order. Please contact customer service for assistance.'
            }
            
            return f"I found your order {order_id}. {status_messages.get(status, f'Your order status is: {status}')} Is there anything else you'd like to know about your order?"
        
        else:
            return f"I found {len(order_data)} orders associated with your account. Your most recent order is {order_data[0].get('status', 'Unknown').lower()}. Would you like details about a specific order?"
    
    else:
        return "I'd be happy to help you with your order! To provide the most accurate information, could you please provide your order ID or let me know what specific information you're looking for? You can also contact our customer service team for personalized assistance."